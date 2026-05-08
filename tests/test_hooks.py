"""Tests for the HookRegistry and event dataclasses."""
import pytest

from retryctl.hooks import CircuitEvent, HookRegistry, RetryEvent


@pytest.fixture
def registry() -> HookRegistry:
    return HookRegistry()


class TestHookRegistry:
    @pytest.mark.asyncio
    async def test_on_retry_hook_called(self, registry: HookRegistry) -> None:
        received: list[RetryEvent] = []

        @registry.on_retry
        async def handler(event: RetryEvent) -> None:
            received.append(event)

        event = RetryEvent(attempt=1, delay=0.5, service_name="svc")
        await registry.emit_retry(event)
        assert len(received) == 1
        assert received[0].attempt == 1

    @pytest.mark.asyncio
    async def test_on_circuit_change_hook_called(self, registry: HookRegistry) -> None:
        received: list[CircuitEvent] = []

        @registry.on_circuit_change
        async def handler(event: CircuitEvent) -> None:
            received.append(event)

        event = CircuitEvent(
            service_name="svc", previous_state="closed", new_state="open", failure_count=5
        )
        await registry.emit_circuit_change(event)
        assert len(received) == 1
        assert received[0].new_state == "open"

    @pytest.mark.asyncio
    async def test_multiple_hooks_all_called(self, registry: HookRegistry) -> None:
        calls: list[int] = []

        @registry.on_retry
        async def first(event: RetryEvent) -> None:
            calls.append(1)

        @registry.on_retry
        async def second(event: RetryEvent) -> None:
            calls.append(2)

        await registry.emit_retry(RetryEvent(attempt=1, delay=0.1))
        assert calls == [1, 2]

    def test_clear_removes_all_hooks(self, registry: HookRegistry) -> None:
        @registry.on_retry
        async def dummy(event: RetryEvent) -> None:
            pass

        registry.clear()
        assert registry._on_retry == []
        assert registry._on_circuit_change == []

    @pytest.mark.asyncio
    async def test_emit_with_no_hooks_is_noop(self, registry: HookRegistry) -> None:
        # Should not raise even when no hooks are registered
        await registry.emit_retry(RetryEvent(attempt=1, delay=0.0))
        await registry.emit_circuit_change(
            CircuitEvent(service_name="x", previous_state="closed", new_state="open")
        )
