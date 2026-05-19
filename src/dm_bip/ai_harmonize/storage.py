"""Local persistence for the AI harmonize client: token cache + job manifests."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CachedToken:
    """A JWT id-token with its expiry (from the JWT's `exp` claim, or None if undecodable)."""

    token: str
    expires_at: float | None = None


def load_token(path: Path) -> CachedToken | None:
    """Load a cached token from disk; returns None if missing, unreadable, or malformed."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        expires_raw = data.get("expires_at")
        return CachedToken(
            token=data["token"],
            expires_at=float(expires_raw) if expires_raw is not None else None,
        )
    except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
        logger.debug("Discarding unreadable token cache at %s: %s", path, exc)
        return None


def save_token(path: Path, token: CachedToken) -> None:
    """Write a token to disk with restrictive (user-only) permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(token)))
    os.chmod(path, 0o600)


@dataclass
class JobManifest:
    """Local record of a submitted job — params, S3 keys, status snapshot."""

    job_id: str
    submitted_at: float
    parameters: dict[str, Any]
    s3_input_key: str | None = None
    last_status: str | None = None
    s3_output_path: str | None = None


def save_manifest(manifest_dir: Path, manifest: JobManifest) -> Path:
    """Persist a job manifest under `<manifest_dir>/<job_id>.json`; returns the path written."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    out = manifest_dir / f"{manifest.job_id}.json"
    out.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True))
    return out


def load_manifest(manifest_dir: Path, job_id: str) -> JobManifest | None:
    """Load a previously saved manifest by job_id; None if missing, unreadable, or malformed."""
    path = manifest_dir / f"{job_id}.json"
    if not path.exists():
        return None
    try:
        return JobManifest(**json.loads(path.read_text()))
    except (json.JSONDecodeError, TypeError, OSError) as exc:
        logger.debug("Discarding unreadable manifest at %s: %s", path, exc)
        return None


def list_manifests(manifest_dir: Path) -> list[JobManifest]:
    """Return all saved manifests sorted by submission time, newest first."""
    if not manifest_dir.exists():
        return []
    manifests = []
    for path in manifest_dir.glob("*.json"):
        try:
            manifests.append(JobManifest(**json.loads(path.read_text())))
        except (json.JSONDecodeError, TypeError, OSError) as exc:
            logger.debug("Skipping unreadable manifest %s: %s", path, exc)
    manifests.sort(key=lambda m: m.submitted_at, reverse=True)
    return manifests
