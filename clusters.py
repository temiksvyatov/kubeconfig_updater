from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ClusterConfig(BaseModel):
    """In-memory representation of a single cluster entry."""

    name: str = Field(..., min_length=1)
    env: Literal["dev", "prod"]


class ClustersConfig(BaseModel):
    """Validated representation of clusters.yaml contents."""

    dev: list[str] = Field(default_factory=list)
    prod: list[str] = Field(default_factory=list)


def validate_clusters_file(path: str) -> ClustersConfig:
    """Validate clusters.yaml file and return a structured config.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the YAML is invalid or fails structural checks.
    """

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"clusters.yaml not found: {path}")

    raw = p.read_text(encoding="utf-8")

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("clusters.yaml must be a mapping")

    dev_list = data.get("dev", []) or []
    prod_list = data.get("prod", []) or []

    for env_name, clusters in (("dev", dev_list), ("prod", prod_list)):
        if not isinstance(clusters, list):
            raise ValueError(f"'{env_name}' must be a list")
        for name in clusters:
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Invalid cluster name in '{env_name}': {name!r}")

    all_clusters = list(dev_list) + list(prod_list)
    if not all_clusters:
        raise ValueError("clusters.yaml contains no clusters")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in all_clusters:
        if name in seen:
            duplicates.add(name)
        else:
            seen.add(name)

    if duplicates:
        dup_str = ", ".join(sorted(duplicates))
        raise ValueError(f"Duplicate cluster names across environments: {dup_str}")

    return ClustersConfig(dev=list(dev_list), prod=list(prod_list))

