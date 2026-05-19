"""Tests for `dm-bip ai-harmonize set-token`."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from typer.testing import CliRunner

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.cli import app


def _make_jwt(claims: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{payload}.signature"


def test_set_token_decodes_expiry_and_writes_cache(harmonize_env: Path) -> None:
    """A valid JWT lands in the cache with its `exp` claim parsed into expires_at."""
    jwt = _make_jwt({"exp": 1700000000, "sub": "test-user"})

    result = CliRunner().invoke(app, ["set-token", jwt])

    assert result.exit_code == 0
    assert "expires" in result.output.lower()

    cached = storage.load_token(harmonize_env / "ai-harmonize-token.json")
    assert cached is not None
    assert cached.token == jwt
    assert cached.expires_at == 1700000000.0


def test_set_token_accepts_non_jwt_with_unknown_expiry(harmonize_env: Path) -> None:
    """An opaque (non-JWT) token still gets cached; output flags the unknown expiry."""
    result = CliRunner().invoke(app, ["set-token", "opaque-token-blob"])

    assert result.exit_code == 0
    assert "expiry could not be determined" in result.output.lower()

    cached = storage.load_token(harmonize_env / "ai-harmonize-token.json")
    assert cached is not None
    assert cached.token == "opaque-token-blob"  # noqa: S105
    assert cached.expires_at is None
