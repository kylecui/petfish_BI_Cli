from __future__ import annotations

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including first).
        delay_seconds: Initial delay between retries.
        backoff: Multiplier applied to delay after each failure.
        exceptions: Exception types that should trigger retry.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Exception | None = None
            delay = delay_seconds
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d failed: %s. Retrying in %.1fs...",
                            attempt,
                            max_attempts,
                            exc,
                            delay,
                        )
                        import time
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        logger.error(
                            "Attempt %d/%d failed: %s. No more retries.",
                            attempt,
                            max_attempts,
                            exc,
                        )
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def safe_execute(func: Callable[..., T], *args: Any, default: T | None = None, **kwargs: Any) -> T | None:
    """Execute function, return default on error instead of raising."""
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        logger.warning("safe_execute caught: %s", exc)
        return default
