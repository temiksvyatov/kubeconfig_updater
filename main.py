from __future__ import annotations

import asyncio
import os
import sys

import structlog

from settings import get_settings
from sync import sync_all
from utils import configure_logging


def main() -> None:
    """CLI entrypoint for kubeconfig synchronization."""

    configure_logging()
    log = structlog.get_logger()

    settings = get_settings()
    log.info(
        "config_loaded",
        rancher_dev_url=settings.rancher_dev_url,
        rancher_prod_url=settings.rancher_prod_url,
        vault_url=settings.vault_url,
        vault_kubeconfig_path=settings.vault_kubeconfig_path,
        clusters_file=settings.clusters_file,
        rancher_dev_token="***",
        rancher_prod_token="***",
        vault_token="***",
        ci=os.getenv("CI"),
        jenkins_url=os.getenv("JENKINS_URL"),
    )

    exit_code = asyncio.run(sync_all(settings))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

