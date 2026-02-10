"""
=============================================================================
BDC Harmonization Ingest Validator (Cohort-Agnostic)
=============================================================================
Project: NHLBI BioData Catalyst (BDC) Data Management Center (DMC) 
Phase:   Post-Pilot Cleanup & Documentation
Version: 2.0.0

PURPOSE:
This tool serves as a "Quality Gate" between the raw dbGaP ingestion and the 
core LinkML transformation pipeline (The Factory). It ensures that the 
pre-processing script (prepare_input.py) has correctly normalized the data 
for ingestion.

FUNCTIONALITY:
1. Coverage Scan: Dynamically identifies all PHT files required by the 
   Harmonized Variables (HV) Dictionary for a specific cohort.
2. Contract Validation:
   - Filename: Verifies PHT-based naming convention.
   - Anchor: Ensures 'dbGaP_Subject_ID' is the primary key (Column 0).
   - Mapping: Confirms descriptive headers were replaced by PHV IDs.
   - Sequence: Enforces strict preservation of original column order.
   - Integrity: Validates record counts against read-only raw sources.

GOVERNANCE & RULES:
- Operates on the 'Triad' architecture: HM (Blueprint), HV (Dictionary), 
  and dm-bip (Factory).
- Read-Only Compliance: Streams compressed raw data to bypass enclave 
  directory mount restrictions.
- Success/Failure reporting follows the Project's QC reporting standards.

=============================================================================
"""

import os
import gzip
import pandas as pd
import re
import yaml
import glob

# =============================================================================
# GLOBAL CONFIGURATION & DEFAULTS
# =============================================================================
# The name of the cohort to validate (e.g., 'CHS', 'ARIC', 'FHS', 'CARDIA')
COHORT = "CHS"

# Specific consent/sub-group identifier for directory targeting
CONSENT = "c4"

# The specific consent/sub-group folder name in the read-only project space
SUBGROUP_DIR = "parent-CHS_DS-CVD-NPU-MDS_-phs000287-v7-p1-c4"

# -- PATHS (Seven Bridges Standard Environment) --

# Read-only source directory for raw dbGaP .txt.gz files
RAW_BASE_DIR = f"/sbgenomics/project-files/PilotParentStudies/{SUBGROUP_DIR}"

# Writeable workspace for the cleaned/prepared .tsv files (Target of validation)
CLEANED_BASE_DIR = f"/sbgenomics/workspace/output/{COHORT}_{CONSENT}_cleaned"

# Location of the Harmonized Variables (HV) transformation logic repository
HV_REPO_DIR = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/"

# =============================================================================

class IngestValidator:
    def __init__(self, cohort, raw_dir, cleaned_dir, hv_dir):
        """
        Initializes the validator with project-specific paths.
        """
        self.cohort = cohort
        self.raw_dir = raw_dir
        self.cleaned_dir = cleaned_dir
        self.hv_ingest_path = os.path.join(hv_dir, f"{cohort}-ingest")

    def get_required_phts(self):
        """
        Variable-to-File Coverage Scan (FP-006):
        Parses all YAML files in the cohort's HV directory to identify 
        which PHT tables are required for harmonization. This ensures 
        the ingest matches the mapping SME requirements.
        """
        required_phts = set()
        yaml_files = glob.glob(os.path.join(self.hv_ingest_path, "*.yaml"))
        
        if not yaml_files:
            print(f"⚠️ Warning: No YAML files found in {self.hv_ingest_path}")
            return []

        for y_file in yaml_files:
            with open(y_file, 'r') as f:
                try:
                    content = yaml.safe_load(f)
                    # Convert to string to find all pht occurrences in the mapping logic
                    raw_text = yaml.dump(content)
                    found = re.findall(r'pht\d+', raw_text)
                    required_phts.update(found)
                except yaml.YAMLError:
                    print(f"Error parsing {y_file}")
        
        return sorted(list(required_phts))

    def get_raw_expectations(self, gz_path):
        """
        Read-Only Expectation Extraction:
        Streams the compressed raw file (read-only) to extract PHV order 
        and record counts without unzipping to disk, bypassing mount limits.
        """
        phv_list = []
        data_row_count = 0
        
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f:
            for line in f:
                if line.startswith('##'):
                    # Capture phvXXXXXX, preserving physical left-to-right order
                    phv_list = re.findall(r'phv\d+', line)
                elif not line.startswith('#') and line.strip():
                    data_row_count += 1

        # Return PHVs and total records (subtracting 1 for the descriptive header)
        return phv_list, (data_row_count - 1)

    def validate_file(self, pht):
        """
        Strict Contract Validation:
        Performs the check of the cleaned file against the raw source.
        Checks: Filename, Anchor Column, PHV Sequence, and Row Integrity.
        """
        cleaned_file = os.path.join(self.cleaned_dir, f"{pht}.tsv")
        
        # 1. Presence Check
        if not os.path.exists(cleaned_file):
            return False, "File missing in cleaned directory"

        # 2. Find Raw Source
        # dbGaP files often look like phs...pht00XXXX...txt.gz
        raw_matches = glob.glob(os.path.join(self.raw_dir, f"*{pht}*.txt.gz"))
        if not raw_matches:
            return False, f"No raw source .txt.gz found containing '{pht}'"
        
        try:
            expected_phvs, expected_records = self.get_raw_expectations(raw_matches[0])
            expected_header = ['dbGaP_Subject_ID'] + expected_phvs
            
            # Load cleaned data
            df_actual = pd.read_csv(cleaned_file, sep='\t')
            actual_header = list(df_actual.columns)
            actual_records = len(df_actual)

            # Check Header Sequence and Anchor
            if actual_header != expected_header:
                if len(actual_header) != len(expected_header):
                    return False, f"Col count mismatch (Expected {len(expected_header)}, got {len(actual_header)})"
                return False, f"Column order violation or naming mismatch"

            # Check Row Integrity
            if actual_records != expected_records:
                return False, f"Row count mismatch (Source: {expected_records}, Cleaned: {actual_records})"

            return True, f"Verified ({actual_records} rows, {len(actual_header)} columns)"

        except Exception as e:
            return False, f"Validation Error: {str(e)}"

    def run_full_scan(self):
        """
        Executive Execution Loop:
        Scans all required files and prints a pass/fail summary report.
        """
        print(f"--- BDC Ingest Validation: {self.cohort} ---")
        required_phts = self.get_required_phts()
        print(f"Scanning for {len(required_phts)} required PHT tables...\n")

        summary = {"PASS": 0, "FAIL": 0}
        
        for pht in required_phts:
            success, message = self.validate_file(pht)
            status = "✅ PASS" if success else "❌ FAIL"
            if success: summary["PASS"] += 1
            else: summary["FAIL"] += 1
            
            print(f"{status} | {pht}.tsv: {message}")

        print("\n" + "="*40)
        print(f"FINAL SUMMARY FOR {self.cohort}")
        print(f"PASSED: {summary['PASS']}")
        print(f"FAILED: {summary['FAIL']}")
        print("="*40)

if __name__ == "__main__":
    validator = IngestValidator(
        cohort=COHORT,
        raw_dir=RAW_BASE_DIR,
        cleaned_dir=CLEANED_BASE_DIR,
        hv_dir=HV_REPO_DIR
    )
    validator.run_full_scan()