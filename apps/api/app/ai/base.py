from typing import Protocol, Type, TypeVar, Optional, Generic, Literal
from pydantic import BaseModel, Field

T = TypeVar("T")


class AIExecutionMetadata(BaseModel):
    requested_provider: Literal["mock", "gemini"]
    actual_provider: Literal["mock", "gemini"]
    is_mock_generated: bool
    model_name: str
    execution_duration_ms: int = Field(default=0, ge=0)
    is_fallback: bool = False
    fallback_reason: Optional[str] = None


class AIResponseEnvelope(BaseModel, Generic[T]):
    data: T
    telemetry: AIExecutionMetadata


class BaseAIProvider(Protocol):
    """Abstract asynchronous interface for all AI model adapters."""

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout_seconds: Optional[float] = None,
    ) -> AIResponseEnvelope[str]:
        """Asynchronously generate unstructured text."""
        ...

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        timeout_seconds: Optional[float] = None,
    ) -> AIResponseEnvelope[T]:
        """Asynchronously generate structured output validated against a Pydantic schema."""
        ...

    def get_provider_name(self) -> str:
        """Return provider identifier ('mock' or 'gemini')."""
        ...

    def is_available(self) -> bool:
        """Return provider readiness status."""
        ...
