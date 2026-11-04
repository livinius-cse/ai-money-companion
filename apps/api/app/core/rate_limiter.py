import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status
from app.core.config import settings


class InMemoryRateLimiter:
    """
    Sliding window rate limiter for login and sensitive endpoints.
    Tracks timestamps of attempts per key (e.g. client IP).
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check_rate_limit(self, key: str) -> Tuple[bool, int]:
        """
        Check if the key is within rate limits.
        Returns: (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Prune timestamps older than window
        timestamps = [t for t in self._history[key] if t > window_start]
        self._history[key] = timestamps

        if len(timestamps) >= self.max_requests:
            # Earliest timestamp in current window
            oldest = timestamps[0]
            retry_after = max(1, int(oldest + self.window_seconds - now))
            return False, retry_after

        # Record this attempt
        self._history[key].append(now)
        return True, 0

    def reset(self, key: Optional[str] = None) -> None:
        """Reset history for a key or all keys (useful in tests)."""
        if key:
            self._history.pop(key, None)
        else:
            self._history.clear()


login_rate_limiter = InMemoryRateLimiter(
    max_requests=settings.RATE_LIMIT_LOGIN_PER_MINUTE,
    window_seconds=60,
)


def get_client_ip(request: Request) -> str:
    """Extract client IP handling proxy headers safely."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the leftmost untrusted client IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def enforce_login_rate_limit(request: Request) -> None:
    """Dependency that enforces the login rate limit."""
    ip = get_client_ip(request)
    allowed, retry_after = login_rate_limiter.check_rate_limit(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
