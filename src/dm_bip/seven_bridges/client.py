"""HTTP client for the Seven Bridges (BDC) API: token resolution + retry on transient errors."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
DEFAULT_PROJECT = "rmathur2/dmc-task-4-controlled"
DEFAULT_APP = "rmathur2/dmc-task-4-controlled/cc-dm-bip-test/6"
DEFAULT_TOKEN_FILE = Path.home() / ".sevenbridges" / "token"

DEFAULT_TIMEOUT_SECONDS = 30.0
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

TOKEN_HELP_URL = "https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token"  # noqa: S105


class SevenBridgesError(Exception):
    """Raised when the Seven Bridges API returns an unrecoverable error."""


class TokenMissingError(SevenBridgesError):
    """Raised when no auth token is configured (no env var, no token file)."""


@dataclass(frozen=True)
class Config:
    """Resolved configuration: base URL, project/app defaults, token file location."""

    base_url: str
    project: str
    app: str
    token_file: Path


def load_config() -> Config:
    """Build a Config from environment variables, falling back to documented defaults."""
    return Config(
        base_url=os.environ.get("SBG_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        project=os.environ.get("SBG_DEFAULT_PROJECT", DEFAULT_PROJECT),
        app=os.environ.get("SBG_DEFAULT_APP", DEFAULT_APP),
        token_file=Path(os.environ.get("SBG_TOKEN_FILE") or DEFAULT_TOKEN_FILE),
    )


def get_token(config: Config) -> str:
    """Resolve the SBG auth token from the SBG_AUTH_TOKEN env var or token file."""
    env_token = os.environ.get("SBG_AUTH_TOKEN", "").strip()
    if env_token:
        return env_token
    if config.token_file.exists():
        return config.token_file.read_text().strip()
    raise TokenMissingError(
        f"Seven Bridges auth token not found.\n"
        f"  - Set SBG_AUTH_TOKEN, or\n"
        f"  - Place the token in {config.token_file}\n"
        f"Get a token: {TOKEN_HELP_URL}"
    )


def _request_with_retry(
    http: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json: Any = None,
    timeout: float | None = None,
) -> httpx.Response:
    """Issue an HTTP request, retrying on 429/5xx with exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            response = http.request(method, url, headers=headers, json=json, timeout=timeout)
        except httpx.TransportError as exc:
            last_exc = exc
            logger.debug("Transport error on attempt %d/%d: %s", attempt, RETRY_MAX_ATTEMPTS, exc)
        else:
            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response
            logger.debug(
                "Retryable status %d on attempt %d/%d for %s %s",
                response.status_code,
                attempt,
                RETRY_MAX_ATTEMPTS,
                method,
                url,
            )
            last_exc = SevenBridgesError(f"HTTP {response.status_code}: {response.text[:200]}")

        if attempt < RETRY_MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    raise SevenBridgesError(f"Request failed after {RETRY_MAX_ATTEMPTS} attempts: {last_exc}")


class Client:
    """Authenticated session against the Seven Bridges API; reads token from env or file."""

    def __init__(self, config: Config, http: httpx.Client | None = None) -> None:
        """Create a client; pass an httpx.Client to override the default (useful for tests)."""
        self.config = config
        self.http = http or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)

    def _auth_headers(self) -> dict[str, str]:
        return {
            "X-SBG-Auth-Token": get_token(self.config),
            "Content-Type": "application/json",
        }

    def request(self, path: str, *, method: str = "GET", body: dict | None = None) -> dict:
        """
        Make an authenticated API request and return the parsed JSON body.

        Accepts either a relative path (joined to the configured base URL) or a full URL
        (used as-is — needed for SBG-returned download_info URLs).
        """
        url = path if path.startswith(("http://", "https://")) else f"{self.config.base_url}/{path.lstrip('/')}"
        response = _request_with_retry(self.http, method, url, headers=self._auth_headers(), json=body)
        if not 200 <= response.status_code < 300:
            raise SevenBridgesError(f"SBG {method} {path} failed ({response.status_code}): {response.text[:300]}")
        return response.json()

    def get_folders(self, *, project: str | None = None, parent: str | None = None) -> list[dict]:
        """List folder-type items in a project root or under a parent folder."""
        if project:
            resp = self.request(f"files?project={project}")
        elif parent:
            resp = self.request(f"files?parent={parent}")
        else:
            raise ValueError("Must provide project or parent")
        return [item for item in resp.get("items", []) if item.get("type") == "folder"]

    def download(self, url: str, *, timeout: float = 60.0) -> str:
        """Fetch raw text content from a URL (used for SBG log download URLs); no auth header."""
        response = self.http.get(url, timeout=timeout)
        if response.status_code != 200:
            raise SevenBridgesError(f"Download failed ({response.status_code}): {response.text[:300]}")
        return response.text
