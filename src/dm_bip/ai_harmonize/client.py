"""HTTP client for RTI's hosted variable-harmonization API: token-based, with retry on transient errors."""

from __future__ import annotations

import base64
import json as _json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.config import Config

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
UPLOAD_TIMEOUT_SECONDS = 600.0
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

TOKEN_REFRESH_HINT = "Token expired or invalid. Refresh with `dm-bip ai-harmonize set-token <new-token>`."  # noqa: S105


class HarmonizeError(Exception):
    """Raised when the harmonization API returns an unrecoverable error."""


class TokenMissingError(HarmonizeError):
    """Raised when no token is configured (no env var, no cache file)."""


_CONTENT_TYPES = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def content_type_for(filename: str) -> str:
    """Pick the S3 Content-Type for a given filename based on extension; defaults to octet-stream."""
    return _CONTENT_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


def decode_jwt_expiry(token: str) -> float | None:
    """Extract the `exp` claim from a JWT; returns None if the token isn't a decodable JWT."""
    try:
        _header, payload_b64, _sig = token.split(".")
    except ValueError:
        return None
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    try:
        payload = _json.loads(base64.urlsafe_b64decode(padded))
        return float(payload["exp"])
    except (ValueError, KeyError, _json.JSONDecodeError):
        return None


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
            last_exc = HarmonizeError(f"HTTP {response.status_code}: {response.text[:200]}")

        if attempt < RETRY_MAX_ATTEMPTS:
            time.sleep(RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    raise HarmonizeError(f"Request failed after {RETRY_MAX_ATTEMPTS} attempts: {last_exc}")


class Client:
    """Session against the harmonization API; reads token from env var or cache file."""

    def __init__(self, config: Config, http: httpx.Client | None = None) -> None:
        """Create a client; pass an httpx.Client to override the default (useful for tests)."""
        self.config = config
        self.http = http or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)

    def get_token(self) -> str:
        """Return the JWT id-token from env or cache; raises TokenMissingError if neither has one."""
        env_token = os.environ.get("AI_HARMONIZE_TOKEN", "").strip()
        if env_token:
            return env_token
        cached = storage.load_token(self.config.token_cache_path)
        if cached:
            return cached.token
        raise TokenMissingError(
            "No token configured. Set one with `dm-bip ai-harmonize set-token <jwt>` "
            "or via the AI_HARMONIZE_TOKEN env var."
        )

    def _api_call(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Hit an API endpoint with auth + retry; raise on 401 / non-2xx; return parsed JSON."""
        url = f"{self.config.api_url}/{path.lstrip('/')}"
        headers = {"Authorization": self.get_token()}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        response = _request_with_retry(self.http, method, url, headers=headers, json=json_body, timeout=timeout)
        if response.status_code == 401:
            raise HarmonizeError(TOKEN_REFRESH_HINT)
        if not 200 <= response.status_code < 300:
            raise HarmonizeError(f"{path} failed ({response.status_code}): {response.text[:300]}")
        return response.json()

    def request_upload_url(
        self,
        *,
        filename: str,
        colname: str,
        subset: str = "",
        pool: int = 10,
        chunk_size: int = 10,
        lim: int | None = None,
    ) -> dict[str, Any]:
        """Request a presigned S3 upload URL via /submit-file; returns dict with job_id, upload_url, s3_key."""
        body: dict[str, Any] = {
            "action": "get_upload_url",
            "filename": filename,
            "colname": colname,
            "subset": subset,
            "pool": pool,
            "chunk_size": chunk_size,
        }
        if lim is not None:
            body["lim"] = lim
        return self._api_call("POST", "submit-file", json_body=body)

    def upload_file(self, upload_url: str, path: Path, content_type: str) -> None:
        """PUT a file to a presigned S3 URL — no auth header (URL is pre-signed)."""
        logger.info("Uploading %s (%d bytes) to S3", path.name, path.stat().st_size)
        with path.open("rb") as fh:
            response = self.http.put(
                upload_url,
                content=fh.read(),
                headers={"Content-Type": content_type},
                timeout=UPLOAD_TIMEOUT_SECONDS,
            )
        if response.status_code not in (200, 204):
            raise HarmonizeError(f"S3 upload failed ({response.status_code}): {response.text[:300]}")

    def get_status(self, job_id: str, *, include_download_url: bool = False) -> dict[str, Any]:
        """GET /retrieve-job-status/{job_id}, optionally requesting a presigned download URL."""
        path = f"retrieve-job-status/{job_id}"
        if include_download_url:
            path += "?include_download_url=true"
        return self._api_call("GET", path)

    def download_results(self, download_url: str, output_path: Path) -> None:
        """Fetch results from a presigned S3 URL and write them to output_path."""
        logger.info("Downloading results to %s", output_path)
        response = self.http.get(download_url, timeout=UPLOAD_TIMEOUT_SECONDS)
        if response.status_code != 200:
            raise HarmonizeError(f"Download failed ({response.status_code}): {response.text[:300]}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
