"""
Generalized utility to standardize dbGaP raw archives.

Removes metadata headers, filters tables based on mapping specs,
and outputs standardized TSVs for LinkML validation.
"""

import gzip
import logging
import os
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

logger = logging.getLogger(__name__)


def _log_directory_tree(root: Path, max_depth: int = 2, max_entries: int = 200) -> None:
    """Log a bounded directory tree for quick environment inspection."""
    if not root.exists():
        logger.info(f"--- Directory snapshot: {root} (missing) ---")
        return

    logger.info(f"--- Directory snapshot: {root} (depth={max_depth}, max_entries={max_entries}) ---")
    entry_count = 0
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        rel_path = Path(dirpath).relative_to(root)
        depth = 0 if str(rel_path) == "." else len(rel_path.parts)
        if depth > max_depth:
            dirnames[:] = []
            continue

        indent = "  " * depth
        logger.info(f"{indent}{rel_path if depth else '.'}/")

        for name in sorted(dirnames):
            if entry_count >= max_entries:
                logger.info(f"{indent}  ... (truncated)")
                return
            logger.info(f"{indent}  {name}/")
            entry_count += 1

        for name in sorted(filenames):
            if entry_count >= max_entries:
                logger.info(f"{indent}  ... (truncated)")
                return
            logger.info(f"{indent}  {name}")
            entry_count += 1


def get_required_phts(mapping_dir, verbose=False):
    """
    Scrapes a directory of YAML files to collect all referenced pht IDs.

    This ensures we only process the tables actually used in the harmonization logic.
    """
    phts = set()
    mapping_path = Path(mapping_dir)

    if not mapping_path.exists() or not mapping_path.is_dir():
        logger.warning(f"Mapping directory {mapping_dir} not found. Processing ALL files.")
        return None

    # We read YAMLs as raw text to quickly find 'pht' IDs without full parsing overhead
    yaml_files = list(mapping_path.glob("*.yaml"))
    for yaml_file in yaml_files:
        with open(yaml_file, "r", encoding="utf-8") as f:
            content = f.read()
            matches = re.findall(r"(pht[0-9]+)", content)
            for match in matches:
                phts.add(match)

    logger.info(f"--- Inventory: Scraped {len(phts)} unique pht IDs from {len(yaml_files)} YAML files ---")
    return phts


def clean_dbgap_content(line_iterator, verbose=False):
    """
    Standardizes dbGaP file streams for the DMC pipeline.

    Ensures 'dbGaP_Subject_ID' is the anchor and all phv accessions are preserved.
    Preserves original column order by modifying the '##' line in place.
    """
    header_processed = False
    skip_next_names_line = False

    for line in line_iterator:
        # STEP 1: Skip metadata comments (but capture the '##' line for header)
        if line.startswith("#"):
            if line.startswith("##") and not header_processed:
                if verbose:
                    logger.info("   [Verbose] Modifying header to preserve original column order...")

                # Parse the ## line and preserve order
                parts = line.lstrip("#").split("\t")
                # Replace first element (originally "##") with dbGaP_Subject_ID
                parts[0] = "dbGaP_Subject_ID"
                # Clean phv accessions while preserving order
                cleaned_parts = []
                for part in parts:
                    if part:  # Skip empty parts
                        cleaned = re.sub(r"(phv\d{8})\..*", r"\1", part).strip()
                        cleaned_parts.append(cleaned)

                header_processed = True
                skip_next_names_line = True  # Next line might be the names line to skip
                yield "\t".join(cleaned_parts) + "\n"
            # Skip all other comment lines
            continue

        # STEP 2: Skip the names line immediately following the '##' line
        if skip_next_names_line and line.strip().startswith("dbGaP_Subject_ID"):
            skip_next_names_line = False  # Reset flag after skipping
            continue

        # STEP 3: Stream the raw data rows
        if line.strip():
            if "Intentionally Blank" in line:
                continue
            yield line


def main(
    source: Annotated[Path, typer.Option("--source", help="Directory containing raw .txt.gz files")],
    mapping: Annotated[Path, typer.Option("--mapping", help="Directory containing YAML mapping files")],
    output: Annotated[
        Optional[Path], typer.Option("--output", help="Explicit destination directory for cleaned .tsv files")
    ] = None,
    verbose: Annotated[bool, typer.Option("--verbose", help="Print detailed processing logs")] = False,
):
    """
    Execute the primary data preparation and cleaning pipeline.

    This function coordinates the reading of input files, standardization
    of dbGaP headers, and output generation.
    """
    # Set logging level based on verbose
    if verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    _log_directory_tree(Path("/"))
    _log_directory_tree(Path.cwd())

    source_path = Path(source)
    # Use explicit output if provided, otherwise default to [STUDY]_PipelineInput
    output_path = output if output else Path(f"{source_path.name}_PipelineInput")
    output_path.mkdir(exist_ok=True, parents=True)

    logger.info(f"--- Target: Cleaning files into {output_path.absolute()} ---")

    # Identify which phts we actually need to process
    required_phts = get_required_phts(mapping, verbose=verbose)

    processed_count = 0
    # Process all compressed text files in the source directory
    for gz_file in source_path.glob("*.txt.gz"):
        # Identify the pht ID from the filename (e.g., CARDIA_pht001562.txt.gz)
        pht_match = re.search(r"(pht[0-9]+)", gz_file.name)
        if not pht_match:
            continue

        pht_id = pht_match.group(1)

        # Smart Filter: Skip files not explicitly mentioned in the YAML mappings
        if required_phts and pht_id not in required_phts:
            continue

        final_tsv = output_path / f"{pht_id}.tsv"
        logger.info(f"Standardizing: {gz_file.name} -> {final_tsv.name}")

        try:
            # Open gzipped file in text mode ('rt')
            with gzip.open(gz_file, "rt", encoding="utf-8", errors="ignore") as f_in:
                with open(final_tsv, "w", encoding="utf-8") as f_out:
                    # Apply our cleaning generator to the stream
                    for cleaned_line in clean_dbgap_content(f_in, verbose=verbose):
                        f_out.write(cleaned_line)
            processed_count += 1
        except Exception as e:
            logger.error(f"CRITICAL ERROR processing {gz_file.name}: {e}")



    logger.info(f"\nSuccess! Processed {processed_count} files into: {output_path}")


if __name__ == "__main__":
    typer.run(main)
