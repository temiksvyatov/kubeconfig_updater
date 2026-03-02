# Dockerfile Requirements

## Rules
- You ALWAYS use multi-stage build: `builder` stage installs deps, `runtime` stage is minimal.
- You ALWAYS run as non-root user (`UID 1000`).
- You NEVER install `pip` packages in the runtime stage — copy virtualenv from builder.
- You ALWAYS pin the base image to a specific digest or minor version tag.
- Final image MUST be based on `python:3.11-slim` or `gcr.io/distroless/python3`.

## Template
```dockerfile
# ---- builder ----
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime ----
FROM python:3.11-slim AS runtime

# Non-root user
RUN useradd -u 1000 -m appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY --chown=appuser:appuser . .

USER appuser

ENTRYPOINT ["python", "main.py"]
```

## .dockerignore (required)
```
.env
.env.*
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
.ruff_cache/
tests/
*.md
.git/
.cursor/
```

## Build & Run
```bash
# Build
docker build -t kubeconfig-sync:latest .

# Run (inject secrets via env)
docker run --rm \
  -e RANCHER_DEV_URL="https://vlg-cicdt-rch.megafon.ru" \
  -e RANCHER_PROD_URL="https://msk-cicd-rch.megafon.ru" \
  -e RANCHER_DEV_TOKEN="$RANCHER_DEV_TOKEN" \
  -e RANCHER_PROD_TOKEN="$RANCHER_PROD_TOKEN" \
  -e VAULT_URL="http://msk-jen-mas02.megafon.ru" \
  -e VAULT_TOKEN="$VAULT_TOKEN" \
  -v "$(pwd)/clusters.yaml:/app/clusters.yaml:ro" \
  kubeconfig-sync:latest
```

## Rules
- You NEVER use `CMD` with shell form — always exec form or `ENTRYPOINT`.
- You NEVER copy `.env` files into the image.
- `COPY . .` MUST come after `COPY requirements.txt` to leverage layer cache.
- Image MUST have no setuid/setgid binaries — verify with `find / -perm /6000` in CI if required.
