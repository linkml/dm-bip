"""Shared fixtures for ai_harmonize unit tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from dm_bip.ai_harmonize import storage


@pytest.fixture
def harmonize_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Point the wrapper at a tmp cache dir and a stable API URL; returns the cache dir."""
    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("AI_HARMONIZE_API_URL", "https://api.test.example/dev")
    monkeypatch.setenv("AI_HARMONIZE_CACHE_DIR", str(cache_dir))
    monkeypatch.delenv("AI_HARMONIZE_TOKEN", raising=False)
    return cache_dir


@pytest.fixture
def sample_tsv(tmp_path: Path) -> Path:
    """Create a tiny TSV file for upload tests."""
    path = tmp_path / "vars.tsv"
    path.write_text("name\tdescription\nbmi\tBody Mass Index\n")
    return path


@pytest.fixture
def seed_token(harmonize_env: Path) -> Callable[[], None]:
    """Return a callable that pre-populates the token cache so tests skip Cognito auth."""

    def _seed() -> None:
        token = "test-jwt"  # noqa: S105  (placeholder, not a real credential)
        storage.save_token(
            harmonize_env / "ai-harmonize-token.json",
            storage.CachedToken(token=token, expires_at=None),
        )

    return _seed
