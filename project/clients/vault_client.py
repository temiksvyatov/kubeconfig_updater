from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel

from project.exceptions import HttpStatusError, RetryableHttpStatusError, VaultForbiddenError
from project.models import VaultReadResponse

T = TypeVar("T", bound=BaseModel)


class VaultClient:
    def __init__(self, *, base_url: str, token: str, timeout_s: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout_s),
            headers={"X-Vault-Token": token},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def read_kubeconfig(self, *, cluster_name: str) -> str | None:
        path = f"/v1/secret/data/jenkins/devops/k8s/kubeconfigs/{cluster_name}"
        resp = await self._client.get(path)
        if resp.status_code == 404:
            return None
        parsed = self._handle_json(resp, model=VaultReadResponse, service="vault")
        return parsed.data.data.kube_config

    async def write_kubeconfig(self, *, cluster_name: str, kube_config: str) -> None:
        path = f"/v1/secret/data/jenkins/devops/k8s/kubeconfigs/{cluster_name}"
        resp = await self._client.post(path, json={"data": {"kube_config": kube_config}})
        self._handle_no_content(resp, service="vault")

    @staticmethod
    def _handle_json(resp: httpx.Response, *, model: type[T], service: str) -> T:
        VaultClient._raise_for_status(resp, service=service)
        data = resp.json()
        return model.model_validate(data)

    @staticmethod
    def _handle_no_content(resp: httpx.Response, *, service: str) -> None:
        VaultClient._raise_for_status(resp, service=service)
        return None

    @staticmethod
    def _raise_for_status(resp: httpx.Response, *, service: str) -> None:
        status = resp.status_code
        if service == "vault" and status == 403:
            raise VaultForbiddenError()
        if 500 <= status <= 599:
            raise RetryableHttpStatusError(service=service, status_code=status, message=resp.text)
        if 400 <= status <= 499:
            raise HttpStatusError(service=service, status_code=status, message=resp.text)

