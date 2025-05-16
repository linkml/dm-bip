"""Tests to make sure that the pipeline is working as expected against test data."""
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
toy_data_input_dir = root_dir / "toy_data/raw_data"

SCHEMA_NAME = "ToyDataSchema"


@pytest.fixture(scope="module")
def toy_data_pipeline_output():
    """Run the pipeline on the toy dataset, with the output in a temporary directory."""
    temp_dir = tempfile.TemporaryDirectory(dir=output_dir, prefix="toy-data-pipeline_")
    toy_data_output_dir = Path(temp_dir.name)
    env = os.environ.copy()

    env.update(
        {
            "DM_INPUT_DIR": str(toy_data_input_dir),
            "DM_OUTPUT_DIR": str(toy_data_output_dir),
            "DM_SCHEMA_NAME": SCHEMA_NAME,
        }
    )

    proc = subprocess.run(
        ["make", "schema-create"],
        cwd=str(root_dir),
        capture_output=True,
        text=True,
        env=env,
    )

    if proc.returncode != 0:
        temp_dir.cleanup()
        raise RuntimeError(f"Could not run pipeline from toy data. stderr from `make schema-create`:\n\n{proc.stderr}")

    yield toy_data_output_dir

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
    assert "no input files detected" in result.stderr


def test_pipeline_schema(toy_data_pipeline_output: Path):
    """Ensure that the pipeline creates a LinkML schema as expected."""
    schema_path = toy_data_pipeline_output / "schema-automator-data" / f"{SCHEMA_NAME}.yaml"
    assert schema_path.exists()
    schema_view = SchemaView(schema_path)

    input_files = [f for f in toy_data_input_dir.iterdir() if f.name.endswith(("csv", "tsv"))]
    assert len(schema_view.all_classes()) == len(input_files)
