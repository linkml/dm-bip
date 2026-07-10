"""Tests for `dm-bip seven-bridges manifest`."""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.seven_bridges.cli import app


def test_manifest_writes_consent_groups_grouped_by_cohort(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """Walks project → study-root → cohorts → consent groups and writes Filename/Schema pairs."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={
            "items": [
                {"id": "root1", "name": "PilotParentStudies_NoDRS", "type": "folder"},
                {"id": "other", "name": "OtherFolder", "type": "folder"},
            ]
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=root1",
        json={
            "items": [
                {"id": "fhs", "name": "FHS", "type": "folder"},
                {"id": "aric", "name": "ARIC", "type": "folder"},
            ]
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=fhs",
        json={
            "items": [
                {"id": "g1", "name": "phs000007-HMB-IRB-MDS", "type": "folder"},
                {"id": "g2", "name": "phs000007-HMB-IRB-NPU", "type": "folder"},
            ]
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=aric",
        json={"items": [{"id": "g3", "name": "phs000280-HMB-IRB", "type": "folder"}]},
    )

    output = tmp_path / "tasks.csv"
    result = CliRunner().invoke(app, ["manifest", "--output", str(output)])

    assert result.exit_code == 0, result.output
    with output.open() as f:
        rows = list(csv.DictReader(f))
    assert rows == [
        {"Filename": "phs000007-HMB-IRB-MDS", "Schema": "FHS"},
        {"Filename": "phs000007-HMB-IRB-NPU", "Schema": "FHS"},
        {"Filename": "phs000280-HMB-IRB", "Schema": "ARIC"},
    ]


def test_manifest_errors_when_study_root_missing(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """Missing study-root folder yields a clear error and non-zero exit."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={"items": [{"id": "x", "name": "SomethingElse", "type": "folder"}]},
    )

    result = CliRunner().invoke(app, ["manifest", "--output", str(tmp_path / "x.csv")])

    assert result.exit_code == 1
    assert "PilotParentStudies_NoDRS" in result.output
