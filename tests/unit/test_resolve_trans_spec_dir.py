"""Unit tests for scripts/workflow/resolve_trans_spec_dir.py."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "workflow" / "resolve_trans_spec_dir.py"


def _load_module():
    """Import the script as a module so we can test its functions directly."""
    spec = importlib.util.spec_from_file_location("resolve_trans_spec_dir", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_module = _load_module()
resolve_trans_spec_dir = _module.resolve_trans_spec_dir
_version_sort_key = _module._version_sort_key


# --- Version sort key -------------------------------------------------------


def test_version_sort_numeric():
    """Numeric components sort numerically, not lexicographically."""
    names = ["v1.2", "v1.10", "v1.1", "v2.0"]
    assert sorted(names, key=_version_sort_key) == ["v1.1", "v1.2", "v1.10", "v2.0"]


def test_version_sort_mixed_chunks():
    """Names with mixed text and numbers sort coherently."""
    names = ["1.0.0", "1.0.10", "1.0.2", "2.0.0"]
    assert sorted(names, key=_version_sort_key) == ["1.0.0", "1.0.2", "1.0.10", "2.0.0"]


# --- Explicit path branch ---------------------------------------------------


def test_explicit_path_resolves(tmp_path):
    """When explicit_path is given, returns repo_dir / explicit_path."""
    target = tmp_path / "some" / "nested" / "dir"
    target.mkdir(parents=True)
    assert resolve_trans_spec_dir(tmp_path, "ANY", "some/nested/dir") == target


def test_explicit_path_missing_dir_raises(tmp_path):
    """Explicit path that doesn't exist raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        resolve_trans_spec_dir(tmp_path, "FHS", "missing/dir")


def test_explicit_path_absolute_rejected(tmp_path):
    """Absolute explicit_path is rejected."""
    with pytest.raises(ValueError, match="must be relative"):
        resolve_trans_spec_dir(tmp_path, "FHS", "/etc/passwd")


def test_explicit_path_traversal_rejected(tmp_path):
    """explicit_path containing '..' is rejected."""
    with pytest.raises(ValueError, match="must be relative"):
        resolve_trans_spec_dir(tmp_path, "FHS", "../outside")


# --- NHLBI-BDC-DMC-HV layout ------------------------------------------------


def test_hv_layout_resolves(tmp_path):
    """priority_variables_transform/<SCHEMA>-ingest layout is auto-detected."""
    target = tmp_path / "priority_variables_transform" / "FHS-ingest"
    target.mkdir(parents=True)
    assert resolve_trans_spec_dir(tmp_path, "FHS") == target


def test_hv_layout_missing_schema_subdir_raises(tmp_path):
    """HV layout present but schema subdir missing raises FileNotFoundError."""
    (tmp_path / "priority_variables_transform").mkdir()
    with pytest.raises(FileNotFoundError, match="Auto-detected"):
        resolve_trans_spec_dir(tmp_path, "MISSING")


# --- bdc-harmonized-variables layout ----------------------------------------


def test_bhv_layout_picks_latest_version(tmp_path):
    """trans_specs/<SCHEMA>/<VERSIONS> layout picks the highest version."""
    base = tmp_path / "trans_specs" / "FHS"
    for v in ("v1.0", "v1.10", "v1.2", "v2.0"):
        (base / v).mkdir(parents=True)
    assert resolve_trans_spec_dir(tmp_path, "FHS") == base / "v2.0"


def test_bhv_layout_single_version(tmp_path):
    """Single version dir is returned as-is."""
    target = tmp_path / "trans_specs" / "COPDGene" / "v1.0"
    target.mkdir(parents=True)
    assert resolve_trans_spec_dir(tmp_path, "COPDGene") == target


def test_bhv_layout_ignores_files_at_version_level(tmp_path):
    """Stray files alongside version dirs are ignored."""
    base = tmp_path / "trans_specs" / "FHS"
    base.mkdir(parents=True)
    (base / "v1.0").mkdir()
    (base / "README.md").write_text("stray file")
    assert resolve_trans_spec_dir(tmp_path, "FHS") == base / "v1.0"


def test_bhv_layout_no_schema_subdir_raises(tmp_path):
    """trans_specs/ present but no dir for the requested schema."""
    (tmp_path / "trans_specs" / "OTHER").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="No trans-spec directory for schema"):
        resolve_trans_spec_dir(tmp_path, "MISSING")


def test_bhv_layout_no_versions_raises(tmp_path):
    """Schema subdir exists but has no version subdirectories."""
    (tmp_path / "trans_specs" / "FHS").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="No trans-spec version directory"):
        resolve_trans_spec_dir(tmp_path, "FHS")


# --- Layout precedence and errors -------------------------------------------


def test_hv_layout_preferred_over_bhv_when_both_present(tmp_path):
    """If both layouts are present, HV (priority_variables_transform) wins."""
    hv = tmp_path / "priority_variables_transform" / "FHS-ingest"
    hv.mkdir(parents=True)
    (tmp_path / "trans_specs" / "FHS" / "v1.0").mkdir(parents=True)
    assert resolve_trans_spec_dir(tmp_path, "FHS") == hv


def test_unknown_layout_raises(tmp_path):
    """Neither layout present raises with a helpful message."""
    (tmp_path / "some-other-dir").mkdir()
    with pytest.raises(ValueError, match="Cannot auto-detect"):
        resolve_trans_spec_dir(tmp_path, "FHS")


def test_missing_repo_dir_raises(tmp_path):
    """Nonexistent repo_dir raises ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        resolve_trans_spec_dir(tmp_path / "nope", "FHS")


# --- CLI / shell-contract tests ---------------------------------------------


def _run(*args) -> subprocess.CompletedProcess:
    """Invoke the script and return the completed process."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_prints_resolved_path(tmp_path):
    """Successful resolution prints a single absolute path on stdout."""
    target = tmp_path / "priority_variables_transform" / "FHS-ingest"
    target.mkdir(parents=True)
    result = _run("--repo-dir", str(tmp_path), "--schema-name", "FHS")
    assert result.returncode == 0
    assert result.stdout.strip() == str(target)


def test_cli_explicit_path_option(tmp_path):
    """--explicit-path overrides auto-detection."""
    target = tmp_path / "custom" / "location"
    target.mkdir(parents=True)
    result = _run(
        "--repo-dir",
        str(tmp_path),
        "--schema-name",
        "FHS",
        "--explicit-path",
        "custom/location",
    )
    assert result.returncode == 0
    assert result.stdout.strip() == str(target)


def test_cli_error_goes_to_stderr(tmp_path):
    """Failure exits non-zero with an ERROR message on stderr."""
    result = _run("--repo-dir", str(tmp_path), "--schema-name", "FHS")
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert result.stdout == ""  # nothing on stdout when we fail
