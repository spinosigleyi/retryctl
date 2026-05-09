"""Health snapshot and reporting for circuit breakers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from retryctl.circuit_breaker import CircuitState
from retryctl.metrics import CircuitBreakerMetrics
from retryctl.registry import CircuitBreakerRegistry


@dataclass(frozen=True)
class BreakerHealth:
    """Immutable snapshot of a single circuit breaker's health."""

    name: str
    state: CircuitState
    failure_rate: float
    total_calls: int
    total_failures: int
    total_successes: int
    total_rejections: int
    consecutive_failures: int

    @property
    def is_healthy(self) -> bool:
        """True when the circuit is closed and failure rate is below 50 %."""
        return self.state == CircuitState.CLOSED and self.failure_rate < 0.5


@dataclass
class HealthReport:
    """Aggregated health report for all tracked circuit breakers."""

    snapshots: List[BreakerHealth] = field(default_factory=list)

    @property
    def healthy(self) -> List[BreakerHealth]:
        return [s for s in self.snapshots if s.is_healthy]

    @property
    def unhealthy(self) -> List[BreakerHealth]:
        return [s for s in self.snapshots if not s.is_healthy]

    @property
    def all_healthy(self) -> bool:
        return len(self.unhealthy) == 0

    def as_dict(self) -> Dict:
        return {
            "all_healthy": self.all_healthy,
            "total": len(self.snapshots),
            "healthy_count": len(self.healthy),
            "unhealthy_count": len(self.unhealthy),
            "breakers": [
                {
                    "name": s.name,
                    "state": s.state.value,
                    "failure_rate": round(s.failure_rate, 4),
                    "total_calls": s.total_calls,
                    "total_failures": s.total_failures,
                    "total_successes": s.total_successes,
                    "total_rejections": s.total_rejections,
                    "consecutive_failures": s.consecutive_failures,
                    "is_healthy": s.is_healthy,
                }
                for s in self.snapshots
            ],
        }


def build_health_report(registry: CircuitBreakerRegistry) -> HealthReport:
    """Build a :class:`HealthReport` from all breakers in *registry*."""
    report = HealthReport()
    for name, breaker in registry.all().items():
        m: CircuitBreakerMetrics = breaker.metrics
        snapshot = BreakerHealth(
            name=name,
            state=breaker.state,
            failure_rate=m.failure_rate,
            total_calls=m.total_calls,
            total_failures=m.total_failures,
            total_successes=m.total_successes,
            total_rejections=m.total_rejections,
            consecutive_failures=m.consecutive_failures,
        )
        report.snapshots.append(snapshot)
    return report
