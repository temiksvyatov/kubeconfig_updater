from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RancherCluster(BaseModel):
    id: str
    name: str


class RancherClustersResponse(BaseModel):
    data: list[RancherCluster] = Field(default_factory=list)


class RancherKubeconfigResponse(BaseModel):
    config: str


class VaultReadInnerData(BaseModel):
    kube_config: str | None = None


class VaultReadData(BaseModel):
    data: VaultReadInnerData
    metadata: dict[str, Any] | None = None


class VaultReadResponse(BaseModel):
    data: VaultReadData


class InputConfig(BaseModel):
    dev_clusters: list[str] = Field(default_factory=list)
    prod_clusters: list[str] = Field(default_factory=list)

    def all_clusters(self) -> list[str]:
        # Preserve order while de-duping.
        seen: set[str] = set()
        out: list[str] = []
        for name in [*self.dev_clusters, *self.prod_clusters]:
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out

