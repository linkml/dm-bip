"""
Generalized utility to standardize dbGaP raw archives.
Removes metadata headers, filters tables based on mapping specs, 
and outputs standardized TSVs for LinkML validation.
"""
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
    Standardizes dbGaP file streams for the DMC pipeline.
    Ensures 'dbGaP_Subject_ID' is the anchor and all phv accessions are preserved.
    """
    phv_accessions = []
    header_processed = False

    for line in line_iterator:
        # STEP 1: Capture Accession IDs from the '##' line
        if line.startswith('##'):
            # Strip hashes and version suffixes (.v1.p1.c1)
            raw_parts = line.lstrip('#').strip().split('\t')
            # Clean each part to get just the 'phvXXXXXXXX'
            phv_accessions = [re.sub(r'(phv\d{8})\..*', r'\1', p).strip() for p in raw_parts if p.strip()]
            continue

        # STEP 2: Skip other metadata comments
        if line.startswith('#'):
            continue

        # STEP 3: Identify the Names Row and construct the Hybrid Header
        if not header_processed:
            if "dbGaP_Subject_ID" in line:
                if verbose: print(f"   [Verbose] Reconstructing header for mapping alignment...")
                
                # The first column is ALWAYS 'dbGaP_Subject_ID'.
                # We then append the FULL list of phvs we found.
                # This ensures phv00113019 is included.
                hybrid_header = ["dbGaP_Subject_ID"] + phv_accessions
                
                header_processed = True
                yield "\t".join(hybrid_header) + "\n"
                continue
            else:
                continue

        # STEP 4: Stream the raw data rows
        if line.strip():
            if "Intentionally Blank" in line:
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