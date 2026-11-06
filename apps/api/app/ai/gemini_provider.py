import asyncio
import time
import json
from typing import Type, TypeVar, Optional, Any
import httpx
from pydantic import BaseModel
from app.ai.base import BaseAIProvider, AIResponseEnvelope, AIExecutionMetadata
from app.ai.exceptions import (
    AIProviderError,
    AITimeoutError,
    AIRateLimitError,
    AIConfigurationError,
    AISchemaValidationError,
)

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(BaseAIProvider):
    """
    Asynchronous Gemini provider communicating via httpx.AsyncClient.
    Zero external Google SDK dependencies required.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        if not api_key:
            raise AIConfigurationError("GEMINI_API_KEY must not be empty.")
        self.api_key = api_key
        self.model_name = model_name
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"

    def get_provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout_seconds: Optional[float] = 30.0,
    ) -> AIResponseEnvelope[str]:
        timeout = timeout_seconds or 30.0
        start = time.monotonic()

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        contents = [{"parts": [{"text": prompt}]}]
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                res = await client.post(self.endpoint, json=payload, headers=headers)
                res.raise_for_status()
                res_data = res.json()

            candidates = res_data.get("candidates", [])
            if not candidates:
                raise AIProviderError("Gemini returned zero candidates.")
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        except asyncio.CancelledError:
            raise
        except httpx.TimeoutException as e:
            raise AITimeoutError(f"Gemini call timed out after {timeout}s.") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429:
                raise AIRateLimitError("Gemini rate limit exceeded.") from e
            if status_code in (401, 403):
                raise AIConfigurationError("Gemini authentication failure. Verify GEMINI_API_KEY.") from e
            raise AIProviderError(f"Gemini upstream error (HTTP {status_code}).") from e
        except Exception as e:
            raise AIProviderError("Gemini communication failure.") from e

        duration = int((time.monotonic() - start) * 1000)
        return AIResponseEnvelope[str](
            data=text,
            telemetry=AIExecutionMetadata(
                requested_provider="gemini",
                actual_provider="gemini",
                is_mock_generated=False,
                model_name=self.model_name,
                execution_duration_ms=duration,
                is_fallback=False,
            ),
        )

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = 30.0,
    ) -> AIResponseEnvelope[T]:
        timeout = timeout_seconds or 30.0
        start = time.monotonic()

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_prompt = (
            f"{prompt}\n\n"
            f"IMPORTANT: Respond strictly with valid JSON conforming to this schema:\n"
            f"{schema_json}"
        )

        contents = [{"parts": [{"text": augmented_prompt}]}]
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                res = await client.post(self.endpoint, json=payload, headers=headers)
                res.raise_for_status()
                res_data = res.json()

            candidates = res_data.get("candidates", [])
            if not candidates:
                raise AIProviderError("Gemini returned zero candidates.")
            raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")

            parsed_json = json.loads(raw_text)
            parsed_data = response_model.model_validate(parsed_json)

        except asyncio.CancelledError:
            raise
        except (json.JSONDecodeError, ValueError) as e:
            raise AISchemaValidationError("Failed to parse Gemini output into target schema.") from e
        except httpx.TimeoutException as e:
            raise AITimeoutError(f"Gemini call timed out after {timeout}s.") from e
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            if status_code == 429:
                raise AIRateLimitError("Gemini rate limit exceeded.") from e
            if status_code in (401, 403):
                raise AIConfigurationError("Gemini authentication failure. Verify GEMINI_API_KEY.") from e
            raise AIProviderError(f"Gemini upstream error (HTTP {status_code}).") from e
        except Exception as e:
            if isinstance(e, (AIError, asyncio.CancelledError)):
                raise
            raise AIProviderError("Gemini communication failure.") from e

        duration = int((time.monotonic() - start) * 1000)
        return AIResponseEnvelope[T](
            data=parsed_data,
            telemetry=AIExecutionMetadata(
                requested_provider="gemini",
                actual_provider="gemini",
                is_mock_generated=False,
                model_name=self.model_name,
                execution_duration_ms=duration,
                is_fallback=False,
            ),
        )
