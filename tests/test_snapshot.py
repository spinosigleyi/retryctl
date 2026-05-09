"""Tests for retryctl.snapshot — circuit breaker state snapshots."""
import pytest

from retryctl.circuit_breaker import CircuitBreakerConfig, CircuitState
from retryctl.registry import CircuitBreakerRegistry
from retryctl.snapshot import (
    BreakerSnapshot,
    RegistrySnapshot,
    snapshot_breaker,
    snapshot_registry,
)


@pytest.fixture()
def registry():
    reg = CircuitBreakerRegistry()
    yield reg
    reg.reset_all()


def _cfg(threshold: int = 3) -> CircuitBreakerConfig:
    return CircuitBreakerConfig(failure_threshold=threshold, recovery_timeout=60)


class TestSnapshotBreaker:
    def test_returns_none_for_unknown_name(self, registry):
        assert snapshot_breaker("ghost", registry) is None

    def test_captures_closed_state(self, registry):
        registry.get_or_create("svc", _cfg())
        snap = snapshot_breaker("svc", registry)
        assert snap is not None
        assert snap.name == "svc"
        assert snap.state == CircuitState.CLOSED
        assert snap.failure_count == 0

    def test_captures_open_state_after_failures(self, registry):
        cfg = _cfg(threshold=2)
        breaker = registry.get_or_create("svc", cfg)
        for _ in range(2):
            breaker.record_failure()
        snap = snapshot_breaker("svc", registry)
        assert snap.state == CircuitState.OPEN
        assert snap.failure_count == 2

    def test_age_increases_over_time(self, registry):
        import time

        registry.get_or_create("svc", _cfg())
        snap = snapshot_breaker("svc", registry)
        time.sleep(0.05)
        assert snap.age_seconds >= 0.04


class TestRegistrySnapshot:
    def test_empty_registry_yields_no_breakers(self, registry):
        snap = snapshot_registry(registry)
        assert isinstance(snap, RegistrySnapshot)
        assert snap.breakers == {}
        assert snap.all_closed is True

    def test_all_closed_when_no_failures(self, registry):
        registry.get_or_create("a", _cfg())
        registry.get_or_create("b", _cfg())
        snap = snapshot_registry(registry)
        assert snap.all_closed is True
        assert snap.open_breakers == []

    def test_open_breakers_listed(self, registry):
        cfg = _cfg(threshold=1)
        breaker = registry.get_or_create("fragile", cfg)
        breaker.record_failure()
        registry.get_or_create("stable", _cfg(threshold=10))
        snap = snapshot_registry(registry)
        assert "fragile" in snap.open_breakers
        assert "stable" not in snap.open_breakers
        assert snap.all_closed is False

    def test_half_open_breakers_listed(self, registry):
        from retryctl.circuit_breaker import CircuitBreakerConfig

        cfg = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0)
        breaker = registry.get_or_create("probe", cfg)
        breaker.record_failure()
        # Transition to HALF_OPEN by allowing the recovery window to pass
        import time
        time.sleep(0.01)
        breaker.allow_request()  # triggers HALF_OPEN transition
        snap = snapshot_registry(registry)
        assert "probe" in snap.half_open_breakers
