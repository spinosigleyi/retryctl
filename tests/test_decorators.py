"""Integration tests for the with_retry decorator."""

import asyncio
import pytest

from retryctl.backoff import BackoffConfig
from retryctl.circuit_breaker import CircuitBreakerConfig, CircuitBreakerOpenError
from retryctl.decorators import with_retry
from retryctl.registry import default_registry


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure the default registry is clean between tests."""
    default_registry.reset_all()
    yield
    default_registry.reset_all()


no_sleep_backoff = BackoffConfig(base_delay=0.0, max_delay=0.0, jitter=False)


class TestWithRetryDecorator:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        @with_retry(max_attempts=3, backoff=no_sleep_backoff)
        async def always_ok():
            return 42

        assert await always_ok() == 42

    @pytest.mark.asyncio
    async def test_retries_and_eventually_succeeds(self):
        calls = []

        @with_retry(max_attempts=3, backoff=no_sleep_backoff)
        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"

        result = await flaky()
        assert result == "ok"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts(self):
        @with_retry(max_attempts=3, backoff=no_sleep_backoff)
        async def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await always_fails()

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable_exception(self):
        calls = []

        @with_retry(
            max_attempts=3,
            backoff=no_sleep_backoff,
            retryable_exceptions=(ValueError,),
        )
        async def raises_key_error():
            calls.append(1)
            raise KeyError("nope")

        with pytest.raises(KeyError):
            await raises_key_error()

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_and_raises(self):
        cb_cfg = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60)

        @with_retry(
            max_attempts=5,
            backoff=no_sleep_backoff,
            circuit_breaker_name="test_svc",
            circuit_breaker_config=cb_cfg,
        )
        async def always_fails():
            raise ConnectionError("down")

        with pytest.raises((ConnectionError, CircuitBreakerOpenError)):
            await always_fails()

        cb = default_registry.get("test_svc")
        assert cb is not None
        # After repeated failures the circuit should be open
        assert not cb.allow_request()

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_raises_immediately(self):
        cb_cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60)
        cb = default_registry.get_or_create("instant_open", cb_cfg)
        cb.record_failure()  # force open

        @with_retry(
            max_attempts=3,
            backoff=no_sleep_backoff,
            circuit_breaker_name="instant_open",
        )
        async def should_not_run():
            return "reached"

        with pytest.raises(CircuitBreakerOpenError):
            await should_not_run()
