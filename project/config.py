from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import yaml

from project.exceptions import ConfigError
from project.models import InputConfig


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ConfigError(f"Missing required environment variable: {name}")
    return value.strip()


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as e:  # pragma: no cover
        raise ConfigError(f"Invalid integer for {name}: {raw}") from e
    return value


def _optional_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError as e:  # pragma: no cover
        raise ConfigError(f"Invalid float for {name}: {raw}") from e
    return value


def _require_https_url(name: str) -> str:
    url = _require_env(name)
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ConfigError(f"{name} must be https:// URL (got: {url})")
    if not parsed.netloc:
        raise ConfigError(f"{name} must include host (got: {url})")
    return url.rstrip("/")


@dataclass(frozen=True, slots=True)
class Settings:
    rancher_dev_base_url: str
    rancher_dev_token: str
    rancher_prod_base_url: str
    rancher_prod_token: str
    vault_base_url: str
    vault_token: str
    request_timeout_s: float
    retry_count: int
    log_level: str
    global_timeout_s: float


def _any_set(*names: str) -> bool:
    return any(os.getenv(n) not in (None, "") for n in names)


def _load_rancher_pair_from_env() -> tuple[str, str, str, str]:
    """
    Load Rancher endpoints/tokens for dev and prod.

    Preferred:
      - RANCHER_DEV_BASE_URL / RANCHER_DEV_TOKEN
      - RANCHER_PROD_BASE_URL / RANCHER_PROD_TOKEN

    Legacy fallback (applies to both dev and prod):
      - RANCHER_BASE_URL / RANCHER_TOKEN
    """

    dev_mode = _any_set("RANCHER_DEV_BASE_URL", "RANCHER_DEV_TOKEN", "RANCHER_PROD_BASE_URL", "RANCHER_PROD_TOKEN")
    if dev_mode:
        dev_url = _require_https_url("RANCHER_DEV_BASE_URL")
        dev_token = _require_env("RANCHER_DEV_TOKEN")
        prod_url = _require_https_url("RANCHER_PROD_BASE_URL")
        prod_token = _require_env("RANCHER_PROD_TOKEN")
        return dev_url, dev_token, prod_url, prod_token

    # Legacy: single Rancher host/token for both environments.
    url = _require_https_url("RANCHER_BASE_URL")
    token = _require_env("RANCHER_TOKEN")
    return url, token, url, token


def load_settings_from_env() -> Settings:
    dev_url, dev_token, prod_url, prod_token = _load_rancher_pair_from_env()
    return Settings(
        rancher_dev_base_url=dev_url,
        rancher_dev_token=dev_token,
        rancher_prod_base_url=prod_url,
        rancher_prod_token=prod_token,
        vault_base_url=_require_https_url("VAULT_BASE_URL"),
        vault_token=_require_env("VAULT_TOKEN"),
        request_timeout_s=_optional_float("REQUEST_TIMEOUT", 10.0),
        retry_count=_optional_int("RETRY_COUNT", 3),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        global_timeout_s=_optional_float("GLOBAL_TIMEOUT", 600.0),
    )


def load_input_config(*, path: str) -> InputConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigError(f"Config file not found: {path}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file: {path}") from e

    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("Config YAML must be a mapping (object) at top level")

    def _list_of_strings(value: Any, key: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ConfigError(f"{key} must be a list of strings")
        out: list[str] = []
        for item in value:
            if not isinstance(item, str) or item.strip() == "":
                raise ConfigError(f"{key} must contain only non-empty strings")
            out.append(item.strip())
        return out

    parsed = InputConfig(
        dev_clusters=_list_of_strings(raw.get("dev_clusters"), "dev_clusters"),
        prod_clusters=_list_of_strings(raw.get("prod_clusters"), "prod_clusters"),
    )
    return parsed

