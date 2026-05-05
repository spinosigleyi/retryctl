# retryctl

Lightweight retry middleware library for Python async HTTP clients with exponential backoff and circuit-breaker support.

---

## Installation

```bash
pip install retryctl
```

---

## Usage

```python
import asyncio
import httpx
from retryctl import RetryClient, RetryConfig, CircuitBreaker

config = RetryConfig(
    max_attempts=5,
    backoff_factor=0.5,
    max_backoff=30.0,
    retry_on_status={429, 500, 502, 503, 504},
)

breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

async def main():
    async with RetryClient(config=config, circuit_breaker=breaker) as client:
        response = await client.get("https://api.example.com/data")
        print(response.json())

asyncio.run(main())
```

`RetryConfig` controls retry behavior, while `CircuitBreaker` trips open after a configurable number of consecutive failures and automatically recovers after a timeout.

---

## Configuration

| Parameter           | Default | Description                              |
|---------------------|---------|------------------------------------------|
| `max_attempts`      | `3`     | Maximum number of retry attempts         |
| `backoff_factor`    | `0.3`   | Multiplier for exponential backoff delay |
| `max_backoff`       | `60.0`  | Maximum backoff delay in seconds         |
| `retry_on_status`   | `{500}` | Set of HTTP status codes to retry on     |
| `failure_threshold` | `5`     | Failures before circuit breaker opens    |
| `recovery_timeout`  | `30`    | Seconds before circuit breaker resets    |

---

## Requirements

- Python 3.9+
- [httpx](https://www.python-httpx.org/) >= 0.24

---

## License

[MIT](LICENSE)