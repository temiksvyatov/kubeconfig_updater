from __future__ import annotations

import asyncio
import functools
from typing import Any, Awaitable, Callable, TypeVar

import aiohttp
import structlog
import yaml


T = TypeVar("T")

log = structlog.get_logger()


def configure_logging() -> None:
    """Configure structlog for either CI (JSON) or local (console) usage."""

    import os

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if os.getenv("CI") or os.getenv("JENKINS_URL")
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            renderer,
        ]
    )


def with_retry(
    attempts: int = 3,
    backoff: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
    ),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry an async function with exponential backoff on selected exceptions."""

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    if attempt == attempts:
                        log.error(
                            "operation_failed_after_retries",
                            attempt=attempt,
                            max_attempts=attempts,
                            error=str(exc),
                        )
                        raise
                    wait = backoff * (2 ** (attempt - 1))
                    log.warning(
                        "operation_retry",
                        attempt=attempt,
                        max_attempts=attempts,
                        wait_seconds=wait,
                        error=str(exc),
                    )
                    await asyncio.sleep(wait)

        return wrapper

    return decorator


def normalize_kubeconfig(raw: str) -> Any:
    """Normalize kubeconfig YAML to a Python structure for comparison."""

    return yaml.safe_load(raw)


def kubeconfigs_are_equal(a: str, b: str | None) -> bool:
    """Return True if two kubeconfig YAML documents are equivalent."""

    if b is None:
        return False

    try:
        a_norm = normalize_kubeconfig(a)
        b_norm = normalize_kubeconfig(b)
    except yaml.YAMLError:
        return False

    return a_norm == b_norm


__all__ = [
    "configure_logging",
    "with_retry",
    "normalize_kubeconfig",
    "kubeconfigs_are_equal",
    "log",
]

