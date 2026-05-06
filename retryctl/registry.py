"""Global registry for named CircuitBreaker instances."""

from threading import Lock
from typing import Dict, Optional

from retryctl.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


class CircuitBreakerRegistry:
    """Thread-safe registry that manages named circuit breakers."""

    def __init__(self) -> None:
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Return an existing breaker or create a new one with the given config."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Return an existing breaker or None."""
        with self._lock:
            return self._breakers.get(name)

    def reset(self, name: str) -> bool:
        """Remove a breaker from the registry. Returns True if it existed."""
        with self._lock:
            if name in self._breakers:
                del self._breakers[name]
                return True
            return False

    def reset_all(self) -> None:
        """Clear all registered breakers."""
        with self._lock:
            self._breakers.clear()

    def list_names(self):
        """Return a snapshot of all registered breaker names."""
        with self._lock:
            return list(self._breakers.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._breakers)


# Module-level default registry
default_registry = CircuitBreakerRegistry()
