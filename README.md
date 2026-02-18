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

### Run locally (with venv)

```bash
python3 -m venv venv
. venv/bin/activate
pip install -e ".[dev]"

python -m project.main --config clusters.yaml
python -m project.main --config clusters.yaml --dry-run
```

### Run without installing dependencies every time (vendored / closed network)

On a machine with internet, populate `vendor/` once:

```bash
make vendor
```

Then copy the whole project (including `vendor/`) to the target. On the target you only need Python 3.11+; no `pip install` is required. Run as usual:

```bash
python3 -m project.main --config clusters.yaml
```

In CI/Jenkins, run `make vendor` before packaging or deploying so the artifact already contains dependencies.

### Behavior notes

- **Idempotent:** reads existing Vault secret first; if checksum matches, skips write.
- **Parallel:** bounded concurrency via `--parallelism` (default 20).
- **Exit codes:**
  - 1: invalid YAML / config
  - 2: Rancher HTTP 4xx occurred
  - 3: Vault HTTP 403 (fail-fast)
  - 4: unexpected error

