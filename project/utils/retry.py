from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from project.exceptions import RetryableHttpStatusError

T = TypeVar("T")

def _backoff_seconds(*, attempt: int, base: float = 0.5, cap: float = 8.0) -> float:
    # Deterministic exponential backoff (no jitter) for reproducible CI runs.
    return min(cap, base * (2**attempt))


async def retry_on_5xx(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int,
) -> T:
    """
    Retry an async operation only when it raises RetryableHttpStatusError (5xx).
    """

    last_err: RetryableHttpStatusError | None = None
    for attempt in range(retries + 1):
        try:
            return await operation()
        except RetryableHttpStatusError as e:
            last_err = e
            if attempt >= retries:
                raise
            await asyncio.sleep(_backoff_seconds(attempt=attempt))
    # Unreachable, but keeps mypy happy.
    assert last_err is not None
    raise last_err

