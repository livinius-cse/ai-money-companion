from app.ai.factory import AIProviderFactory
from app.schemas.metadata import MetadataGenerateRequest, KDPMetadataResponse
from app.services.html_validator import HTMLAllowlistValidator


class MetadataGenerationService:
    """
    Domain service for generating KDP search keywords, categories, and compliant HTML descriptions.
    Enforces conservative HTML allowlist and generates unconfirmed AI disclosure drafts.
    """

    @staticmethod
    async def generate_metadata(request: MetadataGenerateRequest) -> KDPMetadataResponse:
        prompt = (
            f"Generate KDP metadata for book title: '{request.title}', subtitle: '{request.subtitle or ''}', "
            f"summary: '{request.topic_summary}', target audience: '{request.target_audience}'."
        )

        envelope = await AIProviderFactory.execute_structured(
            prompt=prompt,
            response_model=KDPMetadataResponse,
            system_prompt=(
                "You are an expert Amazon KDP SEO strategist and copywriter. "
                "Format book descriptions using ONLY conservative allowed HTML tags: "
                "b, em, i, u, br, p, ol, ul, li, h4, h5, h6. "
                "Do NOT use attributes, links, or disallowed tags."
            ),
        )
        metadata = envelope.data

        # 1. Validate HTML description with conservative allowlist parser
        html_violations = HTMLAllowlistValidator.validate_description(metadata.description_html)
        if html_violations:
            err_msg = "; ".join(v.message for v in html_violations)
            raise ValueError(f"Generated description violates KDP HTML rules: {err_msg}")

        # 2. Check title repetition & keyword length advisories
        title_words = set(w.lower() for w in request.title.split() if len(w) > 3)
        advisories = list(metadata.keyword_advisories)
        for idx, kw in enumerate(metadata.keywords, start=1):
            if len(kw) > 50:
                advisories.append(f"Keyword slot {idx} ('{kw[:30]}...') exceeds 50 characters (advisory).")
            kw_words = set(w.lower() for w in kw.split())
            repeated = title_words.intersection(kw_words)
            if repeated:
                advisories.append(f"Keyword slot {idx} repeats title words {repeated} (advisory).")

        metadata.keyword_advisories = advisories

        # 3. Ensure AI disclosure recommendation is strictly unconfirmed
        if isinstance(metadata.unconfirmed_disclosure_recommendation, dict):
            metadata.unconfirmed_disclosure_recommendation["author_confirmed"] = False

        return metadata
