"""Tests for retryctl.health — health snapshot and reporting."""
from __future__ import annotations

import pytest

from retryctl.circuit_breaker import CircuitBreakerConfig, CircuitState
from retryctl.health import BreakerHealth, HealthReport, build_health_report
from retryctl.registry import CircuitBreakerRegistry


@pytest.fixture()
def registry() -> CircuitBreakerRegistry:
    reg = CircuitBreakerRegistry()
    return reg


class TestBreakerHealth:
    def _make(self, state: CircuitState, failure_rate: float) -> BreakerHealth:
        return BreakerHealth(
            name="svc",
            state=state,
            failure_rate=failure_rate,
            total_calls=10,
            total_failures=int(failure_rate * 10),
            total_successes=10 - int(failure_rate * 10),
            total_rejections=0,
            consecutive_failures=0,
        )

    def test_closed_low_failure_rate_is_healthy(self):
        h = self._make(CircuitState.CLOSED, 0.1)
        assert h.is_healthy is True

    def test_open_circuit_is_not_healthy(self):
        h = self._make(CircuitState.OPEN, 0.0)
        assert h.is_healthy is False

    def test_closed_high_failure_rate_is_not_healthy(self):
        h = self._make(CircuitState.CLOSED, 0.8)
        assert h.is_healthy is False

    def test_half_open_is_not_healthy(self):
        h = self._make(CircuitState.HALF_OPEN, 0.1)
        assert h.is_healthy is False


class TestHealthReport:
    def _snapshot(self, name: str, healthy: bool) -> BreakerHealth:
        state = CircuitState.CLOSED if healthy else CircuitState.OPEN
        rate = 0.1 if healthy else 0.9
        return BreakerHealth(
            name=name,
            state=state,
            failure_rate=rate,
            total_calls=10,
            total_failures=int(rate * 10),
            total_successes=10 - int(rate * 10),
            total_rejections=0,
            consecutive_failures=0,
        )

    def test_all_healthy_when_empty(self):
        report = HealthReport()
        assert report.all_healthy is True

    def test_all_healthy_with_healthy_breakers(self):
        report = HealthReport(snapshots=[self._snapshot("a", True), self._snapshot("b", True)])
        assert report.all_healthy is True
        assert len(report.healthy) == 2
        assert len(report.unhealthy) == 0

    def test_not_all_healthy_when_one_open(self):
        report = HealthReport(snapshots=[self._snapshot("a", True), self._snapshot("b", False)])
        assert report.all_healthy is False
        assert len(report.unhealthy) == 1

    def test_as_dict_structure(self):
        report = HealthReport(snapshots=[self._snapshot("x", True)])
        d = report.as_dict()
        assert d["total"] == 1
        assert d["all_healthy"] is True
        assert d["breakers"][0]["name"] == "x"
        assert "state" in d["breakers"][0]
        assert "failure_rate" in d["breakers"][0]


class TestBuildHealthReport:
    def test_empty_registry_yields_empty_report(self, registry):
        report = build_health_report(registry)
        assert len(report.snapshots) == 0
        assert report.all_healthy is True

    def test_report_contains_registered_breakers(self, registry):
        registry.get_or_create("alpha")
        registry.get_or_create("beta")
        report = build_health_report(registry)
        names = {s.name for s in report.snapshots}
        assert names == {"alpha", "beta"}

    def test_fresh_breaker_is_healthy(self, registry):
        registry.get_or_create("gamma", CircuitBreakerConfig(failure_threshold=5))
        report = build_health_report(registry)
        assert report.all_healthy is True

    def test_report_reflects_open_breaker(self, registry):
        cfg = CircuitBreakerConfig(failure_threshold=2)
        breaker = registry.get_or_create("delta", cfg)
        for _ in range(3):
            try:
                breaker.record_failure()
            except Exception:
                pass
        report = build_health_report(registry)
        delta = next(s for s in report.snapshots if s.name == "delta")
        assert delta.state == CircuitState.OPEN
        assert delta.is_healthy is False
