from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, Literal, Tuple

from pydantic import BaseModel

from clusters import ClustersConfig, validate_clusters_file
from rancher import RancherClient, RancherAPIError
from settings import Settings
from utils import kubeconfigs_are_equal, log
from vault import VaultClient, VaultAPIError


class ClusterNotFoundError(Exception):
    """Raised when a cluster name from config is missing in Rancher mapping."""

    def __init__(self, name: str, env: str) -> None:
        super().__init__(f"Cluster {name!r} not found in Rancher for env {env!r}")
        self.name = name
        self.env = env


class SyncResult(BaseModel):
    """Result of syncing a single cluster."""

    cluster: str
    env: Literal["dev", "prod"]
    updated: bool = False
    skipped: bool = False
    error: str | None = None


def _iter_clusters(config: ClustersConfig) -> Iterable[Tuple[str, Literal["dev", "prod"]]]:
    for name in config.dev:
        yield name, "dev"
    for name in config.prod:
        yield name, "prod"


async def build_cluster_maps(settings: Settings) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build Rancher cluster name→id maps for dev and prod concurrently."""

    async with RancherClient(settings.rancher_dev_url, settings.rancher_dev_token) as dev_client, RancherClient(
        settings.rancher_prod_url, settings.rancher_prod_token
    ) as prod_client:
        dev_map, prod_map = await asyncio.gather(
            dev_client.build_cluster_map(),
            prod_client.build_cluster_map(),
        )
    return dev_map, prod_map


async def sync_cluster(
    env: Literal["dev", "prod"],
    name: str,
    dev_map: Dict[str, str],
    prod_map: Dict[str, str],
    rancher_dev: RancherClient,
    rancher_prod: RancherClient,
    vault_client: VaultClient,
    semaphore: asyncio.Semaphore,
) -> SyncResult:
    """Synchronize kubeconfig for a single cluster between Rancher and Vault."""

    bound_log = log.bind(cluster=name, env=env)
    try:
        if env == "dev":
            cluster_id = dev_map.get(name)
        else:
            cluster_id = prod_map.get(name)
        if cluster_id is None:
            raise ClusterNotFoundError(name=name, env=env)

        async with semaphore:
            if env == "dev":
                rancher_client = rancher_dev
            else:
                rancher_client = rancher_prod

            rancher_cfg = await rancher_client.get_kubeconfig(cluster_id)
            vault_cfg = await vault_client.read_kubeconfig(name)

            if kubeconfigs_are_equal(rancher_cfg, vault_cfg):
                bound_log.info("kubeconfig_up_to_date")
                return SyncResult(cluster=name, env=env, skipped=True)

            await vault_client.write_kubeconfig(name, rancher_cfg)
            bound_log.info("kubeconfig_updated")
            return SyncResult(cluster=name, env=env, updated=True)
    except ClusterNotFoundError as exc:
        bound_log.error("cluster_not_found", error=str(exc))
        return SyncResult(cluster=name, env=env, error=str(exc))
    except (RancherAPIError, VaultAPIError) as exc:
        bound_log.error("sync_failed", error=str(exc))
        return SyncResult(cluster=name, env=env, error=str(exc))


async def sync_all(settings: Settings) -> int:
    """Run full synchronization flow for all clusters."""

    cfg = validate_clusters_file(settings.clusters_file)

    dev_map, prod_map = await build_cluster_maps(settings)

    semaphore = asyncio.Semaphore(5)

    results: list[SyncResult] = []
    async with RancherClient(settings.rancher_dev_url, settings.rancher_dev_token) as rancher_dev, RancherClient(
        settings.rancher_prod_url, settings.rancher_prod_token
    ) as rancher_prod, VaultClient(
        settings.vault_url,
        settings.vault_token,
        settings.vault_kubeconfig_path,
    ) as vault_client:
        tasks = [
            sync_cluster(
                env=env,
                name=name,
                dev_map=dev_map,
                prod_map=prod_map,
                rancher_dev=rancher_dev,
                rancher_prod=rancher_prod,
                vault_client=vault_client,
                semaphore=semaphore,
            )
            for name, env in _iter_clusters(cfg)
        ]

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for item in gathered:
            if isinstance(item, SyncResult):
                results.append(item)
            elif isinstance(item, Exception):
                log.error("unhandled_sync_exception", error=str(item))
            else:
                log.error("unexpected_sync_result_type", result_type=type(item).__name__)

    processed = len(results)
    updated = sum(1 for r in results if r.updated)
    skipped = sum(1 for r in results if r.skipped)
    failed = sum(1 for r in results if r.error is not None)

    log.info(
        "sync_summary",
        processed=processed,
        updated=updated,
        skipped=skipped,
        failed=failed,
    )

    return 0 if failed == 0 else 1


__all__ = ["sync_cluster", "sync_all", "SyncResult", "ClusterNotFoundError", "build_cluster_maps"]

