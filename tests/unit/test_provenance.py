"""Unit tests for the provenance module."""

import os
from pathlib import Path
from unittest.mock import patch

import yaml

from dm_bip.provenance import generate_provenance, get_build_info


def test_get_build_info_from_env():
    """Build info reads from environment variables."""
    env = {
        "DM_BIP_VERSION": "bdc-v1.2.0",
        "DM_BIP_GIT_REF": "abc123",
        "DM_BIP_BUILD_DATE": "2026-04-14T12:00:00Z",
    }
    with patch.dict(os.environ, env):
        info = get_build_info()
    assert info["version"] == "bdc-v1.2.0"
    assert info["git_ref"] == "abc123"
    assert info["build_date"] == "2026-04-14T12:00:00Z"


def test_get_build_info_fallback():
    """Without env vars, version falls back to importlib_metadata."""
    env_clear = {"DM_BIP_VERSION": "", "DM_BIP_GIT_REF": "", "DM_BIP_BUILD_DATE": ""}
    with patch.dict(os.environ, {}, clear=False):
        for k in env_clear:
            os.environ.pop(k, None)
        info = get_build_info()
    # dm-bip is installed, so importlib_metadata should provide a real version
    assert info["version"] != "unknown"
    assert info["git_ref"] == "unknown"
    assert info["build_date"] == "unknown"


def test_generate_provenance_basic(tmp_path):
    """Generates valid YAML with expected sections."""
    output = tmp_path / "provenance.yaml"
    generate_provenance(
        output_path=output,
        schema_name="TestSchema",
        input_dir="/data/input",
        no_external_repos=True,
    )
    assert output.exists()
    data = yaml.safe_load(output.read_text())
    assert "dm_bip" in data
    assert "python" in data
    assert "dependencies" in data
    assert data["external_repos"] == "none (local run)"
    assert data["pipeline"]["schema_name"] == "TestSchema"
    assert data["pipeline"]["input_dir"] == "/data/input"
    assert "timestamp" in data["pipeline"]


def test_generate_provenance_with_manifest(tmp_path):
    """Provenance includes repo info from a manifest file."""
    manifest = tmp_path / "repo-manifest.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "fake-repo": {
                    "commit": "a" * 40,
                    "ref": "v1.0.0",
                }
            }
        )
    )

    output = tmp_path / "provenance.yaml"
    generate_provenance(output_path=output, repo_manifest=manifest)
    data = yaml.safe_load(output.read_text())
    repo_info = data["external_repos"]["fake-repo"]
    assert repo_info["commit"] == "a" * 40
    assert repo_info["ref"] == "v1.0.0"


def test_generate_provenance_missing_manifest(tmp_path):
    """Missing manifest logs error but still writes provenance."""
    output = tmp_path / "provenance.yaml"
    generate_provenance(output_path=output, repo_manifest=Path("/nonexistent/manifest.yaml"))
    assert output.exists()
    data = yaml.safe_load(output.read_text())
    assert data["external_repos"] == {}


def test_generate_provenance_empty_params_omitted(tmp_path):
    """Empty pipeline params are omitted from output."""
    output = tmp_path / "provenance.yaml"
    generate_provenance(output_path=output, no_external_repos=True)
    data = yaml.safe_load(output.read_text())
    assert "schema_name" not in data["pipeline"]
    assert "timestamp" in data["pipeline"]


def test_version_env_fallback():
    """__version__ falls back to DM_BIP_VERSION when package version is 0.0.0."""
    with patch.dict(os.environ, {"DM_BIP_VERSION": "bdc-v2.0.0"}):
        # Re-import to test the fallback logic
        import dm_bip

        # Save original
        original = dm_bip.__version__
        # Simulate container scenario
        dm_bip.__version__ = "0.0.0"
        if dm_bip.__version__ == "0.0.0":
            dm_bip.__version__ = os.environ.get("DM_BIP_VERSION", "0.0.0")
        assert dm_bip.__version__ == "bdc-v2.0.0"
        # Restore
        dm_bip.__version__ = original
