"""Global registry for named circuit breakers."""
from __future__ import annotations

from threading import Lock
from typing import Dict, Iterator, Optional, Tuple

from retryctl.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class CircuitBreakerRegistry:
    """Thread-safe registry that maps names to :class:`CircuitBreaker` instances."""

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Return existing breaker or create one with *config*."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    config=config or CircuitBreakerConfig(),
                )
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Return the breaker for *name*, or ``None`` if not registered."""
        with self._lock:
            return self._breakers.get(name)

    def reset(self, name: str) -> None:
        """Remove the breaker registered under *name*."""
        with self._lock:
            self._breakers.pop(name, None)

    def reset_all(self) -> None:
        """Remove every registered breaker."""
        with self._lock:
            self._breakers.clear()

    def all(self) -> Dict[str, CircuitBreaker]:
        """Return a shallow copy of the internal breaker mapping."""
        with self._lock:
            return dict(self._breakers)

    def __len__(self) -> int:
        with self._lock:
            return len(self._breakers)

    def __iter__(self) -> Iterator[Tuple[str, CircuitBreaker]]:
        with self._lock:
            items = list(self._breakers.items())
        return iter(items)


# Module-level default registry
default_registry: CircuitBreakerRegistry = CircuitBreakerRegistry()
