"""retryctl — Lightweight retry middleware with exponential backoff and circuit-breaker support."""

from retryctl.backoff import BackoffConfig, ExponentialBackoff
from retryctl.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from retryctl.registry import CircuitBreakerRegistry
from retryctl.decorators import with_retry
from retryctl.metrics import MetricsRegistry, default_metrics

__all__ = [
    "BackoffConfig",
    "ExponentialBackoff",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitBreakerRegistry",
    "with_retry",
    "MetricsRegistry",
    "default_metrics",
]

__version__ = "0.1.0"
