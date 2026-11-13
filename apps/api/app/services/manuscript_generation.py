import logging
from typing import Optional, Tuple
from app.ai.base import BaseAIProvider, AIResponseEnvelope
from app.ai.factory import AIProviderFactory
from app.schemas.manuscript import (
    ManuscriptDraftRequest,
    ManuscriptDraftResponse,
    SectionExpandRequest,
    SectionExpandResponse,
    SectionRegenerateRequest,
    SectionRegenerateResponse,
)

logger = logging.getLogger("ai_money_companion.manuscript_generation")


class ManuscriptGenerationService:
    """
    AI-powered manuscript generation service.
    Orchestrates chapter drafting, section expansion, and section regeneration
    with strict human-in-the-loop review semantics.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or AIProviderFactory.get_provider()

    async def draft_chapter(
        self,
        book_title: str,
        book_topic: str,
        target_audience: Optional[str],
        chapter_number: int,
        chapter_title: str,
        chapter_summary: Optional[str],
        req: ManuscriptDraftRequest,
    ) -> AIResponseEnvelope[ManuscriptDraftResponse]:
        """
        Draft a full manuscript chapter based on book and chapter context.
        The returned draft is always marked as DRAFT and unreviewed.
        """
        prompt = (
            f"You are a professional non-fiction author and publishing editor.\n"
            f"Book Title: {book_title}\n"
            f"Book Topic: {book_topic}\n"
            f"Target Audience: {target_audience or 'General non-fiction reader'}\n"
            f"Chapter {chapter_number}: {chapter_title}\n"
            f"Chapter Synopsis: {chapter_summary or 'In-depth exploration of the topic.'}\n"
            f"Target Word Count: {req.target_words} words\n"
            f"Tone: {req.tone or 'authoritative and practical'}\n"
        )
        if req.special_instructions:
            prompt += f"Special Focus: {req.special_instructions}\n"

        system_prompt = (
            "You are an expert author drafting a non-fiction book chapter. "
            "Write in clean, readable GitHub-flavored Markdown. "
            "Include an H1 title, contextual H2 subsections, concrete examples, and actionable takeaways. "
            "Return structured JSON matching ManuscriptDraftResponse."
        )

        return await self.provider.generate_structured(
            prompt=prompt,
            response_model=ManuscriptDraftResponse,
            system_prompt=system_prompt,
            temperature=0.7,
        )

    async def expand_section(
        self,
        book_topic: str,
        chapter_title: str,
        req: SectionExpandRequest,
    ) -> AIResponseEnvelope[SectionExpandResponse]:
        """
        Expand an existing manuscript section with deeper operational details.
        """
        prompt = (
            f"Book Topic: {book_topic}\n"
            f"Chapter Title: {chapter_title}\n"
            f"Section Heading: {req.section_heading}\n"
            f"Current Text:\n{req.current_text}\n\n"
        )
        if req.expansion_guidance:
            prompt += f"Expansion Guidance: {req.expansion_guidance}\n"

        system_prompt = (
            "Expand this book section with actionable, step-by-step methodologies, "
            "clear bullet points, and practical insights. Return valid JSON."
        )

        return await self.provider.generate_structured(
            prompt=prompt,
            response_model=SectionExpandResponse,
            system_prompt=system_prompt,
            temperature=0.6,
        )

    async def regenerate_section(
        self,
        book_topic: str,
        chapter_title: str,
        req: SectionRegenerateRequest,
    ) -> AIResponseEnvelope[SectionRegenerateResponse]:
        """
        Regenerate an existing manuscript section using alternative angles or refined style.
        """
        prompt = (
            f"Book Topic: {book_topic}\n"
            f"Chapter Title: {chapter_title}\n"
            f"Section Heading: {req.section_heading}\n"
            f"Current Text to Rewrite:\n{req.current_text}\n\n"
        )
        if req.alternative_instructions:
            prompt += f"Alternative Style / Instructions: {req.alternative_instructions}\n"

        system_prompt = (
            "Rewrite and refine this section to improve clarity, impact, and reader retention. "
            "Return valid JSON."
        )

        return await self.provider.generate_structured(
            prompt=prompt,
            response_model=SectionRegenerateResponse,
            system_prompt=system_prompt,
            temperature=0.7,
        )
