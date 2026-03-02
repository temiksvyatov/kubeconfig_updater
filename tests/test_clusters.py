from __future__ import annotations

from pathlib import Path

import pytest

from clusters import ClustersConfig, validate_clusters_file


def write_tmp_file(tmp_path: Path, content: str) -> str:
    path = tmp_path / "clusters.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_validate_clusters_file_valid(tmp_path: Path) -> None:
    path = write_tmp_file(
        tmp_path,
        "dev:\n  - dev-1\nprod:\n  - prod-1\n",
    )

    cfg = validate_clusters_file(path)
    assert isinstance(cfg, ClustersConfig)
    assert cfg.dev == ["dev-1"]
    assert cfg.prod == ["prod-1"]


def test_validate_clusters_file_missing(tmp_path: Path) -> None:
    path = str(tmp_path / "missing.yaml")
    with pytest.raises(FileNotFoundError):
        validate_clusters_file(path)


def test_validate_clusters_file_invalid_yaml(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "dev: [unclosed\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "Invalid YAML" in str(exc.value)


def test_validate_clusters_file_non_mapping_root(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "- dev-1\n- prod-1\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "must be a mapping" in str(exc.value)


def test_validate_clusters_file_env_not_list(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "dev: dev-1\nprod:\n  - prod-1\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "'dev' must be a list" in str(exc.value)


def test_validate_clusters_file_invalid_cluster_name(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "dev:\n  - ''\nprod: []\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "Invalid cluster name in 'dev'" in str(exc.value)


def test_validate_clusters_file_no_clusters(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "dev: []\nprod: []\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "contains no clusters" in str(exc.value)


def test_validate_clusters_file_duplicate_names(tmp_path: Path) -> None:
    path = write_tmp_file(tmp_path, "dev:\n  - shared\nprod:\n  - shared\n")
    with pytest.raises(ValueError) as exc:
        validate_clusters_file(path)
    assert "Duplicate cluster names" in str(exc.value)

