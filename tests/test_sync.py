from __future__ import annotations

import asyncio
from typing import Dict

import pytest
from aioresponses import aioresponses
from pydantic import SecretStr

from settings import Settings
from sync import SyncResult, sync_cluster
from rancher import RancherClient
from vault import VaultClient


@pytest.mark.asyncio
async def test_sync_cluster_up_to_date() -> None:
    settings = Settings(
        rancher_dev_url="https://rancher-dev",
        rancher_prod_url="https://rancher-prod",
        rancher_dev_token=SecretStr("dev"),
        rancher_prod_token=SecretStr("prod"),
        vault_url="http://vault",
        vault_token=SecretStr("vault"),
    )

    async with RancherClient(settings.rancher_dev_url, settings.rancher_dev_token) as rancher_dev, RancherClient(
        settings.rancher_prod_url, settings.rancher_prod_token
    ) as rancher_prod, VaultClient(
        settings.vault_url,
        settings.vault_token,
        "secret/data/rancher/kubeconfig",
    ) as vault_client:
        dev_map: Dict[str, str] = {"dev-1": "c-abc"}
        prod_map: Dict[str, str] = {}

        rancher_cfg = "apiVersion: v1\nkind: Config\nclusters: []\n"

        sem = asyncio.Semaphore(5)

        with aioresponses() as mocked:
            mocked.post(
                "https://rancher-dev/v3/clusters/c-abc?action=generateKubeconfig",
                status=200,
                payload={"config": rancher_cfg},
            )
            mocked.get(
                "http://vault/v1/secret/data/rancher/kubeconfig/dev-1",
                status=200,
                payload={"data": {"data": {"kubeconfig": rancher_cfg}}},
            )

            result = await sync_cluster(
                env="dev",
                name="dev-1",
                dev_map=dev_map,
                prod_map=prod_map,
                rancher_dev=rancher_dev,
                rancher_prod=rancher_prod,
                vault_client=vault_client,
                semaphore=sem,
            )

    assert isinstance(result, SyncResult)
    assert result.skipped is True
    assert result.updated is False
    assert result.error is None


@pytest.mark.asyncio
async def test_sync_cluster_triggers_update_when_different() -> None:
    settings = Settings(
        rancher_dev_url="https://rancher-dev",
        rancher_prod_url="https://rancher-prod",
        rancher_dev_token=SecretStr("dev"),
        rancher_prod_token=SecretStr("prod"),
        vault_url="http://vault",
        vault_token=SecretStr("vault"),
    )

    async with RancherClient(settings.rancher_dev_url, settings.rancher_dev_token) as rancher_dev, RancherClient(
        settings.rancher_prod_url, settings.rancher_prod_token
    ) as rancher_prod, VaultClient(
        settings.vault_url,
        settings.vault_token,
        "secret/data/rancher/kubeconfig",
    ) as vault_client:
        dev_map: Dict[str, str] = {"dev-1": "c-abc"}
        prod_map: Dict[str, str] = {}

        rancher_cfg = "apiVersion: v1\nkind: Config\nclusters: []\n"
        vault_cfg = "apiVersion: v1\nkind: Config\nclusters: [{name: other}]\n"

        sem = asyncio.Semaphore(5)

        with aioresponses() as mocked:
            mocked.post(
                "https://rancher-dev/v3/clusters/c-abc?action=generateKubeconfig",
                status=200,
                payload={"config": rancher_cfg},
            )
            mocked.get(
                "http://vault/v1/secret/data/rancher/kubeconfig/dev-1",
                status=200,
                payload={"data": {"data": {"kubeconfig": vault_cfg}}},
            )
            mocked.post(
                "http://vault/v1/secret/data/rancher/kubeconfig/dev-1",
                status=200,
                payload={},
            )

            result = await sync_cluster(
                env="dev",
                name="dev-1",
                dev_map=dev_map,
                prod_map=prod_map,
                rancher_dev=rancher_dev,
                rancher_prod=rancher_prod,
                vault_client=vault_client,
                semaphore=sem,
            )

    assert result.updated is True
    assert result.skipped is False
    assert result.error is None


@pytest.mark.asyncio
async def test_sync_cluster_handles_rancher_error() -> None:
    settings = Settings(
        rancher_dev_url="https://rancher-dev",
        rancher_prod_url="https://rancher-prod",
        rancher_dev_token=SecretStr("dev"),
        rancher_prod_token=SecretStr("prod"),
        vault_url="http://vault",
        vault_token=SecretStr("vault"),
    )

    async with RancherClient(settings.rancher_dev_url, settings.rancher_dev_token) as rancher_dev, RancherClient(
        settings.rancher_prod_url, settings.rancher_prod_token
    ) as rancher_prod, VaultClient(
        settings.vault_url,
        settings.vault_token,
        "secret/data/rancher/kubeconfig",
    ) as vault_client:
        dev_map: Dict[str, str] = {"dev-1": "c-abc"}
        prod_map: Dict[str, str] = {}

        sem = asyncio.Semaphore(5)

        with aioresponses() as mocked:
            mocked.post(
                "https://rancher-dev/v3/clusters/c-abc?action=generateKubeconfig",
                status=500,
                payload={"message": "server error"},
            )

            result = await sync_cluster(
                env="dev",
                name="dev-1",
                dev_map=dev_map,
                prod_map=prod_map,
                rancher_dev=rancher_dev,
                rancher_prod=rancher_prod,
                vault_client=vault_client,
                semaphore=sem,
            )

    assert result.error is not None
    assert result.updated is False
    assert result.skipped is False

