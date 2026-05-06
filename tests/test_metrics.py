"""Tests for the metrics module."""

import pytest
from retryctl.metrics import (
    CircuitBreakerMetrics,
    RetryMetrics,
    MetricsRegistry,
    default_metrics,
)


class TestCircuitBreakerMetrics:
    def test_initial_state(self):
        m = CircuitBreakerMetrics()
        assert m.total_calls == 0
        assert m.failure_rate == 0.0

    def test_record_success(self):
        m = CircuitBreakerMetrics()
        m.record_success()
        assert m.total_calls == 1
        assert m.successful_calls == 1
        assert m.failure_rate == 0.0

    def test_record_failure(self):
        m = CircuitBreakerMetrics()
        m.record_failure()
        assert m.total_calls == 1
        assert m.failed_calls == 1
        assert m.failure_rate == 1.0

    def test_failure_rate_mixed(self):
        m = CircuitBreakerMetrics()
        m.record_success()
        m.record_failure()
        assert m.failure_rate == pytest.approx(0.5)

    def test_record_rejection_does_not_affect_total_calls(self):
        m = CircuitBreakerMetrics()
        m.record_rejection()
        assert m.total_calls == 0
        assert m.rejected_calls == 1

    def test_state_transition_counter(self):
        m = CircuitBreakerMetrics()
        m.record_state_transition()
        m.record_state_transition()
        assert m.state_transitions == 2


class TestRetryMetrics:
    def test_initial_state(self):
        m = RetryMetrics()
        assert m.total_attempts == 0
        assert m.total_retries == 0

    def test_record_success_attempt(self):
        m = RetryMetrics()
        m.record_attempt(success=True, retries_used=2)
        assert m.total_attempts == 1
        assert m.total_successes == 1
        assert m.total_failures == 0
        assert m.total_retries == 2

    def test_record_failed_attempt(self):
        m = RetryMetrics()
        m.record_attempt(success=False, retries_used=3)
        assert m.total_failures == 1
        assert m.total_retries == 3


class TestMetricsRegistry:
    @pytest.fixture(autouse=True)
    def fresh_registry(self):
        registry = MetricsRegistry()
        yield registry

    def test_circuit_returns_same_instance(self, fresh_registry):
        a = fresh_registry.circuit("svc")
        b = fresh_registry.circuit("svc")
        assert a is b

    def test_retry_returns_same_instance(self, fresh_registry):
        a = fresh_registry.retry("op")
        b = fresh_registry.retry("op")
        assert a is b

    def test_snapshot_contains_all_keys(self, fresh_registry):
        fresh_registry.circuit("svc").record_success()
        fresh_registry.retry("op").record_attempt(success=True, retries_used=1)
        snap = fresh_registry.snapshot()
        assert "svc" in snap["circuit_breakers"]
        assert "op" in snap["retry"]

    def test_reset_clears_all(self, fresh_registry):
        fresh_registry.circuit("svc").record_failure()
        fresh_registry.reset()
        assert fresh_registry.snapshot() == {"circuit_breakers": {}, "retry": {}}
