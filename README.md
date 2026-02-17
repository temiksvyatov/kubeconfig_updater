## kubeconfig_updater

Async Python CLI that reads cluster names from YAML, fetches kubeconfigs from Rancher, and stores them in Vault (KV v2). Designed for Jenkins execution.

### Requirements

- Python **3.11+**
- Environment variables:
  - `RANCHER_DEV_BASE_URL` (https)
  - `RANCHER_DEV_TOKEN`
  - `RANCHER_PROD_BASE_URL` (https)
  - `RANCHER_PROD_TOKEN`
  - (legacy fallback) `RANCHER_BASE_URL` (https) + `RANCHER_TOKEN` (used for both dev+prod)
  - `VAULT_BASE_URL` (https)
  - `VAULT_TOKEN`
  - `REQUEST_TIMEOUT` (seconds, optional, default 10)
  - `RETRY_COUNT` (optional, default 3; retries only on HTTP 5xx)
  - `LOG_LEVEL` (optional, default INFO)
  - `GLOBAL_TIMEOUT` (seconds, optional, default 600)

### Config file format

`clusters.yaml`:

```yaml
dev_clusters:
  - cluster-1
  - cluster-2

prod_clusters:
  - cluster-3
```

### Run locally

```bash
python3 -m venv venv
. venv/bin/activate
pip install -e ".[dev]"

python -m project.main --config clusters.yaml
python -m project.main --config clusters.yaml --dry-run
```

### Behavior notes

- **Idempotent:** reads existing Vault secret first; if checksum matches, skips write.
- **Parallel:** bounded concurrency via `--parallelism` (default 20).
- **Exit codes:**
  - 1: invalid YAML / config
  - 2: Rancher HTTP 4xx occurred
  - 3: Vault HTTP 403 (fail-fast)
  - 4: unexpected error

