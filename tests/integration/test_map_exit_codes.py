"""
Integration tests for the per-entity map-data exit-code guard in pipeline.Makefile.

These drive the *real* map sentinel recipe with `RUN` overridden by a stub that
exits a chosen code, so `$(RUN) linkml-map map-data ...` becomes
`<stub> linkml-map map-data ...` and exits STUB_RC. That exercises the whole
recipe end to end — including the `set -o pipefail` that lets `$?` see the
child's code through the `| tee`, and the real scripts/map_exit_guard.sh call —
rather than the guard script in isolation.

The regression these lock down: a signal kill (exit >= 128, e.g. 137 = SIGKILL
from an OOM) was being swallowed by --continue-on-error and reported as success,
leaving silently truncated / empty output behind a "✓ success" banner.
"""

# ruff: noqa: S603 S607

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

root_dir = Path(__file__).parent.parent.parent
ENTITY = "Fixture"


def _run_recipe(tmp: Path, stub_rc: int, strict: str) -> subprocess.CompletedProcess:
    """
    Drive the per-entity map sentinel target with a stubbed child exit code.

    Args:
        tmp: Scratch directory for prereqs, stub, and outputs.
        stub_rc: Exit code the stubbed map-data child returns.
        strict: Value for DM_MAP_STRICT ("true" or "false").

    Returns:
        The completed `make` process.

    """
    mapped = tmp / "mapped"
    trans_specs = tmp / "trans-specs"
    logs = mapped / "logs"
    inp = tmp / "input"
    schema = tmp / "schema.yaml"
    target = tmp / "target.yaml"
    spec = trans_specs / f"{ENTITY}.yaml"
    for d in (trans_specs, logs, inp):
        d.mkdir(parents=True, exist_ok=True)
    # Prereqs — dummy files; the stub ignores their contents.
    for f in (spec, schema, target):
        f.write_text("# stub\n")

    stub = tmp / "stub_run.sh"
    stub.write_text("#!/usr/bin/env bash\nexit ${STUB_RC:-0}\n")
    stub.chmod(0o755)

    env = os.environ.copy()
    env["STUB_RC"] = str(stub_rc)

    return subprocess.run(
        [
            "make",
            "-f",
            "pipeline.Makefile",
            str(mapped / f".{ENTITY}_complete"),
            f"RUN=bash {stub}",
            f"MAPPING_OUTPUT_DIR={mapped}",
            f"DM_TRANS_SPEC_DIR={trans_specs}",
            f"MAP_TRANS_SPEC_FILES={spec}",
            f"MAPPING_LOG_DIR={logs}",
            f"SCHEMA_FILE={schema}",
            f"MAP_TARGET_SCHEMA_FILE={target}",
            f"DM_INPUT_DIR={inp}",
            f"DM_MAP_STRICT={strict}",
            "DM_MAP_OUTPUT_TYPE=tsv",
            "DM_MAP_CHUNK_SIZE=10000",
            # Treat the prereqs as up-to-date so make never tries to rebuild them,
            # isolating the recipe under test.
            "-o",
            str(spec),
            "-o",
            str(schema),
            "-o",
            str(target),
        ],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.mark.parametrize("rc", [137, 143, 139])
def test_signal_kill_always_fails_even_non_strict(rc: int):
    """A child killed by a signal (>=128) must fail the recipe even in non-strict mode."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = _run_recipe(tmp, stub_rc=rc, strict="false")
        assert result.returncode != 0, (
            f"exit {rc} (signal kill) must fail the recipe, got success:\n{result.stdout}\n{result.stderr}"
        )
        assert not (tmp / "mapped" / f".{ENTITY}_complete").exists(), f"exit {rc} must not create the success sentinel"


def test_row_error_tolerated_in_non_strict():
    """linkml-map's own row-error exit (1) is tolerated in non-strict mode."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = _run_recipe(tmp, stub_rc=1, strict="false")
        assert result.returncode == 0, f"exit 1 must be tolerated in non-strict mode:\n{result.stdout}\n{result.stderr}"
        assert (tmp / "mapped" / f".{ENTITY}_complete").exists()


def test_row_error_fails_in_strict():
    """A non-zero exit fails the recipe in strict mode."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = _run_recipe(tmp, stub_rc=1, strict="true")
        assert result.returncode != 0


def test_success_creates_sentinel():
    """Exit 0 completes the recipe and creates the sentinel."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = _run_recipe(tmp, stub_rc=0, strict="false")
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
        assert (tmp / "mapped" / f".{ENTITY}_complete").exists()
