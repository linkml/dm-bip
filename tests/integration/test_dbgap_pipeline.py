"""
Integration tests for the dbGaP-style pipeline path.

Runs the full pipeline (prepare -> schema -> validate -> map) against synthetic
dbGaP .txt.gz files in toy_data/dbgap/raw/, exercising the prepare step
that strips comments, cleans phv headers, and filters unused tables.
"""

# ruff: noqa: S603 S607

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from linkml_runtime import SchemaView

script_dir = Path(__file__).parent
output_dir = script_dir.parent / "output"
root_dir = script_dir.parent.parent

SCHEMA_NAME = "ToyDbgap"
CONFIG_FILE = "toy_data/dbgap/config.mk"
EXPECTED_PREPARED_FILES = {"pht000001.tsv", "pht000002.tsv", "pht000003.tsv"}
EXPECTED_ENTITIES = {"Demography", "MeasurementObservation", "Participant"}


@pytest.fixture(scope="module")
def dbgap_pipeline_output():
    """Run the full dbGaP pipeline against toy data, returning the output directory."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="dbgap-pipeline_")
    toy_output_dir = Path(temp_dir.name)
    prepared_dir = toy_output_dir / "prepared"
    env = os.environ.copy()

    env["TOY_OUTPUT_DIR"] = str(toy_output_dir)

    proc = subprocess.run(
        ["make", "pipeline", f"CONFIG={CONFIG_FILE}"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
        env=env,
    )

    if proc.returncode != 0:
        print("STDOUT:", proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout)
        print("STDERR:", proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr)
        temp_dir.cleanup()
        raise RuntimeError(f"dbGaP pipeline failed (exit {proc.returncode}):\n{proc.stderr[-1000:]}")

    yield {"output_dir": toy_output_dir, "prepared_dir": prepared_dir}

    temp_dir.cleanup()


def test_prepare_filters_unused_tables(dbgap_pipeline_output):
    """pht000099 should NOT be prepared since no trans-spec references it."""
    prepared = dbgap_pipeline_output["prepared_dir"]
    assert not (prepared / "pht000099.tsv").exists(), "pht000099.tsv should have been filtered out"


def test_prepare_creates_expected_files(dbgap_pipeline_output):
    """Only pht000001, pht000002, pht000003 should be prepared."""
    prepared = dbgap_pipeline_output["prepared_dir"]
    actual_files = {f.name for f in prepared.iterdir() if f.suffix == ".tsv"}
    assert actual_files == EXPECTED_PREPARED_FILES


def test_prepare_cleans_headers(dbgap_pipeline_output):
    """Prepared TSVs should have clean phv column names (no version suffixes)."""
    prepared = dbgap_pipeline_output["prepared_dir"]
    for tsv_file in prepared.glob("*.tsv"):
        with open(tsv_file) as f:
            header = f.readline().strip().split("\t")
        for col in header:
            assert ".v1" not in col, f"Version suffix found in {tsv_file.name}: {col}"
            if col.startswith("phv"):
                assert col == col.split(".")[0], f"Unclean phv header in {tsv_file.name}: {col}"


def test_schema_creation(dbgap_pipeline_output):
    """Auto-generated schema should have one class per prepared input file."""
    output = dbgap_pipeline_output["output_dir"]
    schema_path = output / f"{SCHEMA_NAME}.yaml"

    assert schema_path.exists(), f"Schema file not found: {schema_path}"
    schema_view = SchemaView(schema_path)
    assert schema_view.schema.name == SCHEMA_NAME
    assert len(schema_view.all_classes()) == len(EXPECTED_PREPARED_FILES)


def test_validation(dbgap_pipeline_output):
    """Validation logs should exist for each prepared file."""
    output = dbgap_pipeline_output["output_dir"]
    validation_path = output / "validation-logs"

    assert (validation_path / f"{SCHEMA_NAME}-data-validate.log").exists()

    validated_dirs = list((validation_path / "data-validation").iterdir())
    assert len(validated_dirs) == len(EXPECTED_PREPARED_FILES)

    for file_log_dir in validated_dirs:
        success = file_log_dir / "success.log"
        error = file_log_dir / "latest-error.log"
        has_success = success.is_symlink() and success.exists()
        has_error = error.is_symlink() and error.exists()
        assert has_success or has_error, f"No validation result for {file_log_dir.name}"


def test_mapping_outputs(dbgap_pipeline_output):
    """Mapped data files should exist for each discovered entity."""
    output = dbgap_pipeline_output["output_dir"]
    mapped_dir = output / "mapped-data"

    assert mapped_dir.exists(), "mapped-data directory not created"

    for entity in EXPECTED_ENTITIES:
        matches = list(mapped_dir.glob(f"*{entity}*"))
        assert matches, f"No mapped output file found for entity {entity}"
