"""Tests for the Client: token sourcing, retry behavior, 401 handling, JWT decode."""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.client import (
    TOKEN_REFRESH_HINT,
    Client,
    HarmonizeError,
    TokenMissingError,
    decode_jwt_expiry,
)
from dm_bip.ai_harmonize.config import load_config


@pytest.fixture
def client(harmonize_env: Path) -> Client:  # noqa: ARG001
    """Construct a Client wired to the test env (harmonize_env applies the env vars)."""
    return Client(load_config())


def _make_jwt(claims: dict) -> str:
    """Build a minimal-but-decodable JWT string (no signature; we only care about the payload)."""
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"header.{payload}.signature"


def test_decode_jwt_expiry_reads_exp_claim() -> None:
    """decode_jwt_expiry returns the `exp` value from a valid JWT payload."""
    jwt = _make_jwt({"exp": 1700000000, "sub": "anyone"})
    assert decode_jwt_expiry(jwt) == 1700000000.0


def test_decode_jwt_expiry_returns_none_for_non_jwt() -> None:
    """A string that doesn't look like a JWT returns None instead of raising."""
    assert decode_jwt_expiry("not-a-jwt") is None
    assert decode_jwt_expiry("missing.exp_claim.sig") is None


def test_get_token_prefers_env_var_over_cache(
    client: Client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If AI_HARMONIZE_TOKEN is set, it overrides whatever is in the cache file."""
    storage.save_token(
        client.config.token_cache_path,
        storage.CachedToken(token="from-cache", expires_at=None),  # noqa: S106
    )
    monkeypatch.setenv("AI_HARMONIZE_TOKEN", "from-env")

    assert client.get_token() == "from-env"


def test_get_token_falls_back_to_cache(client: Client) -> None:
    """With no env var set, get_token reads the cached token."""
    storage.save_token(
        client.config.token_cache_path,
        storage.CachedToken(token="from-cache", expires_at=None),  # noqa: S106
    )

    assert client.get_token() == "from-cache"


def test_get_token_raises_when_neither_env_nor_cache(client: Client) -> None:
    """With no token anywhere, get_token raises a TokenMissingError pointing at set-token."""
    with pytest.raises(TokenMissingError, match="set-token"):
        client.get_token()


def test_api_401_raises_with_token_refresh_hint(
    client: Client,
    httpx_mock: HTTPXMock,
) -> None:
    """A 401 from any API endpoint surfaces the token-refresh hint via HarmonizeError."""
    storage.save_token(
        client.config.token_cache_path,
        storage.CachedToken(token="stale", expires_at=None),  # noqa: S106
    )
    httpx_mock.add_response(
        method="GET",
        url="https://api.test.example/dev/retrieve-job-status/job-1",
        status_code=401,
        text="Unauthorized",
    )

    with pytest.raises(HarmonizeError) as excinfo:
        client.get_status("job-1")
    assert str(excinfo.value) == TOKEN_REFRESH_HINT


def test_request_retries_on_transient_error_then_succeeds(
    client: Client,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A 503 from /submit-file is retried; subsequent 200 returns the parsed body."""
    monkeypatch.setattr("dm_bip.ai_harmonize.client.time.sleep", lambda _: None)
    storage.save_token(
        client.config.token_cache_path,
        storage.CachedToken(token="jwt", expires_at=None),  # noqa: S106
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.test.example/dev/submit-file",
        status_code=503,
        text="upstream busy",
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.test.example/dev/submit-file",
        json={"job_id": "j1", "upload_url": "https://s3/u", "s3_key": "k"},
    )

    result = client.request_upload_url(filename="x.tsv", colname="desc")

    assert result["job_id"] == "j1"
    assert len([r for r in httpx_mock.get_requests() if r.url.path == "/dev/submit-file"]) == 2


def test_request_raises_after_retries_exhausted(
    client: Client,
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If 5xx persists past RETRY_MAX_ATTEMPTS, surface a HarmonizeError."""
    monkeypatch.setattr("dm_bip.ai_harmonize.client.time.sleep", lambda _: None)
    storage.save_token(
        client.config.token_cache_path,
        storage.CachedToken(token="jwt", expires_at=None),  # noqa: S106
    )
    httpx_mock.add_response(
        method="POST",
        url="https://api.test.example/dev/submit-file",
        status_code=503,
        text="upstream busy",
        is_reusable=True,
    )

    with pytest.raises(HarmonizeError):
        client.request_upload_url(filename="x.tsv", colname="desc")
