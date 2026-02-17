from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass

from project.clients.rancher_client import RancherClient
from project.clients.vault_client import VaultClient
from project.exceptions import HttpStatusError, RetryableHttpStatusError, VaultForbiddenError
from project.utils.logging import Timer, log_event
from project.utils.retry import retry_on_5xx


@dataclass(frozen=True, slots=True)
class ClusterOutcome:
    cluster_name: str
    result: str  # success | skipped | warning | failed | dry_run
    detail: str
    saw_rancher_4xx: bool = False
    saw_unexpected: bool = False


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ClusterUpdater:
    def __init__(
        self,
        *,
        rancher_dev: RancherClient,
        rancher_prod: RancherClient,
        vault: VaultClient,
        logger: logging.Logger,
        retry_count: int,
        parallelism: int,
        dry_run: bool,
    ) -> None:
        self._rancher_dev = rancher_dev
        self._rancher_prod = rancher_prod
        self._vault = vault
        self._logger = logger
        self._retry_count = retry_count
        self._sema = asyncio.Semaphore(max(1, parallelism))
        self._dry_run = dry_run

    async def sync_clusters(
        self,
        *,
        dev_cluster_names: list[str],
        prod_cluster_names: list[str],
    ) -> list[ClusterOutcome]:
        # Build two name->id maps (dev/prod) and process each group on its Rancher host.

        async def _list(rancher: RancherClient, env: str) -> dict[str, str]:
            clusters_timer = Timer.start_now()
            clusters = await retry_on_5xx(rancher.list_clusters, retries=self._retry_count)
            log_event(
                self._logger,
                cluster_name="global",
                action="rancher_list_clusters",
                result="ok",
                duration_ms=clusters_timer.elapsed_ms(),
                extra_fields={"rancher_env": env},
            )
            return {c.name: c.id for c in clusters.data}

        dev_map, prod_map = await asyncio.gather(
            _list(self._rancher_dev, "dev"),
            _list(self._rancher_prod, "prod"),
        )

        dev_tasks = [
            asyncio.create_task(
                self._sync_one(name=name, name_to_id=dev_map, rancher=self._rancher_dev, rancher_env="dev")
            )
            for name in dev_cluster_names
        ]
        prod_tasks = [
            asyncio.create_task(
                self._sync_one(name=name, name_to_id=prod_map, rancher=self._rancher_prod, rancher_env="prod")
            )
            for name in prod_cluster_names
        ]
        tasks = [*dev_tasks, *prod_tasks]
        try:
            results = await asyncio.gather(*tasks)
        except VaultForbiddenError:
            for t in tasks:
                t.cancel()
            raise
        return results

    async def _sync_one(
        self,
        *,
        name: str,
        name_to_id: dict[str, str],
        rancher: RancherClient,
        rancher_env: str,
    ) -> ClusterOutcome:
        async with self._sema:
            if name not in name_to_id:
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="cluster_lookup",
                    result="warning",
                    duration_ms=0,
                    level=logging.WARNING,
                    message="Cluster not found in Rancher list",
                    extra_fields={"rancher_env": rancher_env},
                )
                return ClusterOutcome(cluster_name=name, result="warning", detail="cluster_not_found")

            cluster_id = name_to_id[name]

            try:
                kube_timer = Timer.start_now()

                async def _fetch() -> str:
                    return await rancher.generate_kubeconfig(cluster_id=cluster_id)

                kube_config_obj = await retry_on_5xx(_fetch, retries=self._retry_count)
                kube_config = kube_config_obj
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="rancher_generate_kubeconfig",
                    result="ok",
                    duration_ms=kube_timer.elapsed_ms(),
                    extra_fields={"rancher_env": rancher_env},
                )

                vault_timer = Timer.start_now()
                existing = await retry_on_5xx(
                    lambda: self._vault.read_kubeconfig(cluster_name=name),
                    retries=self._retry_count,
                )
                existing_str = existing
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="vault_read",
                    result="ok",
                    duration_ms=vault_timer.elapsed_ms(),
                )

                new_sum = _sha256(kube_config)
                old_sum = _sha256(existing_str) if existing_str is not None else None

                if old_sum is not None and old_sum == new_sum:
                    log_event(
                        self._logger,
                        cluster_name=name,
                        action="vault_write",
                        result="skipped",
                        duration_ms=0,
                        message="Kubeconfig unchanged; skipping upload",
                    )
                    return ClusterOutcome(cluster_name=name, result="skipped", detail="unchanged")

                if self._dry_run:
                    log_event(
                        self._logger,
                        cluster_name=name,
                        action="vault_write",
                        result="dry_run",
                        duration_ms=0,
                        message="Dry-run; would upload kubeconfig",
                        extra_fields={
                            "changed": old_sum is not None,
                            "new_sha256": new_sum,
                            "rancher_env": rancher_env,
                        },
                    )
                    return ClusterOutcome(cluster_name=name, result="dry_run", detail="would_write")

                write_timer = Timer.start_now()
                await retry_on_5xx(
                    lambda: self._vault.write_kubeconfig(cluster_name=name, kube_config=kube_config),
                    retries=self._retry_count,
                )
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="vault_write",
                    result="ok",
                    duration_ms=write_timer.elapsed_ms(),
                )
                return ClusterOutcome(cluster_name=name, result="success", detail="uploaded")

            except VaultForbiddenError:
                # Security requirement: fail fast on Vault 403.
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="vault_write",
                    result="forbidden",
                    duration_ms=0,
                    level=logging.ERROR,
                    message="Vault forbidden (403); failing fast",
                )
                raise
            except RetryableHttpStatusError as e:
                # Ran out of retries.
                log_event(
                    self._logger,
                    cluster_name=name,
                    action=f"{e.service}_http",
                    result="failed",
                    duration_ms=0,
                    level=logging.ERROR,
                    message=str(e),
                    extra_fields={"rancher_env": rancher_env} if e.service == "rancher" else None,
                )
                return ClusterOutcome(
                    cluster_name=name,
                    result="failed",
                    detail="retry_exhausted",
                    saw_unexpected=True,
                )
            except HttpStatusError as e:
                # Rancher 4xx => exit code 2; Vault 4xx (non-403) treated as unexpected.
                is_rancher_4xx = e.service == "rancher" and 400 <= e.status_code <= 499
                log_event(
                    self._logger,
                    cluster_name=name,
                    action=f"{e.service}_http",
                    result="failed",
                    duration_ms=0,
                    level=logging.ERROR,
                    message=str(e),
                    extra_fields={"rancher_env": rancher_env} if e.service == "rancher" else None,
                )
                return ClusterOutcome(
                    cluster_name=name,
                    result="failed",
                    detail="http_4xx",
                    saw_rancher_4xx=is_rancher_4xx,
                    saw_unexpected=not is_rancher_4xx,
                )
            except Exception as e:  # pragma: no cover
                log_event(
                    self._logger,
                    cluster_name=name,
                    action="unexpected",
                    result="failed",
                    duration_ms=0,
                    level=logging.ERROR,
                    message=repr(e),
                )
                return ClusterOutcome(
                    cluster_name=name,
                    result="failed",
                    detail="unexpected",
                    saw_unexpected=True,
                )

