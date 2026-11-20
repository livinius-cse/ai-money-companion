import base64
import binascii
import logging
import re
from typing import Tuple

import httpx

from app.core.config import settings
from app.core.storage import MAX_UPLOAD_SIZE_BYTES, detect_image_type

logger = logging.getLogger("ai_money_companion.cloudflare_images")

MODEL_ID = "@cf/black-forest-labs/flux-1-schnell"
MODEL_STEPS = 4
COLORING_PAGE_STYLE = (
    " Create a child-friendly black-and-white coloring book illustration: "
    "pure white background, clean bold black closed outlines, simple rounded shapes, "
    "large open spaces for crayons, minimal uncluttered details, no color, no gray, "
    "no gradients, no shadows, no hatching, no textures, no letters, no watermark, "
    "single centered subject, print-friendly line art."
)


class CloudflareImageGenerationError(Exception):
    """Safe, user-facing image generation error without provider secrets."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class CloudflareImageProvider:
    """Cloudflare Workers AI adapter for FLUX.1 Schnell image generation."""

    @staticmethod
    def is_configured() -> bool:
        return bool(
            (settings.CLOUDFLARE_ACCOUNT_ID or "").strip()
            and (settings.CLOUDFLARE_API_TOKEN or "").strip()
        )

    async def generate_image(self, illustration_prompt: str) -> Tuple[bytes, str]:
        account_id = (settings.CLOUDFLARE_ACCOUNT_ID or "").strip()
        api_token = (settings.CLOUDFLARE_API_TOKEN or "").strip()
        if not account_id or not api_token:
            raise CloudflareImageGenerationError(
                503,
                "Cloudflare Workers AI is not configured. Add CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN to the backend .env file.",
            )
        if not re.fullmatch(r"[0-9a-fA-F]{32}", account_id):
            raise CloudflareImageGenerationError(
                503, "CLOUDFLARE_ACCOUNT_ID must be the 32-character Account ID from Cloudflare."
            )

        prompt = f"{illustration_prompt.strip()}{COLORING_PAGE_STYLE}"
        if len(prompt) > 2048:
            prompt = f"{illustration_prompt.strip()[:1800]}{COLORING_PAGE_STYLE}"

        endpoint = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{account_id}/ai/run/{MODEL_ID}"
        )
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        payload = {"prompt": prompt, "steps": MODEL_STEPS}

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(settings.CLOUDFLARE_IMAGE_TIMEOUT_SECONDS)
            ) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            logger.warning("Cloudflare image request timed out.")
            raise CloudflareImageGenerationError(
                504, "Cloudflare image generation timed out. Please retry this illustration."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Cloudflare image request could not connect.")
            raise CloudflareImageGenerationError(
                502, "Could not connect to Cloudflare Workers AI. Please retry."
            ) from exc

        if response.status_code == 429:
            raise CloudflareImageGenerationError(
                429,
                "Cloudflare Workers AI rate limit or daily Neurons quota reached. Check Workers AI usage before retrying.",
            )
        if response.status_code in (401, 403):
            raise CloudflareImageGenerationError(
                503,
                "Cloudflare rejected the Workers AI credentials. Check the Account ID and API token permissions.",
            )
        if response.status_code >= 500:
            logger.warning("Cloudflare image service returned HTTP %s.", response.status_code)
            raise CloudflareImageGenerationError(
                502, "Cloudflare image service is temporarily unavailable. Please retry."
            )
        if response.status_code >= 400:
            logger.warning("Cloudflare image request returned HTTP %s.", response.status_code)
            raise CloudflareImageGenerationError(
                502, "Cloudflare could not process this image prompt. Review the prompt and retry."
            )

        try:
            data = response.json()
            image_base64 = (data.get("result") or {}).get("image") or data.get("image")
            if not isinstance(image_base64, str) or not image_base64:
                raise ValueError("Missing image payload")
            image_bytes = base64.b64decode(image_base64, validate=True)
        except (ValueError, TypeError, binascii.Error) as exc:
            logger.warning("Cloudflare response did not contain a valid Base64 image.")
            raise CloudflareImageGenerationError(
                502, "Cloudflare returned an invalid image response. Please retry."
            ) from exc

        if not image_bytes or len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
            raise CloudflareImageGenerationError(
                502, "Generated image is empty or exceeds the 10 MB asset limit."
            )

        detected = detect_image_type(image_bytes)
        if not detected:
            raise CloudflareImageGenerationError(
                502, "Cloudflare returned an unsupported image format."
            )

        mime_type, _extension = detected
        return image_bytes, mime_type
