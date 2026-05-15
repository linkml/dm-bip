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


def test_mapping_unit_conversion(from_raw_pipeline_output):
    """Body height should be converted from inches to cm via unit_conversion."""
    output = from_raw_pipeline_output["output_dir"]
    mapped_dir = output / "mapped-data"
    mo_files = list(mapped_dir.glob("*MeasurementObservation--*.yaml"))
    records = [r for r in yaml.safe_load_all(mo_files[0].read_text()) if r]

    height_records = [r for r in records if r.get("observation_type") == "OBA:VT0001253"]
    values = [r["value_quantity"]["value_decimal"] for r in height_records if r.get("value_quantity")]
    assert values, "No converted height values found"

    # Input: 59.5 inches → 151.13 cm (59.5 * 2.54)
    assert any(abs(v - 151.13) < 0.01 for v in values), f"Expected ~151.13 cm in values, got {values[:5]}"

    # All values should be in cm range (not raw inches)
    assert all(v > 100 for v in values), f"Values look unconverted (still in inches?): {values[:5]}"

    weight_records = [r for r in records if r.get("observation_type") == "OBA:VT0001254"]
    weights = [r["value_quantity"]["value_decimal"] for r in weight_records if r.get("value_quantity")]
    assert weights, "No converted weight values found"

    # Input: 135.6 lbs → 61.51 kg (135.6 * 0.453592)
    assert any(abs(w - 61.51) < 0.1 for w in weights), f"Expected ~61.51 kg in weights, got {weights[:5]}"

    # Subjects 1005 and 1010 have 'A' (coded missing) in weight column.
    # With none_if_non_numeric: true, these should produce null value_decimal.
    null_weight_records = [
        r for r in weight_records if r.get("value_quantity") and r["value_quantity"].get("value_decimal") is None
    ]
    assert len(null_weight_records) >= 2, (
        f"Expected at least 2 null weights from coded missing values, got {len(null_weight_records)}"
    )


# --- Error handling tests ---
# These reuse the prepared data and schema from the main pipeline run,
# then run the map step through Make with deliberately broken specs.


def _run_map_step(from_raw_pipeline_output, *, strict, tmp_path_factory):
    """Run make map-data with good + bad specs, returning the subprocess result and output dir."""
    pipeline_out = from_raw_pipeline_output["output_dir"]
    schema_file = pipeline_out / f"{SCHEMA_NAME}.yaml"
    prepared_dir = from_raw_pipeline_output["prepared_dir"]

    tmp = tmp_path_factory.mktemp("error-map")
    map_output = tmp / "mapped-data"
    spec_dir = tmp / "specs"
    spec_dir.mkdir()

    # Copy good specs and bad specs into one directory
    for src in (root_dir / "toy_data" / "from_raw" / "specs").glob("*.yaml"):
        shutil.copy2(src, spec_dir / src.name)
    for src in ERROR_SPEC_DIR.glob("*.yaml"):
        shutil.copy2(src, spec_dir / src.name)

    # Fake validation sentinel so Make skips validation
    validation_sentinel = tmp / "_validation_complete"
    validation_sentinel.touch()

    proc = subprocess.run(
        [
            "make",
            "-f",
            "pipeline.Makefile",
            "map-data",
            f"DM_INPUT_DIR={prepared_dir}",
            f"DM_TRANS_SPEC_DIR={spec_dir}",
            "DM_MAP_TARGET_SCHEMA=toy_data/target-schema.yaml",
            f"SCHEMA_FILE={schema_file}",
            f"MAPPING_OUTPUT_DIR={map_output}",
            f"MAPPING_SUCCESS_SENTINEL={map_output}/_mapping_complete",
            f"VALIDATION_SUCCESS_SENTINEL={validation_sentinel}",
            f"DM_MAP_STRICT={'true' if strict else 'false'}",
        ],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
    )
    return proc, map_output


def test_mapping_strict_mode_fails_on_bad_spec(from_raw_pipeline_output, tmp_path_factory):
    """In strict mode, a bad expression should crash the pipeline."""
    proc, _ = _run_map_step(from_raw_pipeline_output, strict=True, tmp_path_factory=tmp_path_factory)
    assert proc.returncode != 0, "Pipeline should fail in strict mode with bad spec"


def test_mapping_continue_on_error(from_raw_pipeline_output, tmp_path_factory):
    """In non-strict mode, the pipeline completes and surfaces errors from all entities."""
    proc, map_output = _run_map_step(from_raw_pipeline_output, strict=False, tmp_path_factory=tmp_path_factory)
    combined = proc.stdout + proc.stderr
    assert proc.returncode == 0, f"Pipeline should complete in non-strict mode.\n{combined[-500:]}"

    # The error summary should report failing entities
    assert "Mapping Error Summary" in combined, "Should print error summary"

    # Both error types should be surfaced in the per-entity logs
    log_dir = map_output / "logs"
    log_contents = {f.stem: f.read_text() for f in log_dir.glob("*.log")}
    assert any("division by zero" in v for v in log_contents.values()), (
        "Demography division-by-zero error should appear in logs"
    )
    assert any("not in safe subset" in v or "not defined" in v for v in log_contents.values()), (
        "Participant unsafe-expression error should appear in logs"
    )
