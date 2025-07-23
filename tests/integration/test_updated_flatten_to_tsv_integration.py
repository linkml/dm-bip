"""Integration test for updated_flatten_to_tsv script."""

import subprocess
import tempfile
from pathlib import Path

import pytest

script_dir = Path(__file__).parent
test_dir = script_dir.parent
root_dir = test_dir.parent

input_dir = test_dir / "input"
output_dir = test_dir / "output"

SCRIPT_PATH = root_dir / "src" / "dm_bip" / "format_converter" / "updated_flatten_to_tsv.py"
SCHEMA_PATH = input_dir / "bdchm-corey-exp.yaml"
INSTANCE_PATH = input_dir / "transformed_person_data_example.yaml"


@pytest.fixture(scope="module")
def flattened_output_dir():
    """Run the flatten script and return the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir, prefix="flatten-output_") as tmp:
        out_dir = Path(tmp)

        cmd = [
            "python",
            str(SCRIPT_PATH),
            str(SCHEMA_PATH),
            str(INSTANCE_PATH),
            str(out_dir),
            "--container-key",
            "persons",
            "--container-class",
            "Person",
            "--mode",
            "per-class",
            "--list-style",
            "join",
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("STDOUT:\n", e.stdout)
            print("STDERR:\n", e.stderr)
            raise

        yield out_dir  # Keeps temp dir alive during the test


def test_flatten_outputs_files(flattened_output_dir):
    """Check that TSV files were created in the output directory."""
    tsv_files = list(flattened_output_dir.glob("*.tsv"))
    assert tsv_files, f"No TSV files found in {flattened_output_dir}"

    for f in tsv_files:
        contents = f.read_text().strip()
        assert contents, f"{f.name} is empty"


# List of expected TSV filenames
EXPECTED_TSV_FILES = [
    "Condition.tsv",
    "Demography.tsv",
    "Exposure.tsv",
    "MeasurementObservation.tsv",
    "Observation.tsv",
    "Participant.tsv",
    "Person.tsv",
    "Procedure.tsv",
    "SdohObservation.tsv",
]


@pytest.mark.parametrize("tsv_name", EXPECTED_TSV_FILES)
def test_flatten_output_matches_expected(tsv_name, flattened_output_dir):
    """Compare generated TSV output to expected TSV in tests/output/."""
    expected_file = output_dir / tsv_name
    actual_file = flattened_output_dir / tsv_name

    assert expected_file.exists(), f"Missing expected file: {expected_file}"
    assert actual_file.exists(), f"Missing actual output file: {actual_file}"

    expected = expected_file.read_text().strip()
    actual = actual_file.read_text().strip()

    assert actual == expected, f"Output mismatch in {actual_file.name}"
