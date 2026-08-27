"""Tests for `dm-bip seven-bridges submit`."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.seven_bridges.cli import app
from dm_bip.seven_bridges.client import DEFAULT_COHORT_APP, load_config


def _write_manifest(path: Path, rows: list[tuple[str, str]]) -> None:
    lines = ["Filename,Schema", *[f"{name},{schema}" for name, schema in rows]]
    path.write_text("\n".join(lines) + "\n")


def test_submit_creates_and_runs_one_task_per_row(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """For each manifest row: resolve folder, POST /tasks, POST /tasks/{id}/actions/run."""
    seed_token()
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("phs000007-HMB-IRB-MDS", "FHS")])

    # Project root listing
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={"items": [{"id": "root1", "name": "PilotParentStudies_NoDRS", "type": "folder"}]},
    )
    # Cohort lookup
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=root1",
        json={"items": [{"id": "fhs-id", "name": "FHS", "type": "folder"}]},
    )
    # Consent-group resolution
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=fhs-id&name=phs000007-HMB-IRB-MDS",
        json={"items": [{"id": "group-id", "name": "phs000007-HMB-IRB-MDS", "type": "folder"}]},
    )
    # Task creation
    httpx_mock.add_response(
        method="POST",
        url="https://api.sbg.test/v2/tasks",
        json={"id": "task-1"},
    )
    # Task run
    httpx_mock.add_response(
        method="POST",
        url="https://api.sbg.test/v2/tasks/task-1/actions/run",
        json={"id": "task-1", "status": "RUNNING"},
    )

    result = CliRunner().invoke(app, ["submit", "--manifest", str(manifest), "--throttle", "0"])

    assert result.exit_code == 0, result.output
    assert "RUNNING: task-1" in result.output

    create_req = next(r for r in httpx_mock.get_requests() if r.method == "POST" and r.url.path == "/v2/tasks")
    body = json.loads(create_req.content)
    assert body["app"] == "test/project/test-app/1"
    assert body["name"] == "Harmonization_FHS_MDS"
    assert body["inputs"]["Schema"] == "FHS"
    assert body["inputs"]["RawSource"] == {"class": "Directory", "path": "group-id"}
    assert "TransSpec" not in body["inputs"]
    assert "Profile" not in body["inputs"]


def test_submit_passes_trans_spec_when_provided(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """--trans-spec adds the TransSpec input to the task body."""
    seed_token()
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("phs000280-HMB-IRB", "ARIC")])

    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={"items": [{"id": "root1", "name": "PilotParentStudies_NoDRS", "type": "folder"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=root1",
        json={"items": [{"id": "aric-id", "name": "ARIC", "type": "folder"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=aric-id&name=phs000280-HMB-IRB",
        json={"items": [{"id": "g-id", "name": "phs000280-HMB-IRB", "type": "folder"}]},
    )
    httpx_mock.add_response(method="POST", url="https://api.sbg.test/v2/tasks", json={"id": "t2"})
    httpx_mock.add_response(method="POST", url="https://api.sbg.test/v2/tasks/t2/actions/run", json={"id": "t2"})

    result = CliRunner().invoke(
        app,
        ["submit", "--manifest", str(manifest), "--throttle", "0", "--trans-spec", "OWNER/REPO@main:specs/foo"],
    )

    assert result.exit_code == 0
    create_req = next(r for r in httpx_mock.get_requests() if r.method == "POST" and r.url.path == "/v2/tasks")
    assert json.loads(create_req.content)["inputs"]["TransSpec"] == "OWNER/REPO@main:specs/foo"


def test_submit_passes_profile_when_provided(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """--profile adds the Profile input to the task body."""
    seed_token()
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("phs000280-HMB-IRB", "ARIC")])

    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={"items": [{"id": "root1", "name": "PilotParentStudies_NoDRS", "type": "folder"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=root1",
        json={"items": [{"id": "aric-id", "name": "ARIC", "type": "folder"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=aric-id&name=phs000280-HMB-IRB",
        json={"items": [{"id": "g-id", "name": "phs000280-HMB-IRB", "type": "folder"}]},
    )
    httpx_mock.add_response(method="POST", url="https://api.sbg.test/v2/tasks", json={"id": "t3"})
    httpx_mock.add_response(method="POST", url="https://api.sbg.test/v2/tasks/t3/actions/run", json={"id": "t3"})

    result = CliRunner().invoke(app, ["submit", "--manifest", str(manifest), "--throttle", "0", "--profile"])

    assert result.exit_code == 0, result.output
    create_req = next(r for r in httpx_mock.get_requests() if r.method == "POST" and r.url.path == "/v2/tasks")
    assert json.loads(create_req.content)["inputs"]["Profile"] is True


def test_submit_errors_when_manifest_missing(sbg_env: Path, tmp_path: Path) -> None:  # noqa: ARG001
    """Missing manifest file yields a clear error and exit code 2."""
    result = CliRunner().invoke(app, ["submit", "--manifest", str(tmp_path / "nope.csv"), "--throttle", "0"])

    assert result.exit_code == 2
    assert "Manifest not found" in result.output


def test_submit_skips_row_when_schema_unknown(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """An unknown schema is logged and skipped; doesn't fail the whole batch."""
    seed_token()
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("group-x", "UNKNOWN")])

    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?project=test/project",
        json={"items": [{"id": "root1", "name": "PilotParentStudies_NoDRS", "type": "folder"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/files?parent=root1",
        json={"items": [{"id": "fhs", "name": "FHS", "type": "folder"}]},
    )

    result = CliRunner().invoke(app, ["submit", "--manifest", str(manifest), "--throttle", "0"])

    assert result.exit_code == 0
    assert "schema 'UNKNOWN' not found" in result.output


def test_cohort_mode_requires_an_app_id(
    sbg_env: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Cohort mode with no --cohort-app and no env default exits 2 instead of guessing.

    There used to be a hardcoded DEFAULT_COHORT_APP, and a further fallback to the
    single-consent app, so an omitted flag silently ran someone else's app.
    """
    monkeypatch.delenv("SBG_DEFAULT_COHORT_APP", raising=False)
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("phs000179-HMB", "COPDGene")])

    result = CliRunner().invoke(app, ["submit", "--manifest", str(manifest), "--cohort-mode"])

    assert result.exit_code == 2
    assert "requires an app ID" in result.output
    # Must not fall back to SBG_DEFAULT_APP (the single-consent app).
    assert "test-app" not in result.output


def test_cohort_mode_does_not_fall_back_to_the_single_consent_app(
    sbg_env: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SBG_DEFAULT_APP must not satisfy cohort mode; only the cohort app may."""
    monkeypatch.delenv("SBG_DEFAULT_COHORT_APP", raising=False)
    config = load_config()

    assert config.app == "test/project/test-app/1"
    assert config.cohort_app == ""
    assert DEFAULT_COHORT_APP == ""


def test_plan_requires_an_app_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan used to substitute a `<mode-b-app-id>` placeholder, hiding an omitted flag."""
    monkeypatch.delenv("SBG_DEFAULT_COHORT_APP", raising=False)
    manifest = tmp_path / "tasks.csv"
    _write_manifest(manifest, [("phs000179-HMB", "COPDGene")])

    result = CliRunner().invoke(app, ["plan", "--manifest", str(manifest)])

    assert result.exit_code == 2
    assert "requires an app ID" in result.output
    assert "mode-b-app-id" not in result.output
