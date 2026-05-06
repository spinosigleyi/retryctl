"""Unit tests for CircuitBreaker and CircuitBreakerRegistry."""

import time
from unittest.mock import patch

import pytest

from retryctl.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from retryctl.registry import CircuitBreakerRegistry


class TestCircuitBreakerStates:
    def _breaker(self, **kwargs) -> CircuitBreaker:
        return CircuitBreaker("test", CircuitBreakerConfig(**kwargs))

    def test_initial_state_is_closed(self):
        cb = self._breaker()
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_failure_threshold(self):
        cb = self._breaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_does_not_open_below_threshold(self):
        cb = self._breaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_open_circuit_rejects_requests(self):
        cb = self._breaker(failure_threshold=1)
        cb.record_failure()
        assert not cb.allow_request()

    def test_transitions_to_half_open_after_timeout(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_allows_limited_calls(self):
        cb = self._breaker(
            failure_threshold=1, recovery_timeout=0.05, half_open_max_calls=1
        )
        cb.record_failure()
        time.sleep(0.06)
        assert cb.allow_request() is True
        assert cb.allow_request() is False  # second call blocked

    def test_closes_after_enough_successes_in_half_open(self):
        cb = self._breaker(
            failure_threshold=1, recovery_timeout=0.05, success_threshold=2,
            half_open_max_calls=2
        )
        cb.record_failure()
        time.sleep(0.06)
        _ = cb.state  # trigger transition to HALF_OPEN
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        _ = cb.state  # trigger HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_retry_after_decreases_over_time(self):
        cb = self._breaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        r1 = cb.retry_after()
        time.sleep(0.05)
        r2 = cb.retry_after()
        assert r2 < r1


class TestCircuitBreakerRegistry:
    def test_get_or_create_returns_same_instance(self):
        reg = CircuitBreakerRegistry()
        cb1 = reg.get_or_create("svc")
        cb2 = reg.get_or_create("svc")
        assert cb1 is cb2

    def test_get_returns_none_for_unknown(self):
        reg = CircuitBreakerRegistry()
        assert reg.get("missing") is None

    def test_reset_removes_breaker(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("svc")
        assert reg.reset("svc") is True
        assert reg.get("svc") is None

    def test_reset_all_clears_registry(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("a")
        reg.get_or_create("b")
        reg.reset_all()
        assert len(reg) == 0

    def test_list_names(self):
        reg = CircuitBreakerRegistry()
        reg.get_or_create("x")
        reg.get_or_create("y")
        assert set(reg.list_names()) == {"x", "y"}
