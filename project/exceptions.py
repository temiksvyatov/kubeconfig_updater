from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ExitCode(IntEnum):
    INVALID_YAML = 1
    RANCHER_4XX = 2
    VAULT_403 = 3
    UNEXPECTED = 4


class KubeconfigUpdaterError(Exception):
    """Base exception for controlled failures."""


class ConfigError(KubeconfigUpdaterError):
    """Configuration file or environment is invalid."""


@dataclass(frozen=True, slots=True)
class HttpStatusError(KubeconfigUpdaterError):
    service: str
    status_code: int
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.service} HTTP {self.status_code}: {self.message}"


@dataclass(frozen=True, slots=True)
class RetryableHttpStatusError(KubeconfigUpdaterError):
    service: str
    status_code: int
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.service} retryable HTTP {self.status_code}: {self.message}"


@dataclass(frozen=True, slots=True)
class VaultForbiddenError(KubeconfigUpdaterError):
    message: str = "Vault returned 403 (forbidden)"

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def exit_code_for_errors(*, saw_rancher_4xx: bool, saw_unexpected: bool) -> int:
    """
    Decide final exit code for per-cluster errors.

    Note: Vault 403 is handled as fail-fast elsewhere and should not reach here.
    """

    if saw_rancher_4xx:
        return int(ExitCode.RANCHER_4XX)
    if saw_unexpected:
        return int(ExitCode.UNEXPECTED)
    return 0

