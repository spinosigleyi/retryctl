"""Metrics collection for retry and circuit breaker events."""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict


@dataclass
class CircuitBreakerMetrics:
    """Tracks per-circuit-breaker statistics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # calls rejected while circuit is open
    state_transitions: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    def record_success(self) -> None:
        self.total_calls += 1
        self.successful_calls += 1

    def record_failure(self) -> None:
        self.total_calls += 1
        self.failed_calls += 1

    def record_rejection(self) -> None:
        self.rejected_calls += 1

    def record_state_transition(self) -> None:
        self.state_transitions += 1


@dataclass
class RetryMetrics:
    """Tracks retry-level statistics for a named operation."""
    total_attempts: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_retries: int = 0

    def record_attempt(self, *, success: bool, retries_used: int) -> None:
        self.total_attempts += 1
        self.total_retries += retries_used
        if success:
            self.total_successes += 1
        else:
            self.total_failures += 1


class MetricsRegistry:
    """Central registry for all retry and circuit breaker metrics."""

    def __init__(self) -> None:
        self._circuit: Dict[str, CircuitBreakerMetrics] = defaultdict(CircuitBreakerMetrics)
        self._retry: Dict[str, RetryMetrics] = defaultdict(RetryMetrics)

    def circuit(self, name: str) -> CircuitBreakerMetrics:
        return self._circuit[name]

    def retry(self, name: str) -> RetryMetrics:
        return self._retry[name]

    def snapshot(self) -> dict:
        return {
            "circuit_breakers": {
                k: vars(v) for k, v in self._circuit.items()
            },
            "retry": {
                k: vars(v) for k, v in self._retry.items()
            },
        }

    def reset(self) -> None:
        self._circuit.clear()
        self._retry.clear()


# Module-level default registry
default_metrics = MetricsRegistry()
