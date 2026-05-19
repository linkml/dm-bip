"""Tests for `dm-bip ai-harmonize wait`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.ai_harmonize.cli import app


def test_wait_polls_until_completed(
    harmonize_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Wait polls until the API reports a terminal status, then exits 0."""
    seed_token()
    url = "https://api.test.example/dev/retrieve-job-status/job-1"
    httpx_mock.add_response(method="GET", url=url, json={"status": "processing"})
    httpx_mock.add_response(method="GET", url=url, json={"status": "completed"})

    result = CliRunner().invoke(app, ["wait", "job-1", "--interval", "0"])

    assert result.exit_code == 0
    assert "completed" in result.output


def test_wait_exits_nonzero_on_failure(
    harmonize_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """A terminal 'failed' status causes wait to exit 1 and surface the error_message."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-1",
        json={"status": "failed", "error_message": "MongoDB connection refused"},
    )

    result = CliRunner().invoke(app, ["wait", "job-1", "--interval", "0"])

    assert result.exit_code == 1
    assert "MongoDB connection refused" in result.output
