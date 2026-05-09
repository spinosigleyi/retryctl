"""Circuit breaker state snapshots for observability and diagnostics."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from retryctl.circuit_breaker import CircuitState
from retryctl.registry import CircuitBreakerRegistry


@dataclass(frozen=True)
class BreakerSnapshot:
    """Point-in-time snapshot of a single circuit breaker."""

    name: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[float]
    captured_at: float = field(default_factory=time.monotonic)

    @property
    def age_seconds(self) -> float:
        """Seconds elapsed since the snapshot was captured."""
        return time.monotonic() - self.captured_at


@dataclass(frozen=True)
class RegistrySnapshot:
    """Aggregated snapshot of all circuit breakers in a registry."""

    breakers: Dict[str, BreakerSnapshot]
    captured_at: float = field(default_factory=time.monotonic)

    @property
    def open_breakers(self) -> List[str]:
        return [
            name
            for name, snap in self.breakers.items()
            if snap.state == CircuitState.OPEN
        ]

    @property
    def half_open_breakers(self) -> List[str]:
        return [
            name
            for name, snap in self.breakers.items()
            if snap.state == CircuitState.HALF_OPEN
        ]

    @property
    def all_closed(self) -> bool:
        return all(s.state == CircuitState.CLOSED for s in self.breakers.values())


def snapshot_breaker(name: str, registry: CircuitBreakerRegistry) -> Optional[BreakerSnapshot]:
    """Capture a snapshot for a single named breaker, or None if not found."""
    breaker = registry.get(name)
    if breaker is None:
        return None
    return BreakerSnapshot(
        name=name,
        state=breaker.state,
        failure_count=breaker._failure_count,
        success_count=breaker._success_count,
        last_failure_time=breaker._last_failure_time,
    )


def snapshot_registry(registry: CircuitBreakerRegistry) -> RegistrySnapshot:
    """Capture snapshots for every breaker currently in the registry."""
    snaps: Dict[str, BreakerSnapshot] = {}
    for name in list(registry._breakers.keys()):
        snap = snapshot_breaker(name, registry)
        if snap is not None:
            snaps[name] = snap
    return RegistrySnapshot(breakers=snaps)
