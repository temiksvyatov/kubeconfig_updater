from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import aiohttp
from pydantic import SecretStr

from utils import log, with_retry


class RancherAPIError(Exception):
    """Raised when Rancher API returns an unexpected error."""

    def __init__(self, status: int, url: str, body_snippet: str) -> None:
        super().__init__(f"Rancher API error {status} for {url}: {body_snippet}")
        self.status = status
        self.url = url
        self.body_snippet = body_snippet


@dataclass
class RancherClient:
    """Async client for interacting with Rancher cluster API."""

    base_url: str
    token: SecretStr
    session: aiohttp.ClientSession | None = field(default=None, init=False)

    async def __aenter__(self) -> "RancherClient":
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *_: object) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token.get_secret_value()}",
            "Content-Type": "application/json",
        }

    @with_retry()
    async def _get_json(self, url: str) -> Dict[str, Any]:
        if self.session is None:
            raise RuntimeError("RancherClient session is not initialized")

        async with self.session.get(url, headers=self._headers(), ssl=False) as resp:
            text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                snippet = text[:200]
                raise RancherAPIError(resp.status, url, snippet)
            return await resp.json()

    @with_retry()
    async def _post_json(self, url: str) -> Dict[str, Any]:
        if self.session is None:
            raise RuntimeError("RancherClient session is not initialized")

        async with self.session.post(url, headers=self._headers(), ssl=False) as resp:
            text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                snippet = text[:200]
                raise RancherAPIError(resp.status, url, snippet)
            return await resp.json()

    async def build_cluster_map(self) -> Dict[str, str]:
        """Return a mapping {cluster_name: cluster_id}, handling pagination."""

        if self.session is None:
            raise RuntimeError("RancherClient session is not initialized")

        clusters: list[Dict[str, Any]] = []
        url = f"{self.base_url.rstrip('/')}/v3/clusters"

        while True:
            data = await self._get_json(url)
            page_clusters = data.get("data", []) or []
            clusters.extend(page_clusters)

            pagination = data.get("pagination") or {}
            next_url = pagination.get("next")
            if not next_url:
                break
            if not next_url.startswith("http"):
                next_url = f"{self.base_url.rstrip('/')}{next_url}"
            url = next_url

        result = {c["name"]: c["id"] for c in clusters if "name" in c and "id" in c}
        log.info("rancher_cluster_map_built", base_url=self.base_url, count=len(result))
        return result

    async def get_kubeconfig(self, cluster_id: str) -> str:
        """Generate kubeconfig for a given cluster ID."""

        url = f"{self.base_url.rstrip('/')}/v3/clusters/{cluster_id}?action=generateKubeconfig"
        data = await self._post_json(url)
        config = data.get("config")
        if not isinstance(config, str):
            raise RancherAPIError(
                status=200,
                url=url,
                body_snippet="Missing 'config' field in response",
            )
        return config


__all__ = ["RancherClient", "RancherAPIError"]

