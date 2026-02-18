# kubeconfig-updater: sync Rancher kubeconfigs to Vault (KV v2)
# Build: docker build -t kubeconfig-updater .
# Run: docker run --rm -e RANCHER_DEV_BASE_URL=... -e RANCHER_DEV_TOKEN=... \
#        -e RANCHER_PROD_BASE_URL=... -e RANCHER_PROD_TOKEN=... \
#        -e VAULT_BASE_URL=... -e VAULT_TOKEN=... \
#        -v /path/to/clusters.yaml:/app/clusters.yaml \
#        kubeconfig-updater

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies from pyproject.toml (no dev extras)
COPY pyproject.toml ./
COPY project ./project
RUN pip install --no-cache-dir .

# Default config (mount your own at run time if needed)
COPY clusters.yaml ./clusters.yaml

# Optional env defaults (required RANCHER_* / VAULT_* must be set at run time)
ENV REQUEST_TIMEOUT=10 \
    RETRY_COUNT=3 \
    LOG_LEVEL=INFO \
    GLOBAL_TIMEOUT=600

# Run as non-root
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["python", "-m", "project.main"]
CMD ["--config", "/app/clusters.yaml"]
