"""Core retry middleware with exponential backoff support."""

import asyncio
import logging
from typing import Callable, Optional, Tuple, Type

from retryctl.backoff import BackoffConfig, ExponentialBackoff

logger = logging.getLogger(__name__)

DEFAULT_RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


async def retry(
    func: Callable,
    *args,
    max_attempts: int = 3,
    backoff_config: Optional[BackoffConfig] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    **kwargs,
):
    """Execute an async callable with exponential backoff retry logic.

    Args:
        func: Async callable to execute.
        max_attempts: Maximum number of total attempts (including the first).
        backoff_config: Backoff configuration; uses defaults if None.
        retryable_exceptions: Exception types that trigger a retry.
        on_retry: Optional callback(attempt, exception, delay) called before each retry.

    Returns:
        The return value of ``func`` on success.

    Raises:
        The last exception raised by ``func`` after all attempts are exhausted.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    backoff = ExponentialBackoff(backoff_config)
    last_exc: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except retryable_exceptions as exc:
            last_exc = exc
            if attempt + 1 >= max_attempts:
                break
            delay = backoff.compute(attempt)
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.2fs.",
                attempt + 1,
                max_attempts,
                exc,
                delay,
            )
            if on_retry is not None:
                on_retry(attempt + 1, exc, delay)
            await asyncio.sleep(delay)

    raise last_exc
