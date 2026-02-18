"""
BDC Mapping Integrity Validator & Auditor (v1.4.1).

=============================================================================
Project: NHLBI BioData Catalyst (BDC) Data Management Center (DMC)
Component: Harmonization Pipeline Static Analysis
Scope: Phase 0.5 - Pre-Harmonization Logic Validation

PURPOSE:
This tool validates the referential integrity of Harmonized Variable (HV)
transformation YAML files. It cross-references the mapping logic against the
physical dbGaP source datasets (PHTs) to ensure every variable (PHV) exists.

TECHNICAL SCOPE:
1. REFERENTIAL CHECK: Verifies that 'populated_from' PHVs exist in source TSVs.
2. JOIN KEY AUDIT: Flags 'associated_participant' mismatches as [CRITICAL].
3. LIVE LOGGING: Streams errors to the console for real-time debugging.
4. AUDIT TRAIL: Generates a CSV report with official dbGaP metadata links.

URL LOGIC:
Builds deep-links using the study_id and pht_id to allow human verification
of variable metadata directly on the NCBI dbGaP website.

GOVERNANCE:
- [CRITICAL] errors typically cause Cartesian Products (row expansion).
- These must be resolved in the HV YAMLs before Phase 1 (Harmonization).

CONTRIBUTORS:
NHLBI BDC DMC Engineering Team
=============================================================================
"""

import glob
import os

import pandas as pd
import yaml

# =============================================================================
# 1. GLOBAL CONFIGURATION
# =============================================================================

# Path to the directory containing 'cleaned' Phase 0 TSV files (e.g., pht001450.tsv)
CLEANED_DATA_DIR = "/sbgenomics/workspace/output/CHS_c4_cleaned"

# Path to the directory containing the HV transformation YAML files (Mapping Logic)
HV_LOGIC_DIR = "/sbgenomics/workspace/NHLBI-BDC-DMC-HV/priority_variables_transform/CHS-ingest"

# The official dbGaP Study Accession for the CHS Cohort
STUDY_ID = "phs000287.v7.p1"

# Output filename for the resulting audit report
AUDIT_OUTPUT_FILE = "mapping_integrity_audit.csv"

# =============================================================================
# 2. CORE VALIDATION ENGINE
# =============================================================================


def validate_mapping_integrity():
    """
    Execute mapping integrity validation.

    Parse HV YAMLs, extract PHV mappings, and validate them against physical
    file headers cached in memory.
    """
    print("\n" + "=" * 85)
    print("🚀 INITIALIZING BDC MAPPING INTEGRITY AUDIT (SC-010)")
    print(f"   Target Study : {STUDY_ID}")
    print(f"   Logic Source : {HV_LOGIC_DIR}")
    print("=" * 85 + "\n")

    # Discovery: Find all YAML transformation files
    yaml_files = glob.glob(os.path.join(HV_LOGIC_DIR, "*.yaml"))

    mismatches = []        # Store error records for CSV export
    checked_count = 0      # Counter for total variables validated
    header_cache = {}      # Local cache to prevent redundant disk I/O

    # Iterate through each transformation file
    for yaml_path in yaml_files:
        current_yaml = os.path.basename(yaml_path)

        with open(yaml_path, 'r') as f:
            try:
                # Load YAML - handles both single dict and list-based LinkML-Map formats
                config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                print(f"❌ YAML Syntax Error in {current_yaml}: {exc}")
                continue

            # Normalize data structure
            configs = config if isinstance(config, list) else [config]

            for item in configs:
                # Process only configuration blocks (ignore metadata lists)
                if not isinstance(item, dict):
                    continue

                # Navigate to the class_derivations (e.g., Person, Demography)
                derivations = item.get('class_derivations', {})
                for class_name, details in derivations.items():

                    # Get the PHT identifier (e.g., pht001490)
                    source_pht = details.get('populated_from')
                    if not source_pht:
                        continue

                    # ---------------------------------------------------------
                    # HEADER CACHE MANAGEMENT
                    # ---------------------------------------------------------
                    # Load PHT column headers only once per run to optimize speed
                    if source_pht not in header_cache:
                        tsv_path = os.path.join(CLEANED_DATA_DIR, f"{source_pht}.tsv")
                        if os.path.exists(tsv_path):
                            # Read only the header row
                            header_cache[source_pht] = pd.read_csv(
                                tsv_path, sep='\t', nrows=0
                            ).columns.tolist()
                        else:
                            # Log missing data files which prevent validation
                            print(
                                f"⚠️  DATA MISSING: {source_pht}.tsv not found in ingest folder."
                            )
                            header_cache[source_pht] = None

                    actual_columns = header_cache[source_pht]
                    if actual_columns is None:
                        continue

                    # ---------------------------------------------------------
                    # VARIABLE-LEVEL VERIFICATION
                    # ---------------------------------------------------------
                    slots = details.get('slot_derivations', {})
                    for slot_name, slot_details in slots.items():
                        # Extract the mapped variable (e.g., phv00123456)
                        phv_mapped = slot_details.get('populated_from')

                        # Process only standard PHV strings (ignore functions/constants)
                        if isinstance(phv_mapped, str) and 'phv' in phv_mapped.lower():
                            checked_count += 1

                            # THE CORE TEST: Check if PHV exists in the actual source file
                            if phv_mapped not in actual_columns:

                                # Generate official dbGaP deep-link for remediation
                                pht_num = ''.join(filter(str.isdigit, source_pht))
                                dbgap_url = f"https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/dataset.cgi?study_id={STUDY_ID}&pht={pht_num}"

                                # Highlight Join Key failures (Cause of 59-row expansion issue)
                                is_critical = (
                                    "YES"
                                    if slot_name == "associated_participant"
                                    else "NO"
                                )

                                error_entry = {
                                    'CRITICAL_JOIN_KEY': is_critical,
                                    'Source_YAML': current_yaml,
                                    'Target_Class': class_name,
                                    'Source_PHT': source_pht,
                                    'Target_Slot': slot_name,
                                    'Mapped_PHV_ID': phv_mapped,
                                    'Verify_at_dbGaP': dbgap_url
                                }
                                mismatches.append(error_entry)

                                # DUAL OUTPUT: Immediate console notification
                                tag = (
                                    "🚨 [CRITICAL]"
                                    if is_critical == "YES"
                                    else "❌ [ERROR]"
                                )
                                print(f"{tag} Mismatch found in {current_yaml}")
                                print(
                                    f"   Slot: {slot_name} | Target: {source_pht} | Missing PHV: {phv_mapped}"
                                )
                                print(f"   Verify: {dbgap_url}\n")

    # =========================================================================
    # 3. AUDIT COMPLETION & DATA EXPORT
    # =========================================================================
    print("-" * 85)
    print("AUDIT SUMMARY")
    print(f"   Total YAMLs Analyzed     : {len(yaml_files)}")
    print(f"   Total Variables Validated : {checked_count}")

    if not mismatches:
        print("\n✅ STATUS: All PHV references verified. Mapping Logic is consistent.")
    else:
        # Sort report: Critical Join Key errors at the top
        df_err = pd.DataFrame(mismatches).sort_values(
            by='CRITICAL_JOIN_KEY', ascending=False
        )
        df_err.to_csv(AUDIT_OUTPUT_FILE, index=False)

        crit_n = len(df_err[df_err['CRITICAL_JOIN_KEY'] == "YES"])
        print(f"\n❌ STATUS: Found {len(mismatches)} invalid variable references.")
        print(
            f"   - {crit_n} errors identified as CRITICAL (affecting Join Keys)."
        )
        print(f"\n📝 Full Audit Trail saved to: {AUDIT_OUTPUT_FILE}")
        print("   Resolve CRITICAL errors first to fix row expansion issues.")
    print("-" * 85 + "\n")

if __name__ == "__main__":
    validate_mapping_integrity()
