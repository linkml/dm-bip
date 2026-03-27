"""
Integration tests for the from_raw pipeline path.

Runs the full pipeline (prepare -> schema -> validate -> map) against synthetic
dbGaP .txt.gz files in toy_data/data/raw/, exercising the prepare step
that strips comments, cleans phv headers, and filters unused tables.
"""

# ruff: noqa: S603 S607

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml
from linkml_runtime import SchemaView

script_dir = Path(__file__).parent
output_dir = script_dir.parent / "output"
root_dir = script_dir.parent.parent

SCHEMA_NAME = "ToyFromRaw"
CONFIG_FILE = "toy_data/from_raw/config.mk"
ERROR_SPEC_DIR = root_dir / "toy_data" / "from_raw" / "error-spec"
EXPECTED_PREPARED_FILES = {"pht000001.tsv", "pht000002.tsv", "pht000003.tsv", "pht000005.tsv"}
EXPECTED_ENTITIES = {
    "Condition",
    "Demography",
    "MeasurementObservation",
    "MeasurementObservationSet",
    "Observation",
    "Participant",
}


@pytest.fixture(scope="module")
def from_raw_pipeline_output():
    """Run the full from_raw pipeline against toy data, returning the output directory."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="from-raw-pipeline_")
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
        raise RuntimeError(f"from_raw pipeline failed (exit {proc.returncode}):\n{proc.stderr[-1000:]}")

    yield {"output_dir": toy_output_dir, "prepared_dir": prepared_dir}

    temp_dir.cleanup()


def test_prepare_filters_unused_tables(from_raw_pipeline_output):
    """pht000099 should NOT be prepared since no trans-spec references it."""
    prepared = from_raw_pipeline_output["prepared_dir"]
    assert not (prepared / "pht000099.tsv").exists(), "pht000099.tsv should have been filtered out"


def test_prepare_creates_expected_files(from_raw_pipeline_output):
    """Only pht000001, pht000002, pht000003, pht000005 should be prepared."""
    prepared = from_raw_pipeline_output["prepared_dir"]
    actual_files = {f.name for f in prepared.iterdir() if f.suffix == ".tsv"}
    assert actual_files == EXPECTED_PREPARED_FILES


def test_prepare_cleans_headers(from_raw_pipeline_output):
    """Prepared TSVs should have clean phv column names (no version suffixes)."""
    prepared = from_raw_pipeline_output["prepared_dir"]
    for tsv_file in prepared.glob("*.tsv"):
        with open(tsv_file) as f:
            header = f.readline().strip().split("\t")
        for col in header:
            assert ".v1" not in col, f"Version suffix found in {tsv_file.name}: {col}"
            if col.startswith("phv"):
                assert col == col.split(".")[0], f"Unclean phv header in {tsv_file.name}: {col}"


def test_schema_creation(from_raw_pipeline_output):
    """Auto-generated schema should have one class per prepared input file."""
    output = from_raw_pipeline_output["output_dir"]
    schema_path = output / f"{SCHEMA_NAME}.yaml"

    assert schema_path.exists(), f"Schema file not found: {schema_path}"
    schema_view = SchemaView(schema_path)
    assert schema_view.schema.name == SCHEMA_NAME
    assert len(schema_view.all_classes()) == len(EXPECTED_PREPARED_FILES)


def test_validation(from_raw_pipeline_output):
    """Validation logs should exist for each prepared file."""
    output = from_raw_pipeline_output["output_dir"]
    validation_path = output / "validation-logs"

    validated_dirs = list((validation_path / "data-validation").iterdir())
    assert len(validated_dirs) == len(EXPECTED_PREPARED_FILES)

    for file_log_dir in validated_dirs:
        success = file_log_dir / "success.log"
        error = file_log_dir / "latest-error.log"
        has_success = success.is_symlink() and success.exists()
        has_error = error.is_symlink() and error.exists()
        assert has_success or has_error, f"No validation result for {file_log_dir.name}"


def test_mapping_outputs(from_raw_pipeline_output):
    """Mapped data files should exist for each discovered entity."""
    output = from_raw_pipeline_output["output_dir"]
    mapped_dir = output / "mapped-data"

    assert mapped_dir.exists(), "mapped-data directory not created"

    for entity in EXPECTED_ENTITIES:
        matches = list(mapped_dir.glob(f"*{entity}*.yaml"))
        assert matches, f"No mapped output file found for entity {entity}"


def test_mapping_demography_values(from_raw_pipeline_output):
    """Demography output should contain sex code value mappings."""
    mapped_dir = from_raw_pipeline_output["output_dir"] / "mapped-data"
    demography_files = list(mapped_dir.glob("*Demography*.yaml"))
    assert demography_files, "No Demography output file"

    records = [r for r in yaml.safe_load_all(demography_files[0].read_text()) if r]
    assert len(records) > 0, "Demography output is empty"

    sex_values = {r.get("sex") for r in records if r.get("sex")}
    assert sex_values & {"OMOP:8507", "OMOP:8532"}, f"Expected OMOP sex codes, got {sex_values}"


def test_mapping_cross_table_age(from_raw_pipeline_output):
    """MeasurementObservation should have age_at_observation from cross-table join."""
    mapped_dir = from_raw_pipeline_output["output_dir"] / "mapped-data"
    mo_files = list(mapped_dir.glob("*MeasurementObservation--*.yaml"))
    assert mo_files, "No MeasurementObservation output file"

    records = [r for r in yaml.safe_load_all(mo_files[0].read_text()) if r]

    # Body height records (OBA:VT0001253) should have age_at_observation from cross-table join
    height_records = [r for r in records if r.get("observation_type") == "OBA:VT0001253"]
    assert height_records, "No body height records found"

    ages = [r.get("age_at_observation") for r in height_records if r.get("age_at_observation")]
    assert ages, "No age_at_observation values in height records"
    # First participant: age 40 * 365 = 14600
    assert 14600 in ages, f"Expected 14600 (40*365) in ages, got {ages[:5]}"


# --- Error handling tests ---
# These reuse the prepared data and schema from the main pipeline run,
# then run only the map step with a deliberately broken spec.


@pytest.fixture(scope="module")
def error_spec_composed(from_raw_pipeline_output):
    """Compose specs that include a deliberately broken expression alongside good ones."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="error-spec_")
    spec_dir = Path(temp_dir.name) / "specs"
    composed_dir = Path(temp_dir.name) / "composed"
    spec_dir.mkdir()

    # Symlink good specs and bad specs into one directory
    for src in (root_dir / "toy_data" / "from_raw" / "specs").glob("*.yaml"):
        (spec_dir / src.name).symlink_to(src.resolve())
    for src in ERROR_SPEC_DIR.glob("*.yaml"):
        (spec_dir / src.name).symlink_to(src.resolve())

    # Compose into per-entity specs
    subprocess.run(
        ["uv", "run", "python", "-m", "dm_bip.map_data.compose_specs", str(spec_dir), str(composed_dir)],
        cwd=str(root_dir),
        check=True,
        capture_output=True,
    )

    yield {
        "composed_dir": composed_dir,
        "schema_file": from_raw_pipeline_output["output_dir"] / f"{SCHEMA_NAME}.yaml",
        "prepared_dir": from_raw_pipeline_output["prepared_dir"],
        "output_dir": Path(temp_dir.name),
    }

    temp_dir.cleanup()


def _run_linkml_map(error_spec_composed, *, entity, continue_on_error):
    """Run linkml-map map-data for a single entity's composed spec."""
    out_file = error_spec_composed["output_dir"] / f"{entity}.yaml"
    cmd = [
        "uv", "run", "linkml-map", "map-data",
        "-T", str(error_spec_composed["composed_dir"] / f"{entity}.yaml"),
        "-s", str(error_spec_composed["schema_file"]),
        "--target-schema", str(root_dir / "toy_data" / "target-schema.yaml"),
        "-o", str(out_file),
        "-f", "yaml",
        str(error_spec_composed["prepared_dir"]) + "/",
    ]
    if continue_on_error:
        cmd.insert(-1, "--continue-on-error")
    return subprocess.run(cmd, cwd=str(root_dir), capture_output=True, text=True)


def test_mapping_strict_mode_fails_on_bad_spec(error_spec_composed):
    """In strict mode, a bad expression should crash immediately."""
    proc = _run_linkml_map(error_spec_composed, entity="Demography", continue_on_error=False)
    assert proc.returncode != 0, "Should fail on bad expression in strict mode"
    assert "division by zero" in proc.stderr, "Error should mention the expression failure"


def test_continue_on_error_reports_all_errors(error_spec_composed):
    """With --continue-on-error, all errors are reported for bulk fixing."""
    # Run Demography (has division by zero errors)
    demography = _run_linkml_map(error_spec_composed, entity="Demography", continue_on_error=True)
    assert demography.returncode == 1, "Should exit 1 when errors occurred"
    assert "transformation error(s)" in demography.stderr, "Should report error count"
    assert "division by zero" in demography.stderr, "Should identify the expression failure"

    # Run Participant (has unsafe expression errors)
    participant = _run_linkml_map(error_spec_composed, entity="Participant", continue_on_error=True)
    assert participant.returncode == 1, "Should exit 1 when errors occurred"
    assert "transformation error(s)" in participant.stderr, "Should report error count"
    assert "not in safe subset" in participant.stderr, "Should identify the unsafe expression"


def test_continue_on_error_reports_multiple_rows(error_spec_composed):
    """Error report should include row numbers so all failures can be located."""
    proc = _run_linkml_map(error_spec_composed, entity="Demography", continue_on_error=True)
    # Should report errors for multiple rows, not just the first
    assert "row=0" in proc.stderr, "Should report first failing row"
    assert "row=1" in proc.stderr, "Should report subsequent failing rows"
