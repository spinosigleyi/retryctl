"""Event hooks for retry and circuit breaker lifecycle events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional


@dataclass
class RetryEvent:
    """Emitted on each retry attempt."""
    attempt: int
    delay: float
    exception: Optional[BaseException] = None
    service_name: Optional[str] = None


@dataclass
class CircuitEvent:
    """Emitted when circuit breaker state changes."""
    service_name: str
    previous_state: str
    new_state: str
    failure_count: int = 0


OnRetryHook = Callable[[RetryEvent], Awaitable[None]]
OnCircuitChangeHook = Callable[[CircuitEvent], Awaitable[None]]


@dataclass
class HookRegistry:
    """Holds registered async hooks for retry and circuit events."""
    _on_retry: List[OnRetryHook] = field(default_factory=list)
    _on_circuit_change: List[OnCircuitChangeHook] = field(default_factory=list)

    def on_retry(self, fn: OnRetryHook) -> OnRetryHook:
        """Register a hook called before each retry sleep."""
        self._on_retry.append(fn)
        return fn

    def on_circuit_change(self, fn: OnCircuitChangeHook) -> OnCircuitChangeHook:
        """Register a hook called when circuit state changes."""
        self._on_circuit_change.append(fn)
        return fn

    async def emit_retry(self, event: RetryEvent) -> None:
        for hook in self._on_retry:
            await hook(event)

    async def emit_circuit_change(self, event: CircuitEvent) -> None:
        for hook in self._on_circuit_change:
            await hook(event)

    def clear(self) -> None:
        self._on_retry.clear()
        self._on_circuit_change.clear()


# Module-level default registry
default_hooks: HookRegistry = HookRegistry()
