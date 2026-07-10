"""Tests for `dm-bip seven-bridges logs`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.seven_bridges.cli import app


def test_logs_lists_recent_tasks_when_no_task_id_given(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Without a task_id, logs lists recent completed/failed tasks grouped by status."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks?project=test/project&status=COMPLETED&limit=10",
        json={"items": [{"id": "t-ok", "name": "Harmonization_FHS_MDS"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks?project=test/project&status=FAILED&limit=10",
        json={"items": [{"id": "t-bad", "name": "Harmonization_ARIC_HMB"}]},
    )

    result = CliRunner().invoke(app, ["logs"])

    assert result.exit_code == 0, result.output
    assert "COMPLETED tasks" in result.output
    assert "t-ok  Harmonization_FHS_MDS" in result.output
    assert "FAILED tasks" in result.output
    assert "t-bad" in result.output


def test_logs_downloads_stderr_by_default(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    tmp_path: Path,
    httpx_mock: HTTPXMock,
) -> None:
    """With a task_id and no flag, only stderr is fetched (default behavior)."""
    seed_token()
    download_info_url = "https://api.sbg.test/v2/tasks/t1/jobs/job1/logs/stderr_dm_bip.log"
    signed_url = "https://s3.test.example/signed/stderr.log"

    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t1",
        json={"id": "t1", "name": "Run1", "status": "FAILED"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t1/execution_details",
        json={
            "jobs": [
                {
                    "name": "job1",
                    "status": "FAILED",
                    "logs": {
                        "stdout_dm_bip.log": "https://api.sbg.test/v2/tasks/t1/jobs/job1/logs/stdout_dm_bip.log",
                        "stderr_dm_bip.log": download_info_url,
                    },
                }
            ]
        },
    )
    httpx_mock.add_response(
        method="GET",
        url=download_info_url,
        json={"url": signed_url},
    )
    httpx_mock.add_response(
        method="GET",
        url=signed_url,
        text="OSError: out of disk space\n",
    )

    result = CliRunner().invoke(app, ["logs", "t1", "--output-dir", str(tmp_path)])

    assert result.exit_code == 0, result.output
    log_path = tmp_path / "Run1" / "job1.stderr_dm_bip.log"
    assert log_path.exists()
    assert log_path.read_text() == "OSError: out of disk space\n"

    # stdout should NOT have been fetched (default is stderr-only)
    requests = httpx_mock.get_requests()
    stdout_url = "https://api.sbg.test/v2/tasks/t1/jobs/job1/logs/stdout_dm_bip.log"
    assert not any(r.url == stdout_url for r in requests)
