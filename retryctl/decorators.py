"""Async decorator that wires retry logic with a circuit breaker."""

import asyncio
import functools
from typing import Callable, Optional, Tuple, Type

from retryctl.backoff import BackoffConfig, ExponentialBackoff
from retryctl.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
)
from retryctl.registry import default_registry


def with_retry(
    *,
    max_attempts: int = 3,
    backoff: Optional[BackoffConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """
    Decorator factory that adds retry + optional circuit-breaker logic
    to any async function.

    Args:
        max_attempts: Total number of attempts before giving up.
        backoff: BackoffConfig controlling exponential delay.
        circuit_breaker_name: If set, use/create a named circuit breaker.
        circuit_breaker_config: Config for the circuit breaker (if creating).
        retryable_exceptions: Only retry on these exception types.
    """
    backoff_cfg = backoff or BackoffConfig()

    def decorator(func: Callable) -> Callable:
        cb: Optional[CircuitBreaker] = None
        if circuit_breaker_name:
            cb = default_registry.get_or_create(
                circuit_breaker_name, circuit_breaker_config
            )

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Optional[BaseException] = None
            delays = ExponentialBackoff(backoff_cfg)

            for attempt, delay in enumerate(delays):
                if attempt >= max_attempts:
                    break

                if cb is not None and not cb.allow_request():
                    raise CircuitBreakerOpenError(
                        circuit_breaker_name, cb.retry_after()  # type: ignore[arg-type]
                    )

                try:
                    result = await func(*args, **kwargs)
                    if cb is not None:
                        cb.record_success()
                    return result
                except retryable_exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if cb is not None:
                        cb.record_failure()
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay)

            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
