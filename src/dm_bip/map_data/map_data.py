"""Module for transforming data using LinkML-Map schemas and specifications."""

import os
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from typing import Annotated, Any, Generator

import typer
import yaml
from linkml.validator.loaders import TsvLoader
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_runtime import SchemaView
from linkml_runtime.linkml_model import SchemaDefinition
from more_itertools import chunked

from dm_bip.map_data.streams import StreamFormat, TSVStream, make_stream


class DataLoader:
    """Load TSV files based on populated_from identifiers."""

    def __init__(self, base_path: Path):
        """Initialize with the base directory containing TSV files."""
        self.base_path = base_path

    def __getitem__(self, pht_id: str):
        """Load instances from the TSV file corresponding to the given populated_from identifier."""
        file_path = self.base_path / f"{pht_id}.tsv"

        if not file_path.exists():
            raise FileNotFoundError(f"No TSV file found for {pht_id} at {file_path}")

        return TsvLoader(file_path).iter_instances()

    def __contains__(self, pht_id):
        """Check if a TSV file exists for the given populated_from identifier."""
        return (self.base_path / f"{pht_id}.tsv").exists()


def get_spec_files(directory: Path, search_string: str) -> list[Path]:
    """
    Find YAML files in the directory that contain the search_string.

    Returns a sorted list of matching file paths.
    """
    grep_path = shutil.which("grep")
    if grep_path is None:
        raise RuntimeError("grep not found on system PATH")

    # Safe subprocess call: no shell, trusted executable, literal args
    result = subprocess.run(  # noqa: S603
        [grep_path, "-rl", "--", search_string, str(directory)],
        stdout=subprocess.PIPE,
        text=True,
        check=False,
        shell=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return []

    matches = [Path(p.strip()) for p in result.stdout.strip().split("\n")]
    yaml_paths = [p for p in matches if p.suffix in (".yaml", ".yml")]
    return sorted(yaml_paths, key=lambda p: p.stem)


def multi_spec_transform(
    data_loader: DataLoader,
    spec_files: list[Path],
    source_schemaview: SchemaView,
    target_schemaview: SchemaView,
) -> Generator[dict[str, Any], None, None]:
    """Apply multiple LinkML-Map specifications to data and yield transformed objects."""
    for file in spec_files:
        print(f"{file.stem}", end="", flush=True)
        block = None
        try:
            with open(file) as f:
                specs = yaml.safe_load(f)
            for block in specs:
                derivation = block["class_derivations"]
                print(".", end="", flush=True)
                for _, class_spec in derivation.items():
                    pht_id = class_spec["populated_from"]
                    rows = data_loader[pht_id]

                    transformer = ObjectTransformer(
                        source_schemaview=source_schemaview,
                        target_schemaview=target_schemaview,
                    )
                    transformer.create_transformer_specification(block)

                    for row in rows:
                        mapped = transformer.map_object(row, source_type=pht_id)
                        yield mapped
            print("")
        except Exception as e:
            print(f"\n⚠️  Error processing {file}: {e.__class__.__name__} - {e}")
            print(block)
            traceback.print_exc()
            raise


def get_schema(schema_path: Path) -> SchemaDefinition:
    """Load and return a LinkML schema from the given path."""
    sv = SchemaView(schema_path)
    schema = sv.schema

    # FIXME: When would schema be None? I don't know, but that's what's in the types.
    if schema is None:
        raise ValueError()

    return schema


def process_entities(
    *,
    entities,
    data_loader,
    var_dir,
    source_schemaview,
    target_schemaview,
    output_dir,
    output_prefix,
    output_postfix,
    output_type,
    chunk_size=1000,
) -> None:
    """Process each entity and write to output files."""
    start = time.perf_counter()
    for entity in entities:
        spec_files = get_spec_files(var_dir, f"^    {entity}:")
        if not spec_files:
            print(f"Skipping {entity} (no spec files)")
            continue

        print(f"Starting {entity}")
        output_path = f"{output_dir}/{output_prefix}-{entity}-{output_postfix}.{output_type}"

        iterable = multi_spec_transform(data_loader, spec_files, source_schemaview, target_schemaview)
        chunks = chunked(iterable, chunk_size)
        key_name = entity.lower() + "s"

        stream = make_stream(output_type, key_name=key_name)

        with open(output_path, "w") as f:
            for output in stream.process(chunks):
                f.write(output)

        if isinstance(stream, TSVStream) and stream.must_update_headers:
            print(f"Rewriting {entity} (headers changed)")
            tmp_path = output_path + ".tmp"
            with open(output_path, "r") as src, open(tmp_path, "w") as dst:
                chunks = chunked(src, chunk_size)
                dst.writelines(TSVStream.rewrite_header_and_pad(chunks, stream.next_headers))
            os.replace(tmp_path, output_path)

        print(f"{entity} Complete")

    end = time.perf_counter()
    print(f"Time: {end - start:.2f} seconds")


def main(
    source_schema: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    target_schema: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
        ),
    ],
    data_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    var_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
        ),
    ],
    output_prefix: Annotated[
        str,
        typer.Option(),
    ],
    output_postfix: Annotated[
        str,
        typer.Option(),
    ],
    output_type: Annotated[
        StreamFormat,
        typer.Option(),
    ] = "jsonl",
    chunk_size: Annotated[
        int,
        typer.Option(),
    ] = 1000,
):
    """Run LinkML-Map transformation from command line arguments."""
    source_schemaview = SchemaView(get_schema(source_schema))
    target_schemaview = SchemaView(get_schema(target_schema))

    data_loader = DataLoader(data_dir)

    entities = [
        "Condition",
        "Demography",
        "DrugExposure",
        "MeasurementObservation",
        "Observation",
        "Participant",
        "Person",
        "Procedure",
        "ResearchStudy",
        "SdohObservation",
    ]

    os.makedirs(output_dir, exist_ok=True)

    process_entities(
        entities=entities,
        data_loader=data_loader,
        var_dir=var_dir,
        source_schemaview=source_schemaview,
        target_schemaview=target_schemaview,
        output_dir=output_dir,
        output_prefix=output_prefix,
        output_postfix=output_postfix,
        output_type=output_type,
        chunk_size=chunk_size,
    )


if __name__ == "__main__":
    typer.run(main)
