# Security and Secrets

## Absolute Rules
- You NEVER hardcode tokens, passwords, URLs, or cluster names in source code.
- You NEVER log token values — mask them as `***` in all output.
- You NEVER store secrets in files that could be committed (`.env` is `.gitignore`d).
- You ALWAYS read secrets from environment variables only.

## Required Environment Variables
```
RANCHER_DEV_URL         # https://vlg-cicdt-rch.megafon.ru
RANCHER_PROD_URL        # https://msk-cicd-rch.megafon.ru
RANCHER_DEV_TOKEN       # Bearer token for DEV Rancher API
RANCHER_PROD_TOKEN      # Bearer token for PROD Rancher API
VAULT_URL               # http://msk-jen-mas02.megafon.ru
VAULT_TOKEN             # Vault access token
VAULT_KUBECONFIG_PATH   # e.g. secret/data/rancher/kubeconfig
CLUSTERS_FILE           # path to clusters.yaml, default: clusters.yaml
```

## Jenkins Credentials Mapping
In `Jenkinsfile`, always use `withCredentials`:
```groovy
withCredentials([
    string(credentialsId: 'rancher-dev-token',  variable: 'RANCHER_DEV_TOKEN'),
    string(credentialsId: 'rancher-prod-token', variable: 'RANCHER_PROD_TOKEN'),
    string(credentialsId: 'vault-token',        variable: 'VAULT_TOKEN'),
]) {
    sh 'python main.py'
}
```

## Python Secret Loading Pattern
```python
import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    rancher_dev_url: str
    rancher_prod_url: str
    rancher_dev_token: SecretStr
    rancher_prod_token: SecretStr
    vault_url: str
    vault_token: SecretStr
    vault_kubeconfig_path: str = "secret/data/rancher/kubeconfig"
    clusters_file: str = "clusters.yaml"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

## Rules
- You ALWAYS use `pydantic.SecretStr` for all token/password fields.
- You ALWAYS call `.get_secret_value()` only at the point of use in HTTP headers.
- You NEVER pass `SecretStr` objects directly to f-strings or loggers.
- When logging config at startup, you ALWAYS redact secret fields:
  ```python
  log.info("config loaded", vault_url=settings.vault_url, vault_token="***")
  ```
