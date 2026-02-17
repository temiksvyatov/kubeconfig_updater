from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import cast

from project.clients.rancher_client import RancherClient
from project.clients.vault_client import VaultClient
from project.models import RancherCluster, RancherClustersResponse
from project.services.cluster_updater import ClusterUpdater
from project.utils.logging import configure_logging


@dataclass
class FakeRancher:
    clusters: dict[str, str]
    kubeconfigs: dict[str, str]

    async def list_clusters(self) -> RancherClustersResponse:
        return RancherClustersResponse(
            data=[RancherCluster(id=cid, name=name) for name, cid in self.clusters.items()]
        )

    async def generate_kubeconfig(self, *, cluster_id: str) -> str:
        return self.kubeconfigs[cluster_id]

    async def aclose(self) -> None:
        return None


@dataclass
class FakeVault:
    existing: dict[str, str]
    writes: dict[str, str]

    async def read_kubeconfig(self, *, cluster_name: str) -> str | None:
        return self.existing.get(cluster_name)

    async def write_kubeconfig(self, *, cluster_name: str, kube_config: str) -> None:
        self.writes[cluster_name] = kube_config

    async def aclose(self) -> None:
        return None


def _logger() -> logging.Logger:
    return configure_logging(level="INFO")


def test_skips_write_when_checksum_matches() -> None:
    rancher_dev = FakeRancher(
        clusters={"cluster-1": "c-1"},
        kubeconfigs={"c-1": "kubeconfig: same"},
    )
    rancher_prod = FakeRancher(clusters={}, kubeconfigs={})
    vault = FakeVault(existing={"cluster-1": "kubeconfig: same"}, writes={})

    updater = ClusterUpdater(
        rancher_dev=cast(RancherClient, rancher_dev),
        rancher_prod=cast(RancherClient, rancher_prod),
        vault=cast(VaultClient, vault),
        logger=_logger(),
        retry_count=0,
        parallelism=5,
        dry_run=False,
    )

    outcomes = asyncio.run(updater.sync_clusters(dev_cluster_names=["cluster-1"], prod_cluster_names=[]))
    assert outcomes[0].result == "skipped"
    assert vault.writes == {}


def test_writes_when_secret_missing() -> None:
    rancher_dev = FakeRancher(
        clusters={"cluster-1": "c-1"},
        kubeconfigs={"c-1": "kubeconfig: new"},
    )
    rancher_prod = FakeRancher(clusters={}, kubeconfigs={})
    vault = FakeVault(existing={}, writes={})

    updater = ClusterUpdater(
        rancher_dev=cast(RancherClient, rancher_dev),
        rancher_prod=cast(RancherClient, rancher_prod),
        vault=cast(VaultClient, vault),
        logger=_logger(),
        retry_count=0,
        parallelism=5,
        dry_run=False,
    )

    outcomes = asyncio.run(updater.sync_clusters(dev_cluster_names=["cluster-1"], prod_cluster_names=[]))
    assert outcomes[0].result == "success"
    assert vault.writes["cluster-1"] == "kubeconfig: new"


def test_dry_run_does_not_write() -> None:
    rancher_dev = FakeRancher(
        clusters={"cluster-1": "c-1"},
        kubeconfigs={"c-1": "kubeconfig: new"},
    )
    rancher_prod = FakeRancher(clusters={}, kubeconfigs={})
    vault = FakeVault(existing={}, writes={})

    updater = ClusterUpdater(
        rancher_dev=cast(RancherClient, rancher_dev),
        rancher_prod=cast(RancherClient, rancher_prod),
        vault=cast(VaultClient, vault),
        logger=_logger(),
        retry_count=0,
        parallelism=5,
        dry_run=True,
    )

    outcomes = asyncio.run(updater.sync_clusters(dev_cluster_names=["cluster-1"], prod_cluster_names=[]))
    assert outcomes[0].result == "dry_run"
    assert vault.writes == {}

