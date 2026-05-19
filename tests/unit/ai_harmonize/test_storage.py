"""Tests for the token cache and job manifest storage layer."""

from __future__ import annotations

from pathlib import Path

from dm_bip.ai_harmonize.storage import (
    CachedToken,
    JobManifest,
    list_manifests,
    load_manifest,
    load_token,
    save_manifest,
    save_token,
)


def test_token_roundtrip_preserves_value_and_expiry(tmp_path: Path) -> None:
    """save_token then load_token returns an equivalent CachedToken."""
    path = tmp_path / "token.json"
    token = CachedToken(token="jwt-value", expires_at=1_700_000_000.0)  # noqa: S106

    save_token(path, token)
    loaded = load_token(path)

    assert loaded is not None
    assert loaded.token == token.token
    assert loaded.expires_at == token.expires_at


def test_token_roundtrip_handles_unknown_expiry(tmp_path: Path) -> None:
    """A token saved with expires_at=None round-trips correctly (graceful JWT-decode fallback)."""
    path = tmp_path / "token.json"
    save_token(path, CachedToken(token="opaque", expires_at=None))  # noqa: S106

    loaded = load_token(path)

    assert loaded is not None
    assert loaded.token == "opaque"  # noqa: S105
    assert loaded.expires_at is None


def test_load_token_returns_none_for_missing_or_malformed(tmp_path: Path) -> None:
    """Missing or unreadable token files yield None rather than raising."""
    assert load_token(tmp_path / "missing.json") is None

    bad = tmp_path / "bad.json"
    bad.write_text("not-json")
    assert load_token(bad) is None


def test_manifest_roundtrip(tmp_path: Path) -> None:
    """save_manifest then load_manifest preserves all fields."""
    manifest = JobManifest(
        job_id="job-1",
        submitted_at=123456.0,
        parameters={"colname": "description"},
        s3_input_key="inputs/job-1.tsv",
        last_status="processing",
        s3_output_path=None,
    )

    save_manifest(tmp_path, manifest)
    loaded = load_manifest(tmp_path, "job-1")

    assert loaded == manifest


def test_list_manifests_sorts_newest_first(tmp_path: Path) -> None:
    """list_manifests returns manifests ordered by submitted_at descending."""
    save_manifest(tmp_path, JobManifest(job_id="old", submitted_at=100.0, parameters={}))
    save_manifest(tmp_path, JobManifest(job_id="new", submitted_at=200.0, parameters={}))
    save_manifest(tmp_path, JobManifest(job_id="mid", submitted_at=150.0, parameters={}))

    listed = list_manifests(tmp_path)

    assert [m.job_id for m in listed] == ["new", "mid", "old"]


def test_list_manifests_skips_malformed_files(tmp_path: Path) -> None:
    """A non-JSON file in the manifest dir doesn't break list_manifests."""
    save_manifest(tmp_path, JobManifest(job_id="good", submitted_at=100.0, parameters={}))
    (tmp_path / "broken.json").write_text("{not json")

    listed = list_manifests(tmp_path)

    assert len(listed) == 1
    assert listed[0].job_id == "good"
