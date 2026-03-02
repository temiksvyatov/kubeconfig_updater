from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import aiohttp
from pydantic import SecretStr

from utils import log, with_retry


class VaultAPIError(Exception):
    """Raised when Vault API returns an unexpected error."""

    def __init__(self, status: int, url: str, body_snippet: str) -> None:
        super().__init__(f"Vault API error {status} for {url}: {body_snippet}")
        self.status = status
        self.url = url
        self.body_snippet = body_snippet


@dataclass
class VaultClient:
    """Async client for interacting with Vault KV v2 for kubeconfigs."""

    base_url: str
    token: SecretStr
    kubeconfig_path: str
    session: aiohttp.ClientSession | None = field(default=None, init=False)

    async def __aenter__(self) -> "VaultClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Vault-Token": self.token.get_secret_value(),
            "Content-Type": "application/json",
        }

    @with_retry()
    async def _get(self, url: str) -> aiohttp.ClientResponse:
        if self.session is None:
            raise RuntimeError("VaultClient session is not initialized")

        resp = await self.session.get(url, headers=self._headers())
        return resp

    @with_retry()
    async def _post(self, url: str, json: Dict[str, Any]) -> aiohttp.ClientResponse:
        if self.session is None:
            raise RuntimeError("VaultClient session is not initialized")

        resp = await self.session.post(url, headers=self._headers(), json=json)
        return resp

    async def read_kubeconfig(self, cluster_name: str) -> str | None:
        """Read kubeconfig for a cluster from Vault KV v2, returning None on 404."""

        if self.session is None:
            raise RuntimeError("VaultClient session is not initialized")

        url = f"{self.base_url.rstrip('/')}/v1/{self.kubeconfig_path.rstrip('/')}/{cluster_name}"
        async with await self._get(url) as resp:
            text = await resp.text()
            if resp.status == 404:
                log.info("vault_kubeconfig_missing", path=self.kubeconfig_path, cluster=cluster_name)
                return None
            if resp.status < 200 or resp.status >= 300:
                snippet = text[:200]
                raise VaultAPIError(resp.status, url, snippet)
            data = await resp.json()
        return data.get("data", {}).get("data", {}).get("kubeconfig")

    async def write_kubeconfig(self, cluster_name: str, kubeconfig: str) -> None:
        """Write kubeconfig for a cluster to Vault KV v2."""

        if self.session is None:
            raise RuntimeError("VaultClient session is not initialized")

        url = f"{self.base_url.rstrip('/')}/v1/{self.kubeconfig_path.rstrip('/')}/{cluster_name}"
        payload = {"data": {"kubeconfig": kubeconfig}}
        async with await self._post(url, json=payload) as resp:
            text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                snippet = text[:200]
                raise VaultAPIError(resp.status, url, snippet)
        log.info("vault_kubeconfig_written", path=self.kubeconfig_path, cluster=cluster_name)


__all__ = ["VaultClient", "VaultAPIError"]

