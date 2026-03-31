"""Seven Bridges API client — shared configuration and HTTP helpers."""

# ruff: noqa: S310

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SBG_BASE_URL = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
SBG_DEFAULT_PROJECT = "rmathur2/dmc-task-4-controlled"
SBG_DEFAULT_APP = "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/31"
SBG_TOKEN_PATH = Path.home() / ".sevenbridges" / "token"


def get_token() -> str:
    """Resolve SBG auth token from environment or token file."""
    token = os.environ.get("SBG_AUTH_TOKEN", "").strip()
    if token:
        return token
    if SBG_TOKEN_PATH.exists():
        return SBG_TOKEN_PATH.read_text().strip()
    print(
        "Seven Bridges auth token not found.\n\n"
        "Provide it via ONE of:\n"
        f"  1. Environment variable: SBG_AUTH_TOKEN\n"
        f"  2. Token file: {SBG_TOKEN_PATH}\n\n"
        "Get a token at: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token",
        file=sys.stderr,
    )
    sys.exit(1)


def sbg_request(path: str, *, method: str = "GET", body: dict | None = None) -> dict:
    """Make an authenticated request to the SBG API."""
    url = f"{SBG_BASE_URL}/{path.lstrip('/')}"
    headers = {
        "X-SBG-Auth-Token": get_token(),
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"SBG API error {e.code}: {error_body}", file=sys.stderr)
        raise


def get_folders(*, project: str | None = None, parent: str | None = None) -> list[dict]:
    """List folder-type items in a project root or under a parent folder."""
    if project:
        resp = sbg_request(f"files?project={project}")
    elif parent:
        resp = sbg_request(f"files?parent={parent}")
    else:
        raise ValueError("Must provide project or parent")
    return [item for item in resp.get("items", []) if item.get("type") == "folder"]
