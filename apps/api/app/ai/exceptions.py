class AIError(Exception):
    """Base exception for all AI subsystem errors."""
    pass


class AIConfigurationError(AIError):
    """Raised when an AI provider is improperly configured or missing required keys."""
    pass


class AIProviderError(AIError):
    """Raised when an upstream AI provider fails or returns an error."""
    pass


class AITimeoutError(AIProviderError):
    """Raised when an AI provider call exceeds its configured timeout deadline."""
    pass


class AIRateLimitError(AIProviderError):
    """Raised when an AI provider rejects calls due to quota exhaustion or rate limits."""
    pass


class AISchemaValidationError(AIProviderError):
    """Raised when AI model output fails Pydantic schema validation."""
    pass
