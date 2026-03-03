"""
Integration tests for the pre_cleaned pipeline path.

Runs the full pipeline (schema -> validate -> map) against human-readable
TSVs in toy_data/data/pre_cleaned/, exercising the pipeline without a prepare step.
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
toy_data_input_dir = root_dir / "toy_data/data/pre_cleaned"

SCHEMA_NAME = "ToyPreCleaned"
CONFIG_FILE = "toy_data/pre_cleaned/config.mk"
EXPECTED_ENTITIES = {"Person", "Participant"}


@pytest.fixture(scope="module")
def pre_cleaned_pipeline_output():
    """Run the pre_cleaned pipeline against toy data, returning the output directory."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="pre-cleaned-pipeline_")
    toy_output_dir = Path(temp_dir.name)
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
        raise RuntimeError(f"pre_cleaned pipeline failed (exit {proc.returncode}):\n{proc.stderr[-1000:]}")

    yield toy_output_dir

    temp_dir.cleanup()


def test_pipeline_no_input():
    """Ensure a non-zero exit code when no input files are given."""
    result = subprocess.run(
        ["make", "schema-create"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )

    assert result.returncode > 0
    assert "No input files detected" in result.stderr


def test_schema_creation(pre_cleaned_pipeline_output: Path):
    """Ensure that the pipeline creates a LinkML schema as expected."""
    schema_path = pre_cleaned_pipeline_output / f"{SCHEMA_NAME}.yaml"
    validation_path = pre_cleaned_pipeline_output / "validation-logs"

    assert schema_path.exists()
    schema_view = SchemaView(schema_path)

    input_files = [f for f in toy_data_input_dir.iterdir() if f.name.endswith(("csv", "tsv"))]
    assert schema_view.schema.name == SCHEMA_NAME
    assert len(schema_view.all_classes()) == len(input_files)

    assert (validation_path / f"{SCHEMA_NAME}-data-validate.log").exists()
    validated_files = list((validation_path / "data-validation").iterdir())
    assert set(d.name for d in validated_files) == set(a.name for a in input_files)
    for file_log_dir in validated_files:
        success_symlink = file_log_dir / "success.log"
        error_symlink = file_log_dir / "latest-error.log"
        has_success = success_symlink.is_symlink() and success_symlink.exists()
        has_error = error_symlink.is_symlink() and error_symlink.exists()
        assert has_success or has_error


def test_mapping_outputs(pre_cleaned_pipeline_output: Path):
    """Mapped data files should exist for each discovered entity."""
    mapped_dir = pre_cleaned_pipeline_output / "mapped-data"

    assert mapped_dir.exists(), "mapped-data directory not created"

    for entity in EXPECTED_ENTITIES:
        matches = list(mapped_dir.glob(f"*{entity}*"))
        assert matches, f"No mapped output file found for entity {entity}"
