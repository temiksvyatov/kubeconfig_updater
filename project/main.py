from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from project.clients.rancher_client import RancherClient
from project.clients.vault_client import VaultClient
from project.config import load_input_config, load_settings_from_env
from project.exceptions import ConfigError, ExitCode, VaultForbiddenError, exit_code_for_errors
from project.services.cluster_updater import ClusterUpdater
from project.utils.logging import Timer, configure_logging, log_event


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kubeconfig-updater", add_help=True)
    p.add_argument("--config", required=True, help="Path to YAML config with cluster lists")
    p.add_argument("--dry-run", action="store_true", help="Do not write to Vault")
    p.add_argument(
        "--parallelism",
        type=int,
        default=20,
        help="Maximum number of clusters to process concurrently (default: 20)",
    )
    return p


async def _async_main(args: argparse.Namespace) -> int:
    timer = Timer.start_now()

    try:
        settings = load_settings_from_env()
        logger = configure_logging(level=settings.log_level)
        cfg = load_input_config(path=args.config)
    except ConfigError as e:
        logger = configure_logging(level="INFO")
        log_event(
            logger,
            cluster_name="global",
            action="config",
            result="failed",
            duration_ms=timer.elapsed_ms(),
            level=logging.ERROR,
            message=str(e),
        )
        return int(ExitCode.INVALID_YAML)

    dev_clusters = list(cfg.dev_clusters)
    prod_clusters = list(cfg.prod_clusters)
    clusters_total = len(cfg.all_clusters())
    log_event(
        logger,
        cluster_name="global",
        action="config",
        result="ok",
        duration_ms=timer.elapsed_ms(),
        extra_fields={
            "cluster_count": clusters_total,
            "dev_cluster_count": len(dev_clusters),
            "prod_cluster_count": len(prod_clusters),
            "dry_run": bool(args.dry_run),
        },
    )

    rancher_dev = RancherClient(
        base_url=settings.rancher_dev_base_url,
        token=settings.rancher_dev_token,
        timeout_s=settings.request_timeout_s,
    )
    rancher_prod = RancherClient(
        base_url=settings.rancher_prod_base_url,
        token=settings.rancher_prod_token,
        timeout_s=settings.request_timeout_s,
    )
    vault = VaultClient(
        base_url=settings.vault_base_url,
        token=settings.vault_token,
        timeout_s=settings.request_timeout_s,
    )

    updater = ClusterUpdater(
        rancher_dev=rancher_dev,
        rancher_prod=rancher_prod,
        vault=vault,
        logger=logger,
        retry_count=settings.retry_count,
        parallelism=int(args.parallelism),
        dry_run=bool(args.dry_run),
    )

    saw_rancher_4xx = False
    saw_unexpected = False

    try:
        async with asyncio.timeout(settings.global_timeout_s):
            outcomes = await updater.sync_clusters(dev_cluster_names=dev_clusters, prod_cluster_names=prod_clusters)
    except VaultForbiddenError:
        return int(ExitCode.VAULT_403)
    except Exception as e:  # pragma: no cover
        log_event(
            logger,
            cluster_name="global",
            action="run",
            result="failed",
            duration_ms=timer.elapsed_ms(),
            level=logging.ERROR,
            message=repr(e),
        )
        return int(ExitCode.UNEXPECTED)
    finally:
        await rancher_dev.aclose()
        await rancher_prod.aclose()
        await vault.aclose()

    for o in outcomes:
        saw_rancher_4xx = saw_rancher_4xx or o.saw_rancher_4xx
        saw_unexpected = saw_unexpected or o.saw_unexpected

    exit_code = exit_code_for_errors(saw_rancher_4xx=saw_rancher_4xx, saw_unexpected=saw_unexpected)
    log_event(
        logger,
        cluster_name="global",
        action="summary",
        result="ok" if exit_code == 0 else "failed",
        duration_ms=timer.elapsed_ms(),
        level=logging.INFO if exit_code == 0 else logging.ERROR,
        extra_fields={
            "total": len(outcomes),
            "success": sum(1 for o in outcomes if o.result == "success"),
            "skipped": sum(1 for o in outcomes if o.result == "skipped"),
            "dry_run": sum(1 for o in outcomes if o.result == "dry_run"),
            "warning": sum(1 for o in outcomes if o.result == "warning"),
            "failed": sum(1 for o in outcomes if o.result == "failed"),
            "exit_code": exit_code,
        },
    )
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    args.config = str(Path(args.config))
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

