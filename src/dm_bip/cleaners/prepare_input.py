import os
import re
import gzip
import argparse
from pathlib import Path

def get_required_phts(mapping_dir, verbose=False):
    """
    Scrapes a directory of YAML files to collect all referenced pht IDs.
    This ensures we only process the tables actually used in the harmonization logic.
    """
    phts = set()
    mapping_path = Path(mapping_dir)
    
    if not mapping_path.exists() or not mapping_path.is_dir():
        print(f"Warning: Mapping directory {mapping_dir} not found. Processing ALL files.")
        return None
    
    # We read YAMLs as raw text to quickly find 'pht' IDs without full parsing overhead
    yaml_files = list(mapping_path.glob("*.yaml"))
    for yaml_file in yaml_files:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'(pht[0-9]+)', content)
            for match in matches:
                phts.add(match)
    
    print(f"--- Inventory: Scraped {len(phts)} unique pht IDs from {len(yaml_files)} YAML files ---")
    return phts

def clean_dbgap_content(line_iterator, verbose=False):
    """
    Standardizes dbGaP file streams by:
    1. Stripping all metadata (lines starting with # or blank).
    2. Identifying the first valid row as the header.
    3. Cleaning the header (removing ## markers and phv version suffixes).
    4. Prepending dbGaP_Subject_ID if the first column is unlabeled.
    """
    header_processed = False

    for line in line_iterator:
        clean_line = line.strip()

        # STEP 1: Skip metadata (#) and empty lines. 
        # We don't stop until we hit the actual header row.
        if line.startswith('#') or clean_line == "":
            continue

        # STEP 2: Process the Header Row
        # This is the first line that is NOT metadata and NOT empty.
        if not header_processed:
            if verbose: print(f"   [Verbose] Raw Header Detected: {line[:60]}...")
            
            # Remove leading '##' and any adjacent whitespace or tabs.
            # This handles both '## phv...' and '##\tphv...' (found in pht001872).
            line = re.sub(r'^##\s*', '', line)
            
            # Ensure the Subject ID column is properly labeled.
            # If the line now starts with a variable ID (phv), we must prepend the ID label
            # to keep the column count and LinkML mapping consistent.
            if line.startswith('phv') or "Subject_ID" not in line:
                line = "dbGaP_Subject_ID\t" + line
            
            # Clean variable IDs: Strip suffixes (e.g., phv00123456.v1.p1 -> phv00123456).
            # This is critical so variable names match the LinkML YAML keys.
            line = re.sub(r'(phv\d{8})\.[^\s\t]*', r'\1', line)
            
            header_processed = True
            if verbose: print(f"   [Verbose] Final Standardized Header: {line[:80]}...")
            yield line
            continue

        # STEP 3: Stream the raw data rows.
        # Skip redundant header rows if the dbGaP file happens to repeat them.
        if "dbGaP_Subject_ID" in line and not line.startswith("dbGaP_Subject_ID"):
            if verbose: print("   [Verbose] Skipping redundant header row.")
            continue
            
        yield line

def main():
    parser = argparse.ArgumentParser(description="Clean and standardize dbGaP files for Pipeline Input")
    parser.add_argument("--source", required=True, help="Directory containing raw .txt.gz files")
    parser.add_argument("--mapping", required=True, help="Directory containing YAML mapping files")
    parser.add_argument("--output", help="Explicit destination directory for cleaned .tsv files")
    parser.add_argument("--verbose", action="store_true", help="Print detailed processing logs")
    
    args = parser.parse_args()
    
    source_path = Path(args.source)
    # Use explicit output if provided, otherwise default to [STUDY]_PipelineInput
    output_path = Path(args.output) if args.output else Path(f"{source_path.name}_PipelineInput")
    output_path.mkdir(exist_ok=True, parents=True)
    
    print(f"--- Target: Cleaning files into {output_path.absolute()} ---")
    
    # Identify which phts we actually need to process
    required_phts = get_required_phts(args.mapping, verbose=args.verbose)
    
    processed_count = 0
    # Process all compressed text files in the source directory
    for gz_file in source_path.glob("*.txt.gz"):
        # Identify the pht ID from the filename (e.g., CARDIA_pht001562.txt.gz)
        pht_match = re.search(r'(pht[0-9]+)', gz_file.name)
        if not pht_match:
            continue
            
        pht_id = pht_match.group(1)
        
        # Smart Filter: Skip files not explicitly mentioned in the YAML mappings
        if required_phts and pht_id not in required_phts:
            continue

        final_tsv = output_path / f"{pht_id}.tsv"
        print(f"Standardizing: {gz_file.name} -> {final_tsv.name}")
        
        try:
            # Open gzipped file in text mode ('rt')
            with gzip.open(gz_file, 'rt', encoding='utf-8', errors='ignore') as f_in:
                with open(final_tsv, 'w', encoding='utf-8') as f_out:
                    # Apply our cleaning generator to the stream
                    for cleaned_line in clean_dbgap_content(f_in, verbose=args.verbose):
                        f_out.write(cleaned_line)
            processed_count += 1
        except Exception as e:
            print(f"CRITICAL ERROR processing {gz_file.name}: {e}")

    print(f"\nSuccess! Processed {processed_count} files into: {output_path}")

if __name__ == "__main__":
    main()