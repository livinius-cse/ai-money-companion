from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs (application/problem+json)."""
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Short, human-readable summary of problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation of occurrence")
    instance: str = Field(..., description="URI of request path")

    # Extension Members
    requested_provider: Optional[Literal["mock", "gemini"]] = None
    actual_provider: Optional[Literal["mock", "gemini"]] = None
    fallback_attempted: bool = False
    violations: List[Dict[str, Any]] = Field(default_factory=list)
