"""Tests for `dm-bip ai-harmonize list`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.cli import app


def test_list_when_empty(harmonize_env: Path) -> None:  # noqa: ARG001
    """An empty manifest dir prints a friendly placeholder, not an error."""
    result = CliRunner().invoke(app, ["list"])

    assert result.exit_code == 0
    assert "no tracked jobs" in result.output.lower()


def test_list_orders_newest_first_with_json_payload(harmonize_env: Path) -> None:
    """--json emits the saved manifests as a JSON array, newest first."""
    manifest_dir = harmonize_env / "ai-harmonize-jobs"
    storage.save_manifest(
        manifest_dir,
        storage.JobManifest(job_id="old", submitted_at=100.0, parameters={"filename": "old.tsv"}),
    )
    storage.save_manifest(
        manifest_dir,
        storage.JobManifest(job_id="new", submitted_at=200.0, parameters={"filename": "new.tsv"}),
    )

    result = CliRunner().invoke(app, ["list", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert [m["job_id"] for m in parsed] == ["new", "old"]
