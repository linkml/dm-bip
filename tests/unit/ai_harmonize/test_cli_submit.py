"""Happy-path test for `dm-bip ai-harmonize submit`."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.ai_harmonize.cli import app


def test_submit_uploads_and_tracks_manifest(
    harmonize_env: Path,
    seed_token: Callable[[], None],
    sample_tsv: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """Submit should request a presigned URL, PUT the file, and persist a manifest using the cached token."""
    seed_token()
    httpx_mock.add_response(
        method="POST",
        url="https://api.test.example/dev/submit-file",
        json={
            "job_id": "20260518_120000_abc",
            "upload_url": "https://s3.test.example/presigned-upload",
            "s3_key": "harmonization/inputs/20260518_120000_abc_vars.tsv",
            "expires_in": 600,
        },
    )
    httpx_mock.add_response(
        method="PUT",
        url="https://s3.test.example/presigned-upload",
        status_code=200,
    )

    result = CliRunner().invoke(
        app,
        ["submit", str(sample_tsv), "--col", "description"],
    )

    assert result.exit_code == 0, result.output
    assert result.output.strip().endswith("20260518_120000_abc")

    manifest_path = harmonize_env / "ai-harmonize-jobs" / "20260518_120000_abc.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["job_id"] == "20260518_120000_abc"
    assert manifest["parameters"]["colname"] == "description"
    assert manifest["s3_input_key"] == "harmonization/inputs/20260518_120000_abc_vars.tsv"

    submit_request = next(req for req in httpx_mock.get_requests() if req.url.path == "/dev/submit-file")
    assert submit_request.headers["Authorization"] == "test-jwt"
    submit_body = json.loads(submit_request.content)
    assert submit_body["action"] == "get_upload_url"
    assert submit_body["filename"] == "vars.tsv"
    assert submit_body["colname"] == "description"
