"""Module for transforming data using LinkML-Map schemas and specifications."""

import logging
import os
import shutil
import subprocess
import time
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

logger = logging.getLogger(__name__)


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
    strict: bool = False,
) -> Generator[dict[str, Any], None, None]:
    """Apply multiple LinkML-Map specifications to data and yield transformed objects."""
    for file in spec_files:
        logger.info("Processing spec file: %s", file.stem)
        block = None
        try:
            with open(file) as f:
                specs = yaml.safe_load(f)
            for block in specs:
                derivation = block["class_derivations"]
                logger.debug("Processing derivation block")
                for _, class_spec in derivation.items():
                    pht_id = class_spec["populated_from"]
                    if pht_id not in data_loader:
                        if strict:
                            raise FileNotFoundError(f"No data file for {pht_id}")
                        logger.warning("Skipping block in %s — no data file for %s", file.stem, pht_id)
                        continue
                    rows = data_loader[pht_id]

                    transformer = ObjectTransformer(
                        source_schemaview=source_schemaview,
                        target_schemaview=target_schemaview,
                    )
                    transformer.create_transformer_specification(block)

                    for row in rows:
                        mapped = transformer.map_object(row, source_type=pht_id)
                        yield mapped
        except (FileNotFoundError, ValueError):
            if strict:
                raise
            logger.exception("Error processing %s | Block: %s", file, block)
            continue


def discover_entities(var_dir: Path) -> list[str]:
    """
    Discover entity names from top-level class_derivations in spec files.

    Scans all YAML files in var_dir and collects the unique class names
    from top-level class_derivations blocks. Nested class_derivations
    (inside object_derivations) are ignored since those represent
    sub-components like Quantity, not standalone entities.

    Returns a sorted list of entity names.
    """
    entities: set[str] = set()
    yaml_files = sorted([*var_dir.rglob("*.yaml"), *var_dir.rglob("*.yml")])
    for yaml_file in yaml_files:
        try:
            with open(yaml_file) as f:
                specs = yaml.safe_load(f)
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Skipping spec file %s due to read/parse error: %s", yaml_file, e)
            continue
        if not isinstance(specs, list):
            continue
        for block in specs:
            if isinstance(block, dict) and "class_derivations" in block:
                entities.update(block["class_derivations"].keys())
    return sorted(entities)


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
    strict=False,
) -> None:
    """Process each entity and write to output files."""
    start = time.perf_counter()
    for entity in entities:
        spec_files = get_spec_files(var_dir, f"^    {entity}:")
        if not spec_files:
            logger.info("Skipping %s (no spec files)", entity)
            continue

        logger.info("Starting %s", entity)
        output_path = f"{output_dir}/{'-'.join(x for x in [output_prefix, entity, output_postfix] if x)}.{output_type}"

        iterable = multi_spec_transform(data_loader, spec_files, source_schemaview, target_schemaview, strict=strict)
        chunks = chunked(iterable, chunk_size)
        key_name = entity.lower() + "s"

        stream = make_stream(output_type, key_name=key_name)

        with open(output_path, "w") as f:
            for output in stream.process(chunks):
                f.write(output)

        if isinstance(stream, TSVStream) and stream.must_update_headers:
            logger.info("Rewriting %s (headers changed)", entity)
            tmp_path = output_path + ".tmp"
            with open(output_path, "r") as src, open(tmp_path, "w") as dst:
                chunks = chunked(src, chunk_size)
                dst.writelines(TSVStream.rewrite_header_and_pad(chunks, stream.next_headers))
            os.replace(tmp_path, output_path)

        logger.info("%s Complete", entity)

    end = time.perf_counter()
    logger.info("Time: %.2f seconds", end - start)


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
    ] = "",
    output_postfix: Annotated[
        str,
        typer.Option(),
    ] = "",
    output_type: Annotated[
        StreamFormat,
        typer.Option(),
    ] = "jsonl",
    chunk_size: Annotated[
        int,
        typer.Option(),
    ] = 1000,
    strict: Annotated[
        bool,
        typer.Option(help="Fail on data/spec mismatches instead of skipping"),
    ] = False,
):
    """Run LinkML-Map transformation from command line arguments."""
    source_schemaview = SchemaView(get_schema(source_schema))
    target_schemaview = SchemaView(get_schema(target_schema))

    data_loader = DataLoader(data_dir)

    entities = discover_entities(var_dir)
    logger.info("Discovered entities: %s", entities)
    if not entities:
        logger.warning("No entities discovered in %s - pipeline will produce no outputs", var_dir)

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
        strict=strict,
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logging.getLogger("linkml_runtime").setLevel(logging.WARNING)
    typer.run(main)
