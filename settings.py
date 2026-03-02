from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All secrets are represented as `SecretStr` and must only be unwrapped
    at the HTTP boundary (e.g. when constructing authorization headers).
    """

    rancher_dev_url: str
    rancher_prod_url: str

    rancher_dev_token: SecretStr
    rancher_prod_token: SecretStr

    vault_url: str
    vault_token: SecretStr

    vault_kubeconfig_path: str = "secret/data/rancher/kubeconfig"
    clusters_file: str = "clusters.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings instance."""

    return Settings()

