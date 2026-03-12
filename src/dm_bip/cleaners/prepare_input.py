"""
Prepare raw dbGaP archives for the BDC data harmonization pipeline.

Standardizes compressed dbGaP phenotype table archives (.txt.gz)
into clean TSV files suitable for schema validation and LinkML-Map transformation.

Processing steps for each file:
  1. Decompress the gzipped archive
  2. Strip dbGaP metadata comment lines (lines starting with '#')
  3. Reconstruct the header row from the '##' accession line, preserving
     column order and cleaning phv version suffixes
  4. Skip the redundant human-readable column names row
  5. Filter out empty rows and "Intentionally Blank" placeholders
  6. Write the cleaned output as a standard TSV

File selection is driven by the mapping specification directory — only phenotype
tables (pht IDs) referenced in the YAML transformation specs are processed.
If no mapping directory is found, all tables are processed.

Parameters
----------
    --source    Directory containing raw .txt.gz dbGaP archive files
    --mapping   Directory containing YAML transformation spec files (used to
                determine which pht tables to process)
    --output    Destination directory for cleaned .tsv files (default:
                <source>_PipelineInput alongside the source directory)
    --verbose   Enable detailed per-file processing log output

The process exits with a non-zero status if any file fails to clean,
ensuring the downstream pipeline halts on data preparation errors.

"""

import gzip
import logging
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

logger = logging.getLogger(__name__)


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

    source_path = Path(source)
    # Use explicit output if provided, otherwise default to [STUDY]_PipelineInput
    output_path = output if output else Path(f"{source_path.name}_PipelineInput")
    output_path.mkdir(exist_ok=True, parents=True)

    logger.info(f"--- Target: Cleaning files into {output_path.absolute()} ---")

    # Identify which phts we actually need to process
    required_phts = get_required_phts(mapping, verbose=verbose)

    processed_count = 0
    failed_files = []
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
            failed_files.append(gz_file.name)

    logger.info(f"\nProcessed {processed_count} files into: {output_path}")

    if failed_files:
        msg = f"Failed to process {len(failed_files)} file(s): {', '.join(failed_files)}"
        logger.error(msg)
        raise SystemExit(msg)


if __name__ == "__main__":
    typer.run(main)
