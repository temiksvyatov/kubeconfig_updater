from __future__ import annotations

import asyncio
from typing import Any

import pytest

from utils import kubeconfigs_are_equal, normalize_kubeconfig, with_retry


@pytest.mark.asyncio
async def test_with_retry_eventual_success() -> None:
    calls: list[int] = []

    class CustomError(Exception):
        pass

    @with_retry(attempts=3, backoff=0.01, exceptions=(CustomError,))
    async def flaky() -> str:
        calls.append(1)
        if len(calls) == 1:
            raise CustomError("first failure")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_with_retry_exhausts_attempts() -> None:
    class CustomError(Exception):
        pass

    @with_retry(attempts=2, backoff=0.01, exceptions=(CustomError,))
    async def always_fail() -> None:
        raise CustomError("fail")

    with pytest.raises(CustomError):
        await always_fail()


def test_normalize_kubeconfig_parses_yaml() -> None:
    raw = "apiVersion: v1\nkind: Config\n"
    data = normalize_kubeconfig(raw)
    assert isinstance(data, dict)
    assert data["kind"] == "Config"


def test_kubeconfigs_are_equal_structurally() -> None:
    a = """
apiVersion: v1
kind: Config
clusters:
  - name: c1
    cluster:
      server: https://example
"""
    b = """
# comment
apiVersion: v1
kind: Config
clusters:
  - cluster:
      server: https://example
    name: c1
"""
    assert kubeconfigs_are_equal(a, b) is True


def test_kubeconfigs_are_equal_none_b() -> None:
    a = "apiVersion: v1\nkind: Config\n"
    assert kubeconfigs_are_equal(a, None) is False


def test_kubeconfigs_are_equal_invalid_yaml() -> None:
    a = "apiVersion: v1\nkind: Config\n"
    b = ":\nnot-yaml"
    assert kubeconfigs_are_equal(a, b) is False

