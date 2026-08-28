"""
Integration tests for the output-directory ownership guard in pipeline.Makefile.

An output directory belongs to exactly one DM_SCHEMA_NAME. The guard compares the
incoming DM_SCHEMA_NAME against the one recorded in the directory's
provenance.yaml and aborts at parse time on a mismatch.

These drive real `make` invocations against fixture directories rather than
testing a helper in isolation, because the behaviour under test is make's own
parse-phase ordering: the guard has to fire *before* make remakes the -include'd
$(PREPARED_INPUT_MK), whose recipe writes into the contested directory.

The guard degrades open — a missing, unparseable, or key-less provenance.yaml lets
the run proceed. That makes a silently-broken guard indistinguishable from a
passing one, so the important assertions here are the ones that check it *fires*.
"""

# ruff: noqa: S603 S607

import subprocess
from pathlib import Path

import pytest

root_dir = Path(__file__).parent.parent.parent


def _write_provenance(out_dir: Path, body: str) -> None:
    """
    Write a provenance.yaml fixture into an output directory.

    Args:
        out_dir: Directory to write into; created if absent.
        body: Full provenance.yaml contents.

    """
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "provenance.yaml").write_text(body)


def _make(out_dir: Path, schema_name: str, *goals: str, **overrides: str) -> subprocess.CompletedProcess:
    """
    Run make against an output directory with a given schema name.

    Args:
        out_dir: Value for DM_OUTPUT_DIR.
        schema_name: Value for DM_SCHEMA_NAME.
        *goals: Make goals; defaults to `provenance`.
        **overrides: Extra VAR=value assignments.

    Returns:
        The completed `make` process.

    """
    cmd = ["make", *(goals or ("provenance",)), f"DM_OUTPUT_DIR={out_dir}", f"DM_SCHEMA_NAME={schema_name}"]
    cmd += [f"{k}={v}" for k, v in overrides.items()]
    return subprocess.run(cmd, cwd=str(root_dir), capture_output=True, text=True)


OWNED_BY_STUDY_ONE = "dm_bip:\n  version: 1.0\npipeline:\n  schema_name: StudyOne\n  input_dir: /somewhere\n"


def test_guard_fires_on_mismatched_schema_name(tmp_path: Path) -> None:
    """A directory owned by another study aborts the run and names both studies."""
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    result = _make(tmp_path, "StudyTwo")
    assert result.returncode != 0
    assert "StudyOne" in result.stderr
    assert "StudyTwo" in result.stderr


def test_guard_fires_before_any_output_is_written(tmp_path: Path) -> None:
    """
    The abort happens at parse time, before the prepared-input include is remade.

    This is the property that makes the guard worth having: a recipe-level check
    would run only after prepare_input.py had already written into the directory.
    """
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    before = sorted(p.name for p in tmp_path.iterdir())
    result = _make(tmp_path, "StudyTwo", DM_RAW_SOURCE=str(tmp_path / "raw"), DM_INPUT_DIR=str(tmp_path / "prepared"))
    assert result.returncode != 0
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_same_schema_name_is_silent(tmp_path: Path) -> None:
    """Re-running the same study into its own directory is the normal case."""
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    result = _make(tmp_path, "StudyOne")
    assert result.returncode == 0
    assert "holds products for" not in result.stderr


def test_allow_output_reuse_overrides_the_guard(tmp_path: Path) -> None:
    """The documented escape hatch lets a deliberate overwrite through."""
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    result = _make(tmp_path, "StudyTwo", DM_ALLOW_OUTPUT_REUSE="1")
    assert result.returncode == 0


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("dm_bip:\n  version: 1.0\n", id="no-pipeline-block"),
        pytest.param("pipeline:\n  input_dir: /somewhere\n", id="no-schema-name-key"),
        pytest.param("", id="empty-file"),
        pytest.param("\x00\x01 not yaml at all\n", id="unparseable"),
        pytest.param("dm_bip:\n  schema_name: NotTheOwner\n", id="schema-name-outside-pipeline-block"),
    ],
)
def test_guard_degrades_open(tmp_path: Path, body: str) -> None:
    """
    Absent or unreadable ownership evidence lets the run proceed.

    The guard may fail to catch a mismatch; it must never invent one. The last
    case matters most: schema_name under a different top-level block is not
    ownership evidence and must not be read as such.
    """
    _write_provenance(tmp_path, body)
    result = _make(tmp_path, "StudyTwo")
    assert result.returncode == 0
    assert "holds products for" not in result.stderr


@pytest.mark.parametrize("goal", ["output-clean", "map-clean", "pipeline-debug", "help"])
def test_cleanup_and_debug_goals_stay_reachable(tmp_path: Path, goal: str) -> None:
    """
    The guard must not block the goals used to inspect or reset the directory.

    output-clean especially: it is the supported way out of a mismatch, so a guard
    that blocked it would leave no path forward but editing files by hand.
    """
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    result = _make(tmp_path, "StudyTwo", goal)
    assert result.returncode == 0


def test_output_clean_removes_the_previous_owners_schema(tmp_path: Path) -> None:
    """
    Resetting a directory clears the prior study's products, not just the current name's.

    The schema file is named for DM_SCHEMA_NAME, so cleaning a directory owned by
    another study has to consult provenance.yaml for the name to remove.
    """
    _write_provenance(tmp_path, OWNED_BY_STUDY_ONE)
    (tmp_path / "StudyOne.yaml").write_text("# prior owner's inferred schema\n")
    (tmp_path / "mapping-provenance.yaml").write_text("# prior owner\n")
    (tmp_path / "mapped-data").mkdir()
    (tmp_path / "mapped-data" / "StudyOne-Demography.yaml").write_text("# prior owner's output\n")

    result = _make(tmp_path, "StudyTwo", "output-clean")
    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []
