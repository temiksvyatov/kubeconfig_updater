from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel

from project.exceptions import HttpStatusError, RetryableHttpStatusError
from project.models import RancherClustersResponse, RancherKubeconfigResponse

T = TypeVar("T", bound=BaseModel)


class RancherClient:
    def __init__(self, *, base_url: str, token: str, timeout_s: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s),
            headers={"Authorization": f"Bearer {token}"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def list_clusters(self) -> RancherClustersResponse:
        resp = await self._client.get("/v3/clusters")
        parsed = self._handle_json(resp, model=RancherClustersResponse, service="rancher")
        return parsed

    async def generate_kubeconfig(self, *, cluster_id: str) -> str:
        resp = await self._client.post(f"/v3/clusters/{cluster_id}", params={"action": "generateKubeconfig"})
        parsed = self._handle_json(resp, model=RancherKubeconfigResponse, service="rancher")
        return parsed.config

    @staticmethod
    def _handle_json(resp: httpx.Response, *, model: type[T], service: str) -> T:
        status = resp.status_code
        if 500 <= status <= 599:
            raise RetryableHttpStatusError(service=service, status_code=status, message=resp.text)
        if 400 <= status <= 499:
            raise HttpStatusError(service=service, status_code=status, message=resp.text)
        data = resp.json()
        return model.model_validate(data)

