"""Tests for exponential backoff and retry logic."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from retryctl.backoff import BackoffConfig, ExponentialBackoff
from retryctl.retry import retry


# ---------------------------------------------------------------------------
# BackoffConfig / ExponentialBackoff
# ---------------------------------------------------------------------------

class TestExponentialBackoff:
    def test_first_attempt_equals_base_delay_no_jitter(self):
        cfg = BackoffConfig(base_delay=1.0, jitter=False)
        bo = ExponentialBackoff(cfg)
        assert bo.compute(0) == pytest.approx(1.0)

    def test_delay_doubles_each_attempt(self):
        cfg = BackoffConfig(base_delay=1.0, multiplier=2.0, jitter=False)
        bo = ExponentialBackoff(cfg)
        assert bo.compute(1) == pytest.approx(2.0)
        assert bo.compute(2) == pytest.approx(4.0)

    def test_delay_capped_at_max(self):
        cfg = BackoffConfig(base_delay=1.0, max_delay=5.0, multiplier=10.0, jitter=False)
        bo = ExponentialBackoff(cfg)
        assert bo.compute(3) == pytest.approx(5.0)

    def test_negative_attempt_raises(self):
        bo = ExponentialBackoff()
        with pytest.raises(ValueError):
            bo.compute(-1)

    def test_iter_yields_increasing_delays(self):
        cfg = BackoffConfig(base_delay=0.1, multiplier=2.0, max_delay=10.0, jitter=False)
        bo = ExponentialBackoff(cfg)
        delays = [next(iter(bo)) for _ in range(4)]
        # Grab fresh iterator
        it = iter(bo)
        d0, d1, d2 = next(it), next(it), next(it)
        assert d1 > d0
        assert d2 > d1


# ---------------------------------------------------------------------------
# retry()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    mock = AsyncMock(return_value="ok")
    result = await retry(mock, max_attempts=3)
    assert result == "ok"
    mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failures():
    mock = AsyncMock(side_effect=[ConnectionError("down"), ConnectionError("down"), "ok"])
    cfg = BackoffConfig(base_delay=0.01, jitter=False)
    result = await retry(mock, max_attempts=3, backoff_config=cfg)
    assert result == "ok"
    assert mock.await_count == 3


@pytest.mark.asyncio
async def test_retry_raises_after_all_attempts_exhausted():
    mock = AsyncMock(side_effect=ConnectionError("always down"))
    cfg = BackoffConfig(base_delay=0.01, jitter=False)
    with pytest.raises(ConnectionError):
        await retry(mock, max_attempts=3, backoff_config=cfg)
    assert mock.await_count == 3


@pytest.mark.asyncio
async def test_retry_does_not_catch_non_retryable_exception():
    mock = AsyncMock(side_effect=ValueError("bad input"))
    with pytest.raises(ValueError):
        await retry(mock, max_attempts=3)
    mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_retry_callback_invoked():
    calls = []
    mock = AsyncMock(side_effect=[ConnectionError("err"), "ok"])
    cfg = BackoffConfig(base_delay=0.01, jitter=False)

    def on_retry(attempt, exc, delay):
        calls.append((attempt, type(exc).__name__, delay))

    await retry(mock, max_attempts=2, backoff_config=cfg, on_retry=on_retry)
    assert len(calls) == 1
    assert calls[0][0] == 1
    assert calls[0][1] == "ConnectionError"


@pytest.mark.asyncio
async def test_retry_invalid_max_attempts():
    with pytest.raises(ValueError):
        await retry(AsyncMock(), max_attempts=0)
