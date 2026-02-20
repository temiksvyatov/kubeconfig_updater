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

### Jenkins (webhook → run Docker image)

The pipeline runs the app from a Docker image stored in your corporate registry (no Python/venv on the agent).

1. **Build and push the image** (e.g. in a separate build pipeline or locally):
   ```bash
   docker build -t registry.example.com/your-group/kubeconfig-updater:latest .
   docker push registry.example.com/your-group/kubeconfig-updater:latest
   ```
2. **In the Jenkinsfile**, set `DOCKER_REGISTRY` and `DOCKER_IMAGE` to your registry and image path.
3. **In Jenkins**, create credentials:
   - `docker-registry-credentials`: Username and password for the Docker registry.
   - `rancher_dev_url`, `rancher_dev_token`, `rancher_prod_url`, `rancher_prod_token`, `vault_url`, `vault_token`: for Rancher and Vault (same as before).

The job checks out the repo (for `clusters.yaml`), logs in to the registry, pulls the image, and runs it with env vars from the Jenkinsfile and credentials.

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

