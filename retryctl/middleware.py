"""High-level retry middleware that integrates hooks, backoff, and circuit breaker."""
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Type, Tuple

from retryctl.backoff import BackoffConfig, ExponentialBackoff
from retryctl.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from retryctl.hooks import CircuitEvent, HookRegistry, RetryEvent, default_hooks
from retryctl.registry import CircuitBreakerRegistry, default_registry


async def execute_with_retry(
    fn: Callable[..., Any],
    *args: Any,
    service_name: str = "default",
    max_attempts: int = 3,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
    backoff_config: Optional[BackoffConfig] = None,
    registry: CircuitBreakerRegistry = default_registry,
    hooks: HookRegistry = default_hooks,
    **kwargs: Any,
) -> Any:
    """Execute *fn* with exponential backoff retries and circuit-breaker protection.

    Args:
        fn: Async callable to execute.
        service_name: Logical name used to look up the circuit breaker.
        max_attempts: Maximum number of total attempts (including the first).
        retryable_exceptions: Exception types that trigger a retry.
        backoff_config: Optional custom backoff configuration.
        registry: Circuit breaker registry to use.
        hooks: Hook registry for observability callbacks.
    """
    cfg = backoff_config or BackoffConfig()
    backoff = ExponentialBackoff(cfg)
    breaker: CircuitBreaker = registry.get_or_create(service_name)

    prev_state = breaker.state.value
    last_exc: Optional[BaseException] = None

    for attempt, delay in enumerate(backoff, start=1):
        if attempt > max_attempts:
            break

        # Emit circuit change hook if state changed since last iteration
        current_state = breaker.state.value
        if current_state != prev_state:
            await hooks.emit_circuit_change(
                CircuitEvent(
                    service_name=service_name,
                    previous_state=prev_state,
                    new_state=current_state,
                    failure_count=breaker._failure_count,
                )
            )
            prev_state = current_state

        try:
            result = await breaker.call(fn, *args, **kwargs)
            return result
        except CircuitBreakerOpenError:
            raise
        except retryable_exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt < max_attempts:
                await hooks.emit_retry(
                    RetryEvent(
                        attempt=attempt,
                        delay=delay,
                        exception=exc,
                        service_name=service_name,
                    )
                )
                await asyncio.sleep(delay)

    assert last_exc is not None
    raise last_exc
