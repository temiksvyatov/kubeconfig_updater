# Script Requirements & Algorithm

## Execution Order (STRICT — never reorder)

### Step 1: Validate clusters.yaml
```python
import yaml
from pathlib import Path

def validate_clusters_file(path: str) -> dict:
    """Must raise ValueError with descriptive message on any failure."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"clusters.yaml not found: {path}")
    
    raw = p.read_text()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("clusters.yaml must be a mapping")
    
    allowed_envs = {"dev", "prod"}
    for env in allowed_envs:
        clusters = data.get(env, [])
        if not isinstance(clusters, list):
            raise ValueError(f"'{env}' must be a list")
        for name in clusters:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Invalid cluster name in '{env}': {name!r}")
    
    all_clusters = data.get("dev", []) + data.get("prod", [])
    if not all_clusters:
        raise ValueError("clusters.yaml contains no clusters")
    
    return data  # {"dev": [...], "prod": [...]}
```

### Step 2: Build Rancher cluster ID mappings
- Call `build_cluster_map(dev_rancher)` and `build_cluster_map(prod_rancher)` concurrently.
- For each name in `clusters.yaml["dev"]`, look up ID in dev map.
- For each name in `clusters.yaml["prod"]`, look up ID in prod map.
- If any name is missing from the respective Rancher → log error, add to `failed_clusters`, continue.

### Step 3: Per-cluster sync loop
For each cluster (concurrency limited to 5 with `asyncio.Semaphore`):

1. `GET kubeconfig from Rancher` (with retry)
2. `GET kubeconfig from Vault` (with retry) — None if 404
3. Compare (see normalization below)
4. If different or Vault has None → write to Vault
5. If identical → log "up-to-date", skip

### kubeconfig Normalization & Comparison
```python
import yaml

def normalize_kubeconfig(raw: str) -> dict:
    """Parse YAML, strip comments (yaml.safe_load drops them), return dict."""
    return yaml.safe_load(raw)

def kubeconfigs_are_equal(a: str, b: str | None) -> bool:
    if b is None:
        return False
    try:
        return normalize_kubeconfig(a) == normalize_kubeconfig(b)
    except yaml.YAMLError:
        return False
```

### Step 4: Final report
- Log summary: total processed, updated, skipped (up-to-date), failed.
- Exit code `0` if no failures, `1` if any cluster failed.

## Retry Decorator
```python
import asyncio
import functools
from typing import TypeVar, Callable, Awaitable

T = TypeVar("T")

def with_retry(attempts: int = 3, backoff: float = 1.0):
    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    if attempt == attempts:
                        raise
                    wait = backoff * (2 ** (attempt - 1))
                    await asyncio.sleep(wait)
        return wrapper
    return decorator
```

## Rules
- You ALWAYS run steps in the order above — never skip validation.
- You NEVER abort the entire run on a single cluster failure — collect errors and report at end.
- You ALWAYS use `asyncio.Semaphore(5)` to cap concurrent Rancher/Vault requests.
- Exit with code `1` if any cluster failed; `0` if all succeeded (even if some were skipped as up-to-date).
