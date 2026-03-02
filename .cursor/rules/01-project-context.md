# Project Context

## Overview
This project automates synchronization of Kubernetes cluster kubeconfigs from Rancher into Jenkins Vault.

## Infrastructure
- **Rancher DEV**: `https://vlg-cicdt-rch.megafon.ru`
- **Rancher PROD**: `https://msk-cicd-rch.megafon.ru`
- **Jenkins Vault**: `http://msk-jen-mas02.megafon.ru`
- **Cluster list**: `clusters.yaml` (split into `dev` and `prod` sections)

## Architecture
```
clusters.yaml
    ↓ validate
Rancher API (dev/prod) → clusterId mapping
    ↓ per cluster
  GET /v3/clusters/{id}?action=generateKubeConfig
    ↓ compare
  GET secret/data/rancher/kubeconfig/{name} from Vault
    ↓ if diff
  PUT/POST secret/data/rancher/kubeconfig/{name} to Vault
```

## Entry Points
- `main.py` — CLI entrypoint, reads env/config, runs sync loop
- `Jenkinsfile` — CI pipeline, injects credentials via `withCredentials`
- `Dockerfile` — multi-stage, non-root container image

## Runtime Modes
- **CI (Jenkins)**: credentials injected as env vars via `withCredentials`
- **Local dev**: `.env` file or exported env vars (never committed)

## Rules
- You ALWAYS treat `clusters.yaml` as the source of truth for which clusters to process.
- You NEVER hardcode URLs, tokens, or paths — all from environment or config.
- You ALWAYS distinguish dev clusters (processed via DEV Rancher) from prod clusters (via PROD Rancher) based on `clusters.yaml` structure.
- The script MUST be idempotent — running it twice produces no side effects if nothing changed.
