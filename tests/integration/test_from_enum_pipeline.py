"""
Integration tests for the enum derivations pipeline path.

Runs the full pipeline (prepare -> schema -> validate -> map) against synthetic
dbGaP .txt.gz files in toy_data_w_enums/data/raw/, using committed enum_derivations
specs at toy_data_w_enums/specs/with_enum_derivations/.
"""

# ruff: noqa: S603 S607

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

SCHEMA_NAME = "ToyEnums"
CONFIG_FILE = "toy_data_w_enums/config-enums.mk"
EXPECTED_PREPARED_FILES = {"pht000001.tsv", "pht000002.tsv", "pht000003.tsv", "pht000005.tsv"}
EXPECTED_ENTITIES = {"Condition", "Demography", "MeasurementObservation", "Observation", "Participant"}


@pytest.fixture(scope="module")
def enum_pipeline_output():
    """Run the full enum pipeline against toy data, returning the output directory."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="enum-pipeline_")
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
        raise RuntimeError(f"enum pipeline failed (exit {proc.returncode}):\n{proc.stderr[-1000:]}")

    yield {"output_dir": toy_output_dir, "prepared_dir": prepared_dir}

    temp_dir.cleanup()


def test_prepare_creates_expected_files(enum_pipeline_output):
    """Only pht000001, pht000002, pht000003, pht000005 should be prepared."""
    prepared = enum_pipeline_output["prepared_dir"]
    actual_files = {f.name for f in prepared.iterdir() if f.suffix == ".tsv"}
    assert actual_files == EXPECTED_PREPARED_FILES


def test_schema_creation(enum_pipeline_output):
    """Auto-generated schema should have one class per prepared input file."""
    output = enum_pipeline_output["output_dir"]
    schema_path = output / f"{SCHEMA_NAME}.yaml"

    assert schema_path.exists(), f"Schema file not found: {schema_path}"
    schema_view = SchemaView(schema_path)
    assert schema_view.schema.name == SCHEMA_NAME
    assert len(schema_view.all_classes()) == len(EXPECTED_PREPARED_FILES)


def test_schema_has_enums(enum_pipeline_output):
    """Source schema should contain enum definitions from enum inference."""
    output = enum_pipeline_output["output_dir"]
    schema_path = output / f"{SCHEMA_NAME}.yaml"
    schema_view = SchemaView(schema_path)

    enums = schema_view.all_enums()
    assert len(enums) > 0, "No enums found in source schema"
    assert "phv00000002_enum" in enums, "Expected phv00000002_enum (sex) in source schema enums"


def test_validation(enum_pipeline_output):
    """Validation logs should exist for each prepared file."""
    output = enum_pipeline_output["output_dir"]
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


def test_mapping_outputs(enum_pipeline_output):
    """Mapped data files should exist for each discovered entity."""
    output = enum_pipeline_output["output_dir"]
    mapped_dir = output / "mapped-data"

    assert mapped_dir.exists(), "mapped-data directory not created"

    for entity in EXPECTED_ENTITIES:
        matches = list(mapped_dir.glob(f"*{entity}*"))
        assert matches, f"No mapped output file found for entity {entity}"


def test_mapping_uses_enum_derivations(enum_pipeline_output):
    """Mapped output for Demography should contain enum-derived values (e.g., sex_enum values)."""
    output = enum_pipeline_output["output_dir"]
    mapped_dir = output / "mapped-data"
    demography_files = list(mapped_dir.glob("*Demography*"))
    assert demography_files, "No mapped Demography output"

    with open(demography_files[0]) as f:
        content = yaml.safe_load(f)

    assert content, "Demography mapped output is empty"
    records = content if isinstance(content, list) else [content]
    sex_values = {r.get("sex") for r in records if r.get("sex")}
    assert sex_values, "No sex values found in mapped Demography output"
    # These are the target enum permissible values from sex_enum
    assert sex_values <= {"OMOP:8507", "OMOP:8532"}, f"Unexpected sex values: {sex_values}"
