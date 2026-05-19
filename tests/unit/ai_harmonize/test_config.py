"""Tests for the AI harmonize config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from dm_bip.ai_harmonize.config import DEFAULT_API_URL, DEFAULT_CACHE_DIR, load_config


def test_load_config_uses_defaults_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """API URL and cache dir fall back to documented defaults when no env overrides are set."""
    monkeypatch.delenv("AI_HARMONIZE_API_URL", raising=False)
    monkeypatch.delenv("AI_HARMONIZE_CACHE_DIR", raising=False)

    config = load_config()

    assert config.api_url == DEFAULT_API_URL
    assert config.cache_dir == DEFAULT_CACHE_DIR


def test_load_config_respects_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Both endpoint and cache location accept env overrides."""
    monkeypatch.setenv("AI_HARMONIZE_API_URL", "https://override.example/v1/")
    monkeypatch.setenv("AI_HARMONIZE_CACHE_DIR", str(tmp_path))

    config = load_config()

    assert config.api_url == "https://override.example/v1"  # trailing slash stripped
    assert config.cache_dir == tmp_path


def test_config_derives_token_and_manifest_paths(tmp_path: Path) -> None:
    """The cache_dir drives the locations of the token cache and manifest dir."""
    from dm_bip.ai_harmonize.config import Config

    config = Config(api_url="https://x", cache_dir=tmp_path)

    assert config.token_cache_path == tmp_path / "ai-harmonize-token.json"
    assert config.job_manifest_dir == tmp_path / "ai-harmonize-jobs"
