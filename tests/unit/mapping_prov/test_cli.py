"""Tests for the extract-mapping-provenance CLI command."""

import shutil
from pathlib import Path

import yaml
from typer.testing import CliRunner

from dm_bip.cli import app

INPUT_DIR = Path(__file__).parents[2] / "input" / "mapping_prov"

runner = CliRunner()


def test_cli_extracts_directory_to_stdout():
    """A spec directory is extracted to a YAML list of study documents on stdout."""
    result = runner.invoke(app, ["extract-mapping-provenance", str(INPUT_DIR / "ARIC-ingest")])
    assert result.exit_code == 0, result.output

    [study] = yaml.safe_load(result.output)
    assert study["id"] == "bdchm:Study/phs000280"
    assert any(d["id"] == "dbgap:pht004063" for d in study["datasets"])


def test_cli_writes_output_file(tmp_path):
    """The -o option writes the YAML to a file, covering multiple study directories."""
    # copy the fixtures outside any git checkout so spec ids deterministically use path form
    specs = tmp_path / "specs"
    shutil.copytree(INPUT_DIR, specs)
    out = tmp_path / "mapping-prov.yaml"
    result = runner.invoke(app, ["extract-mapping-provenance", str(specs), "-o", str(out)])
    assert result.exit_code == 0, result.output

    studies = yaml.safe_load(out.read_text())
    assert [s["id"] for s in studies] == ["bdchm:Study/phs000280", "dmcprov:MESA-ingest"]
    aric = studies[0]
    # spec ids are relative to the common base directory, so they keep the study-dir prefix
    assert any(s["id"] == "dmcprov:ARIC-ingest/bmi.yaml" for s in aric["transformation_specs"])


def test_cli_errors_when_no_specs_found(tmp_path):
    """An input directory containing no spec files is an error."""
    result = runner.invoke(app, ["extract-mapping-provenance", str(tmp_path)])
    assert result.exit_code == 1
