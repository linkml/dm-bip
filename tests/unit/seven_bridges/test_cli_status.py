"""Tests for `dm-bip seven-bridges status`."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pytest_httpx import HTTPXMock
from typer.testing import CliRunner

from dm_bip.seven_bridges.cli import app


def test_status_prints_friendly_message_when_no_active_tasks(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Empty tasks list yields 'No active tasks.' and exits 0."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks?project=test/project&status=RUNNING&limit=100",
        json={"items": []},
    )

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0
    assert "No active tasks" in result.output


def test_status_renders_rows_with_health_and_instance(
    sbg_env: Path,  # noqa: ARG001
    seed_token: Callable[[], None],
    httpx_mock: HTTPXMock,
) -> None:
    """Each running task is rendered with its health (Healthy/Zombie/Delay) and instance type."""
    seed_token()
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks?project=test/project&status=RUNNING&limit=100",
        json={"items": [{"id": "t1"}, {"id": "t2"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t1",
        json={"id": "t1", "name": "Harmonization_FHS_MDS", "created_time": "2026-05-19T10:00:00Z"},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t1/execution_details",
        json={"jobs": [{"instance_type": "c5.4xlarge"}]},
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t2",
        json={"id": "t2", "name": "Harmonization_ARIC_HMB", "created_time": "2026-05-19T09:30:00Z"},
    )
    # Zombie: no jobs returned
    httpx_mock.add_response(
        method="GET",
        url="https://api.sbg.test/v2/tasks/t2/execution_details",
        json={"jobs": []},
    )

    result = CliRunner().invoke(app, ["status"])

    assert result.exit_code == 0, result.output
    assert "Harmonization_FHS_MDS" in result.output
    assert "c5.4xlarge" in result.output
    assert "Harmonization_ARIC_HMB" in result.output
    assert "ZOMBIE" in result.output
