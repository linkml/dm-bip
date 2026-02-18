"""
BDC Remote Logic Auditor (v2.0.0).

=============================================================================
Project: NHLBI BioData Catalyst (BDC) Data Management Center (DMC)
Phase:   Phase 0.5 - Remote Mapping Validation

PURPOSE:
Validates HV transformation YAMLs hosted on GitHub against a local
Master Manifest (CSV).

KEY FEATURES:
1. GitHub Integration: Fetches specification files directly via URL.
2. Manifest Authority: Uses the provided CSV as the "Source of Truth."
3. Version Agnostic: Cleans versioning (e.g., .v1.p1) for reliable matching.
=============================================================================
"""

import os
import re

import pandas as pd
import requests
import yaml

# =============================================================================
# 1. CONFIGURATION
# =============================================================================

# The GitHub URL provided by the user
GITHUB_TREE_URL = "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/ARIC"

# The local spreadsheet authority
MANIFEST_PATH = "dbgap_variables_priority_cohorts_V2.csv"

# Study name filter to use within the Manifest
STUDY_FILTER = "Atherosclerosis Risk in Communities (ARIC) Cohort"

# Output results
AUDIT_OUTPUT_FILE = "remote_mapping_audit_results.csv"

# =============================================================================
# 2. HELPER FUNCTIONS
# =============================================================================

def parse_github_url(url):
    """Convert a GitHub web URL into a GitHub API URL for contents."""
    # Pattern: https://github.com/{owner}/{repo}/tree/{branch}/{path}
    pattern = r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)"
    match = re.match(pattern, url)
    if not match:
        raise ValueError("Invalid GitHub URL format. Use the /tree/{branch}/{path} format.")

    owner, repo, branch, path = match.groups()
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    return api_url

def clean_accession(val):
    """Standardize PHT/PHV by removing versioning (e.g., pht001234.v1.p1 -> pht001234)."""
    if pd.isna(val):
        return ""
    match = re.search(r"(pht\d+|phv\d+)", str(val).lower())
    return match.group(1) if match else str(val).lower()

# =============================================================================
# 3. MAIN AUDIT LOGIC
# =============================================================================

def run_remote_audit():
    """Run remote audit to validate GitHub YAMLs against local manifest."""
    print("--- 🩺 Initializing Remote Mapping Audit ---")

    # 1. Load the Local Manifest Authority
    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ CRITICAL: Manifest file {MANIFEST_PATH} not found.")
        return

    manifest_df = pd.read_csv(MANIFEST_PATH)
    # Filter for the target study and clean accession columns
    auth_df = manifest_df[manifest_df['Study'].str.contains(STUDY_FILTER, na=False, case=False)].copy()
    auth_df['pht_clean'] = auth_df['Dataset accession'].apply(clean_accession)
    auth_df['phv_clean'] = auth_df['Variable accession'].apply(clean_accession)

    print(f"✅ Loaded {len(auth_df)} authoritative mappings for {STUDY_FILTER}.")

    # 2. Fetch YAML list from GitHub
    api_url = parse_github_url(GITHUB_TREE_URL)
    response = requests.get(api_url, timeout=30)
    if response.status_code != 200:
        print(f"❌ Failed to fetch GitHub contents: {response.status_code}")
        return

    files = response.json()
    yaml_files = [f for f in files if f['name'].endswith('.yaml')]
    print(f"📡 Found {len(yaml_files)} YAML files on GitHub. Starting Audit...\n")

    mismatches = []

    # 3. Process Remote YAMLs
    for yf in yaml_files:
        print(f"Processing: {yf['name']}...")
        raw_resp = requests.get(yf['download_url'], timeout=30)
        config = yaml.safe_load(raw_resp.text)

        configs = config if isinstance(config, list) else [config]
        for item in configs:
            if not isinstance(item, dict):
                continue
            derivations = item.get('class_derivations', {})

            for _class_name, details in derivations.items():
                source_pht = clean_accession(details.get('populated_from'))
                if not source_pht:
                    continue

                # Filter manifest for this specific PHT
                authorized_phvs = auth_df[auth_df['pht_clean'] == source_pht]['phv_clean'].tolist()

                slots = details.get('slot_derivations', {})
                for slot_name, slot_details in slots.items():
                    phv_mapped = clean_accession(slot_details.get('populated_from'))

                    if phv_mapped.startswith('phv'):
                        # THE TEST: Is this PHV mapped to this PHT in the Master Manifest?
                        if phv_mapped not in authorized_phvs:
                            is_critical = "YES" if slot_name == "associated_participant" else "NO"

                            mismatches.append({
                                'CRITICAL': is_critical,
                                'Remote_YAML': yf['name'],
                                'PHT': source_pht,
                                'Slot': slot_name,
                                'Invalid_PHV': phv_mapped,
                                'Study_Context': STUDY_FILTER
                            })

                            status = "🚨 [CRITICAL]" if is_critical == "YES" else "❌ [ERROR]"
                            print(f"   {status} {slot_name}: {phv_mapped} is not authorized for {source_pht}")

    # 4. Final Reporting
    if mismatches:
        df_out = pd.DataFrame(mismatches).sort_values(by='CRITICAL', ascending=False)
        df_out.to_csv(AUDIT_OUTPUT_FILE, index=False)
        print(f"\nAudit complete. {len(mismatches)} issues found. Report saved to {AUDIT_OUTPUT_FILE}.")
    else:
        print("\n✅ SUCCESS: All remote mappings are authorized by the Master Manifest.")

if __name__ == "__main__":
    run_remote_audit()
