"""
Integration tests for the pre_cleaned pipeline path.

Runs the full pipeline (schema -> validate -> map) against human-readable
TSVs in toy_data/data/pre_cleaned/, exercising the pipeline without a prepare step.
This config uses multi-format output (yaml + tsv) to validate both formats.
"""

# ruff: noqa: S603 S607

import csv
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml
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

    validated_files = list((validation_path / "data-validation").iterdir())
    assert set(d.name for d in validated_files) == set(a.name for a in input_files)
    for file_log_dir in validated_files:
        success_symlink = file_log_dir / "success.log"
        error_symlink = file_log_dir / "latest-error.log"
        has_success = success_symlink.is_symlink() and success_symlink.exists()
        has_error = error_symlink.is_symlink() and error_symlink.exists()
        assert has_success or has_error


def test_mapping_outputs(pre_cleaned_pipeline_output: Path):
    """Mapped data files should exist in both yaml and tsv for each entity."""
    mapped_dir = pre_cleaned_pipeline_output / "mapped-data"

    assert mapped_dir.exists(), "mapped-data directory not created"

    for entity in EXPECTED_ENTITIES:
        yaml_files = list(mapped_dir.glob(f"*{entity}--*.yaml"))
        tsv_files = list(mapped_dir.glob(f"*{entity}--*.tsv"))
        assert yaml_files, f"No YAML output for {entity}"
        assert tsv_files, f"No TSV output for {entity}"


def test_mapping_person_values(pre_cleaned_pipeline_output: Path):
    """Person output should contain demographic values from the input data."""
    mapped_dir = pre_cleaned_pipeline_output / "mapped-data"
    person_yaml = list(mapped_dir.glob("*Person--*.yaml"))
    assert person_yaml, "No Person YAML output"

    records = [r for r in yaml.safe_load_all(person_yaml[0].read_text()) if r]
    assert len(records) > 0, f"Expected Person records, got {len(records)}"

    genders = {r.get("gender") for r in records}
    assert "Male" in genders and "Female" in genders, f"Expected Male and Female, got {genders}"


def test_tsv_output_matches_yaml(pre_cleaned_pipeline_output: Path):
    """TSV and YAML outputs should contain the same records."""
    mapped_dir = pre_cleaned_pipeline_output / "mapped-data"
    person_yaml = list(mapped_dir.glob("*Person--*.yaml"))
    person_tsv = list(mapped_dir.glob("*Person--*.tsv"))

    yaml_records = [r for r in yaml.safe_load_all(person_yaml[0].read_text()) if r]

    with open(person_tsv[0]) as f:
        tsv_records = list(csv.DictReader(f, delimiter="\t"))

    assert len(tsv_records) == len(yaml_records), (
        f"TSV has {len(tsv_records)} rows but YAML has {len(yaml_records)} records"
    )

    # Spot-check: first record's id should match
    yaml_ids = sorted(str(r["id"]) for r in yaml_records)
    tsv_ids = sorted(r["id"] for r in tsv_records)
    assert yaml_ids == tsv_ids, "Record IDs should match between YAML and TSV"
