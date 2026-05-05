"""Exponential backoff strategies for retry delays."""

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackoffConfig:
    """Configuration for exponential backoff."""

    base_delay: float = 0.5
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1


class ExponentialBackoff:
    """Computes exponential backoff delays with optional jitter."""

    def __init__(self, config: Optional[BackoffConfig] = None) -> None:
        self.config = config or BackoffConfig()

    def compute(self, attempt: int) -> float:
        """Return the delay in seconds for the given attempt number (0-indexed)."""
        if attempt < 0:
            raise ValueError("attempt must be >= 0")

        delay = self.config.base_delay * (self.config.multiplier ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            spread = delay * self.config.jitter_range
            delay += random.uniform(-spread, spread)
            delay = max(0.0, delay)

        return delay

    def __iter__(self):
        """Iterate over successive backoff delays indefinitely."""
        attempt = 0
        while True:
            yield self.compute(attempt)
            attempt += 1
