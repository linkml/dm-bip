"""Shared fixtures for seven_bridges unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sbg_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point client at a stable test base URL, project, app, and tmp token file. Returns the token file path."""
    token_file = tmp_path / "token"
    monkeypatch.setenv("SBG_BASE_URL", "https://api.sbg.test/v2")
    monkeypatch.setenv("SBG_DEFAULT_PROJECT", "test/project")
    monkeypatch.setenv("SBG_DEFAULT_APP", "test/project/test-app/1")
    monkeypatch.setenv("SBG_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("SBG_AUTH_TOKEN", raising=False)
    return token_file


@pytest.fixture
def seed_token(sbg_env: Path):
    """Write a test token to the configured token file."""

    def _seed(token: str = "test-sbg-token") -> None:  # noqa: S107
        sbg_env.write_text(token)

    return _seed
