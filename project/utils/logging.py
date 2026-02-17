from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "message": record.getMessage(),
            "cluster_name": getattr(record, "cluster_name", "global"),
            "action": getattr(record, "action", "log"),
            "result": getattr(record, "result", "info"),
            "duration_ms": getattr(record, "duration_ms", 0),
        }
        # Allow extra structured fields, but avoid accidentally dumping secrets.
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            for k, v in extra_fields.items():
                if k not in payload:
                    payload[k] = v
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(*, level: str) -> logging.Logger:
    logger = logging.getLogger("kubeconfig_updater")
    logger.setLevel(level)
    logger.propagate = False

    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


@dataclass(frozen=True, slots=True)
class Timer:
    start: float

    @staticmethod
    def start_now() -> "Timer":
        return Timer(start=time.monotonic())

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.start) * 1000)


def log_event(
    logger: logging.Logger,
    *,
    cluster_name: str,
    action: str,
    result: str,
    duration_ms: int,
    level: int = logging.INFO,
    message: str = "",
    extra_fields: dict[str, Any] | None = None,
) -> None:
    logger.log(
        level,
        message,
        extra={
            "cluster_name": cluster_name,
            "action": action,
            "result": result,
            "duration_ms": duration_ms,
            "extra_fields": extra_fields or {},
        },
    )

