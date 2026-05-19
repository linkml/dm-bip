"""Tests for `dm-bip ai-harmonize status`."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.cli import app


def test_status_prints_status_and_updates_manifest(
    harmonize_env: Path,
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Status should print the API's status field and refresh the local manifest."""
    seed_token()
    manifest_dir = harmonize_env / "ai-harmonize-jobs"
    storage.save_manifest(
        manifest_dir,
        storage.JobManifest(job_id="job-1", submitted_at=100.0, parameters={"colname": "desc"}),
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-1",
        json={"status": "processing", "job_id": "job-1"},
    )

    result = CliRunner().invoke(app, ["status", "job-1"])

    assert result.exit_code == 0
    assert result.output.strip() == "processing"

    updated = storage.load_manifest(manifest_dir, "job-1")
    assert updated is not None
    assert updated.last_status == "processing"


def test_status_with_json_flag_dumps_full_payload(
    harmonize_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """--json emits the full API response, not just the status field."""
    seed_token()
    payload = {"status": "completed", "job_id": "job-2", "processing_time_seconds": 42.5}
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-2",
        json=payload,
    )

    result = CliRunner().invoke(app, ["status", "job-2", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed == payload
