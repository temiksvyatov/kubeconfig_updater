# Coding Standards

## Language & Runtime
- Python **3.11+** only. Use `match` statements, `tomllib`, `ExceptionGroup` where appropriate.
- Async-first: use `asyncio` + `aiohttp` for all HTTP calls.

## Type Annotations
- You ALWAYS annotate every function signature (args + return type).
- You ALWAYS use `from __future__ import annotations` at top of each file.
- Use `pydantic.BaseModel` for all data structures passed between functions.

## Project Structure
```
.
├── main.py                  # entrypoint: parse args, load settings, run asyncio.run(sync())
├── settings.py              # pydantic-settings Settings class
├── rancher.py               # RancherClient (async context manager)
├── vault.py                 # VaultClient (async context manager)
├── clusters.py              # validate_clusters_file(), ClusterConfig model
├── sync.py                  # core sync_cluster(), sync_all() logic
├── utils.py                 # with_retry, normalize_kubeconfig, kubeconfigs_are_equal
├── clusters.yaml            # cluster names
├── Dockerfile
├── Jenkinsfile
├── requirements.txt
├── requirements-dev.txt     # pytest, pytest-asyncio, pytest-cov, ruff, mypy
└── tests/
    ├── test_clusters.py
    ├── test_sync.py
    └── test_utils.py
```

## Logging
- Use `structlog` with JSON renderer in CI, console renderer locally.
- Detect CI via `os.getenv("CI") == "true"` or `os.getenv("JENKINS_URL")`.

```python
import structlog, os

def configure_logging() -> None:
    renderer = (
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

log = structlog.get_logger()
```

## Error Handling
- You ALWAYS raise domain-specific exceptions (`RancherAPIError`, `VaultAPIError`, `ClusterNotFoundError`).
- You NEVER use bare `except Exception` without re-raising or explicit logging.
- HTTP errors: always include `status_code`, `url`, and response body snippet in exception message.

## Testing
- You ALWAYS write tests for: `validate_clusters_file`, `kubeconfigs_are_equal`, `sync_cluster` (mocked HTTP).
- Use `pytest-asyncio` for async tests.
- Minimum coverage target: **80%**.
- Mock HTTP with `aioresponses` library.

## Linting & Formatting
- `ruff` for linting + formatting (replaces black + flake8).
- `mypy --strict` must pass with zero errors.

## Rules
- You NEVER use `requests` library — always `aiohttp`.
- You NEVER use `print()` — always `log.info/warning/error`.
- You ALWAYS handle `aiohttp.ClientError` and `asyncio.TimeoutError` at the retry boundary.
- All public functions MUST have docstrings.
