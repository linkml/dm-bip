"""Tests for `dm-bip ai-harmonize fetch`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.ai_harmonize.cli import app


def test_fetch_downloads_results_when_job_completed(
    harmonize_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """Fetch should follow the download_url and write its contents to the requested output path."""
    seed_token()
    output_path = tmp_path / "results.csv"
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-1?include_download_url=true",
        json={
            "status": "completed",
            "download_url": "https://s3.test.example/results.csv",
        },
    )
    httpx_mock.add_response(
        method="GET",
        url="https://s3.test.example/results.csv",
        content=b"original,matched\nbmi,body_mass_index\n",
    )

    result = CliRunner().invoke(app, ["fetch", "job-1", "--output", str(output_path)])

    assert result.exit_code == 0
    assert output_path.read_bytes() == b"original,matched\nbmi,body_mass_index\n"


def test_fetch_refuses_when_job_not_completed(
    harmonize_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """Fetch exits non-zero with a clear message when the job is still processing."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-1?include_download_url=true",
        json={"status": "processing"},
    )

    result = CliRunner().invoke(app, ["fetch", "job-1", "--output", str(tmp_path / "x.csv")])

    assert result.exit_code == 1
    assert "not complete" in result.output.lower()
