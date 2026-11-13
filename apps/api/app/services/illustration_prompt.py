import logging
from typing import Optional, List, Tuple
from app.ai.base import BaseAIProvider, AIResponseEnvelope
from app.ai.factory import AIProviderFactory
from app.schemas.illustration import (
    IllustrationPromptGenerateRequest,
    IllustrationPromptGenerateResponse,
)

logger = logging.getLogger("ai_money_companion.illustration_prompt")

VALID_STATUSES = {"PROMPT", "PLACEHOLDER", "GENERATED", "APPROVED_FINAL"}


class IllustrationPromptService:
    """
    Service for generating creative illustration prompts and managing
    the strict illustration asset lifecycle.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider or AIProviderFactory.get_provider()

    async def generate_prompts(
        self,
        book_title: str,
        book_topic: str,
        chapter_title: Optional[str],
        chapter_summary: Optional[str],
        req: IllustrationPromptGenerateRequest,
    ) -> AIResponseEnvelope[IllustrationPromptGenerateResponse]:
        """
        Generate contextual illustration prompts adhering to a consistent visual style.
        """
        prompt = (
            f"You are an art director for a professional publishing house.\n"
            f"Book Title: {book_title}\n"
            f"Book Topic: {book_topic}\n"
            f"Style Preset: {req.style_preset or 'modern_clean_vector'}\n"
            f"Target Prompts: {req.target_count}\n"
        )
        if chapter_title:
            prompt += f"Chapter Context: {chapter_title} - {chapter_summary or ''}\n"
        if req.visual_instructions:
            prompt += f"Specific Visual Instructions: {req.visual_instructions}\n"

        system_prompt = (
            "Create high-clarity, high-impact illustration prompts suitable for professional KDP book publication. "
            "Ensure prompts describe clear focal subjects, high-contrast monochrome or vector palettes, "
            "and clean negative space. Return valid JSON."
        )

        return await self.provider.generate_structured(
            prompt=prompt,
            response_model=IllustrationPromptGenerateResponse,
            system_prompt=system_prompt,
            temperature=0.7,
        )

    @staticmethod
    def validate_status_transition(
        current_status: str,
        new_status: str,
        has_asset: bool,
        human_approved: bool,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validates state machine transitions for illustrations:
        PROMPT -> PLACEHOLDER, GENERATED
        PLACEHOLDER -> PROMPT, GENERATED
        GENERATED -> APPROVED_FINAL, PLACEHOLDER, PROMPT
        APPROVED_FINAL -> GENERATED (revert)
        """
        if new_status not in VALID_STATUSES:
            return False, f"Invalid status '{new_status}'. Allowed: {', '.join(sorted(VALID_STATUSES))}"

        if current_status == new_status:
            return True, None

        # Cannot be GENERATED or APPROVED_FINAL without an uploaded image file
        if new_status in ("GENERATED", "APPROVED_FINAL") and not has_asset:
            return False, f"Cannot set status to '{new_status}' without an uploaded image asset."

        # Cannot be APPROVED_FINAL without explicit human publisher approval
        if new_status == "APPROVED_FINAL" and not human_approved:
            return False, "Cannot transition to 'APPROVED_FINAL' without explicit publisher human approval."

        # Valid transitions table
        valid_transitions = {
            "PROMPT": {"PLACEHOLDER", "GENERATED"},
            "PLACEHOLDER": {"PROMPT", "GENERATED"},
            "GENERATED": {"APPROVED_FINAL", "PLACEHOLDER", "PROMPT"},
            "APPROVED_FINAL": {"GENERATED", "PLACEHOLDER"},
        }

        allowed_next = valid_transitions.get(current_status, set())
        if new_status not in allowed_next:
            return False, f"Invalid status transition from '{current_status}' to '{new_status}'."

        return True, None
