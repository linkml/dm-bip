"""Unit tests for scripts/workflow/resolve_source.py."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "workflow" / "resolve_source.py"


def _load_module():
    """Import the script as a module so we can test its functions directly."""
    spec = importlib.util.spec_from_file_location("resolve_source", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolve_source = _load_module().resolve_source


# --- Local directory --------------------------------------------------------


def test_local_dir_returned_unchanged(tmp_path):
    """An existing local directory is returned exactly as given (no behavior change)."""
    assert resolve_source(str(tmp_path)) == str(tmp_path)


def test_missing_local_dir_raises(tmp_path):
    """A local path that does not exist raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="does not exist"):
        resolve_source(str(tmp_path / "nope"))


def test_local_file_is_not_a_dir(tmp_path):
    """A path to a file (not a directory) raises FileNotFoundError."""
    f = tmp_path / "data.txt"
    f.write_text("x")
    with pytest.raises(FileNotFoundError):
        resolve_source(str(f))


def test_empty_source_raises():
    """Empty source is rejected."""
    with pytest.raises(ValueError, match="must not be empty"):
        resolve_source("")


# --- Not-yet-implemented schemes --------------------------------------------


def test_s3_scheme_not_implemented():
    """s3:// is recognized but deferred to Stage 1, with a volume hint."""
    with pytest.raises(NotImplementedError, match="Stage 1"):
        resolve_source("s3://bucket/prefix")


def test_drs_scheme_not_implemented():
    """drs:// is recognized but deferred to Stage 3."""
    with pytest.raises(NotImplementedError, match="Stage 3"):
        resolve_source("drs://abc123")


# --- CLI / shell-contract tests ---------------------------------------------


def _run(*args) -> subprocess.CompletedProcess:
    """Invoke the script and return the completed process."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_prints_local_dir(tmp_path):
    """A valid local dir is echoed on stdout with a zero exit."""
    result = _run("--source", str(tmp_path))
    assert result.returncode == 0
    assert result.stdout.strip() == str(tmp_path)


def test_cli_error_goes_to_stderr(tmp_path):
    """A missing source exits non-zero with ERROR on stderr and nothing on stdout."""
    result = _run("--source", str(tmp_path / "missing"))
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert result.stdout == ""


def test_cli_s3_not_implemented():
    """s3:// exits non-zero with a helpful Stage-1 message on stderr."""
    result = _run("--source", "s3://bucket/prefix")
    assert result.returncode != 0
    assert "Stage 1" in result.stderr
