"""Configuration for the AI harmonize client — env var resolution with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_API_URL = "https://c0zz109oak.execute-api.us-east-1.amazonaws.com/dev"

_XDG_CACHE_HOME = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
DEFAULT_CACHE_DIR = _XDG_CACHE_HOME / "dm-bip"


@dataclass(frozen=True)
class Config:
    """Resolved configuration: API endpoint + cache directory paths."""

    api_url: str
    cache_dir: Path

    @property
    def token_cache_path(self) -> Path:
        """Path to the cached JWT id-token JSON file."""
        return self.cache_dir / "ai-harmonize-token.json"

    @property
    def job_manifest_dir(self) -> Path:
        """Directory holding per-job manifest JSON files."""
        return self.cache_dir / "ai-harmonize-jobs"


def load_config() -> Config:
    """Build a Config from environment variables, falling back to documented defaults."""
    return Config(
        api_url=os.environ.get("AI_HARMONIZE_API_URL", DEFAULT_API_URL).rstrip("/"),
        cache_dir=Path(os.environ.get("AI_HARMONIZE_CACHE_DIR") or DEFAULT_CACHE_DIR),
    )
