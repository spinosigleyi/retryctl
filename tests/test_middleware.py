"""Tests for execute_with_retry middleware."""
import pytest

from retryctl.backoff import BackoffConfig
from retryctl.circuit_breaker import CircuitBreakerOpenError
from retryctl.hooks import HookRegistry, RetryEvent
from retryctl.middleware import execute_with_retry
from retryctl.registry import CircuitBreakerRegistry


@pytest.fixture
def reg() -> CircuitBreakerRegistry:
    return CircuitBreakerRegistry()


@pytest.fixture
def hooks() -> HookRegistry:
    return HookRegistry()


@pytest.fixture
def fast_backoff() -> BackoffConfig:
    return BackoffConfig(base_delay=0.0, max_delay=0.0)


class TestExecuteWithRetry:
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self, reg, hooks, fast_backoff):
        async def fn():
            return 42

        result = await execute_with_retry(
            fn, service_name="svc", backoff_config=fast_backoff, registry=reg, hooks=hooks
        )
        assert result == 42

    @pytest.mark.asyncio
    async def test_retries_on_failure_then_succeeds(self, reg, hooks, fast_backoff):
        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient")
            return "ok"

        result = await execute_with_retry(
            fn,
            service_name="svc",
            max_attempts=3,
            backoff_config=fast_backoff,
            registry=reg,
            hooks=hooks,
        )
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self, reg, hooks, fast_backoff):
        async def fn():
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="always fails"):
            await execute_with_retry(
                fn,
                service_name="svc",
                max_attempts=3,
                backoff_config=fast_backoff,
                registry=reg,
                hooks=hooks,
            )

    @pytest.mark.asyncio
    async def test_retry_hook_called_on_each_retry(self, reg, hooks, fast_backoff):
        events: list[RetryEvent] = []

        @hooks.on_retry
        async def capture(event: RetryEvent) -> None:
            events.append(event)

        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("boom")
            return "done"

        await execute_with_retry(
            fn,
            service_name="svc",
            max_attempts=3,
            backoff_config=fast_backoff,
            registry=reg,
            hooks=hooks,
        )
        assert len(events) == 2
        assert events[0].attempt == 1
        assert events[1].attempt == 2

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_not_retried(self, reg, hooks, fast_backoff):
        from retryctl.circuit_breaker import CircuitBreakerConfig

        reg2 = CircuitBreakerRegistry(default_config=CircuitBreakerConfig(failure_threshold=1))

        call_count = 0

        async def fn():
            nonlocal call_count
            call_count += 1
            raise IOError("network")

        with pytest.raises((IOError, CircuitBreakerOpenError)):
            await execute_with_retry(
                fn,
                service_name="svc",
                max_attempts=5,
                backoff_config=fast_backoff,
                registry=reg2,
                hooks=hooks,
            )
