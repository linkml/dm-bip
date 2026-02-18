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

# Mapping of cohort names (as they appear in CSV) to their GitHub transform directories
COHORT_CONFIGS = {
    "Atherosclerosis Risk in Communities (ARIC) Cohort":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/ARIC",

    "CARDIA Cohort":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/CARDIA",

    "Framingham Cohort":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/FHS",

    ("Cardiovascular Health Study (CHS) Cohort: an NHLBI-funded observational study "
     "of risk factors for cardiovascular disease in adults 65 years or older"):
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/CHS",

    "Hispanic Community Health Study /Study of Latinos (HCHS/SOL)":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/HCHS_SOL",

    "Jackson Heart Study (JHS) Cohort":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/JHS",

    "Multi-Ethnic Study of Atherosclerosis (MESA) Cohort":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/MESA",

    "Women's Health Initiative":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/WHI",

    "Genetic Epidemiology of COPD (COPDGene)":
        "https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform/COPDGene"
}

# The local spreadsheet authority
MANIFEST_PATH = "dbgap_variables_priority_cohorts_V2.csv"

# Output directory for results
OUTPUT_DIR = "audit_results"

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

def run_remote_audit(cohort_name, github_url, manifest_df):
    """Run remote audit to validate GitHub YAMLs against local manifest for a single cohort."""
    print("--- 🩺 Initializing Remote Mapping Audit ---")
    print(f"📍 Cohort: {cohort_name}\n")

    # Filter for the target study and clean accession columns
    auth_df = manifest_df[manifest_df['Study'].str.contains(cohort_name, na=False, case=False, regex=False)].copy()
    auth_df['pht_clean'] = auth_df['Dataset accession'].apply(clean_accession)
    auth_df['phv_clean'] = auth_df['Variable accession'].apply(clean_accession)

    print(f"✅ Loaded {len(auth_df):,} PHT-PHV mappings from manifest for {cohort_name}.")

    # 2. Fetch YAML list from GitHub
    api_url = parse_github_url(github_url)
    response = requests.get(api_url, timeout=30)
    if response.status_code != 200:
        print(f"❌ Failed to fetch GitHub contents: {response.status_code}")
        return

    files = response.json()
    yaml_files = [f for f in files if f['name'].endswith('.yaml')]
    print(f"📡 Found {len(yaml_files)} YAML files on GitHub. Starting Audit...\n")

    mismatches = []
    yaml_errors = []
    file_stats = []

    # 3. Process Remote YAMLs
    for yf in yaml_files:
        print(f"Processing: {yf['name']}...")
        file_violations = 0
        file_phts = set()
        file_phvs_checked = 0

        raw_resp = requests.get(yf['download_url'], timeout=30)
        try:
            config = yaml.safe_load(raw_resp.text)
        except yaml.YAMLError as e:
            error_msg = str(e)
            yaml_errors.append({
                'file': yf['name'],
                'error': error_msg
            })
            print(f"   ⚠️  [YAML ERROR] Skipping {yf['name']}: {error_msg.split(chr(10))[0]}...")
            # Add to file_stats with ERROR indicator
            file_stats.append({
                'file': yf['name'],
                'phts_used': 'ERROR',
                'phvs_checked': 'ERROR',
                'violations': 'PARSE_ERROR'
            })
            continue

        configs = config if isinstance(config, list) else [config]
        for item in configs:
            if not isinstance(item, dict):
                continue
            derivations = item.get('class_derivations', {})

            for _class_name, details in derivations.items():
                source_pht = clean_accession(details.get('populated_from'))
                if not source_pht:
                    continue

                file_phts.add(source_pht)
                # Filter manifest for this specific PHT
                authorized_phvs = auth_df[auth_df['pht_clean'] == source_pht]['phv_clean'].tolist()

                slots = details.get('slot_derivations', {})
                for slot_name, slot_details in slots.items():
                    phv_mapped = clean_accession(slot_details.get('populated_from'))

                    if phv_mapped.startswith('phv'):
                        file_phvs_checked += 1
                        # THE TEST: Is this PHV mapped to this PHT in the Master Manifest?
                        if phv_mapped not in authorized_phvs:
                            is_critical = "YES" if slot_name == "associated_participant" else "NO"
                            file_violations += 1

                            mismatches.append({
                                'CRITICAL': is_critical,
                                'Remote_YAML': yf['name'],
                                'PHT': source_pht,
                                'Slot': slot_name,
                                'Invalid_PHV': phv_mapped,
                                'Study_Context': cohort_name
                            })

                            status = "🚨 [CRITICAL]" if is_critical == "YES" else "❌ [ERROR]"
                            print(f"   {status} {slot_name}: {phv_mapped} is not authorized for {source_pht}")

        # Store statistics for this file
        file_stats.append({
            'file': yf['name'],
            'phts_used': len(file_phts),
            'phvs_checked': file_phvs_checked,
            'violations': file_violations
        })

    # 4. Final Reporting
    print("\n" + "="*80)
    print("AUDIT SUMMARY")
    print("="*80)

    # Manifest statistics
    total_phts = auth_df['pht_clean'].nunique()
    total_phvs = auth_df['phv_clean'].nunique()
    print(f"\n📊 Manifest Reference Database ({cohort_name}):")
    print(f"   - Unique PHTs (datasets): {total_phts:,}")
    print(f"   - Unique PHVs (variables): {total_phvs:,}")
    print(f"   - Total PHT-PHV mapping rows: {len(auth_df):,}")

    # Per-file statistics
    if file_stats:
        # Calculate totals, excluding files with errors
        total_phvs_checked = sum(s['phvs_checked'] for s in file_stats if isinstance(s['phvs_checked'], int))
        files_with_violations = len([s for s in file_stats if isinstance(s['violations'], int) and s['violations'] > 0])
        files_with_errors = len([s for s in file_stats if s['violations'] == 'PARSE_ERROR'])

        print("\n📂 YAML File Processing Summary:")
        print(f"   - Files processed: {len(file_stats)}")
        print(f"   - Files with parse errors: {files_with_errors}")
        print(f"   - Total PHVs checked across all files: {total_phvs_checked:,}")
        print(f"   - Files with violations: {files_with_violations}")

        print("\n📋 Per-File Breakdown:")
        print(f"   {'File':<35} {'PHTs':<6} {'PHVs':<8} {'Violations':<12}")
        print(f"   {'-'*35} {'-'*6} {'-'*8} {'-'*12}")
        for stat in file_stats:
            if stat['violations'] == 'PARSE_ERROR':
                status = "⚠️ "
                phts_display = "N/A"
                phvs_display = "N/A"
                viol_display = "PARSE_ERR"
            else:
                status = "❌" if stat['violations'] > 0 else "✅"
                phts_display = str(stat['phts_used'])
                phvs_display = str(stat['phvs_checked'])
                viol_display = str(stat['violations'])

            print(f"   {status} {stat['file']:<33} {phts_display:<6} {phvs_display:<8} {viol_display:<12}")

    if yaml_errors:
        print(f"\n⚠️  {len(yaml_errors)} YAML file(s) had parsing errors and were skipped:")
        for err in yaml_errors:
            print(f"   - {err['file']}")
            # Extract just the first line of error for summary
            error_line = err['error'].split('\n')[0] if '\n' in err['error'] else err['error']
            print(f"     Reason: {error_line}")

    if mismatches:
        # Create output filename from cohort name
        cohort_short = cohort_name.split()[0].replace('(', '').replace(')', '')
        output_file = os.path.join(OUTPUT_DIR, f"audit_results_{cohort_short}.csv")

        df_out = pd.DataFrame(mismatches).sort_values(by='CRITICAL', ascending=False)
        df_out.to_csv(output_file, index=False)
        critical_count = len([m for m in mismatches if m['CRITICAL'] == 'YES'])

        print(f"\n❌ {len(mismatches)} mapping violation(s) found:")
        print(f"   - {critical_count} CRITICAL violations (associated_participant field)")
        print(f"   - {len(mismatches) - critical_count} NON-CRITICAL violations (other fields)")

        print("\n🔍 Detailed Findings:")
        for i, m in enumerate(mismatches, 1):
            status = "🚨 CRITICAL" if m['CRITICAL'] == 'YES' else "❌ ERROR"
            print(f"   {i}. [{status}] {m['Remote_YAML']}")
            print(f"      PHT: {m['PHT']} | Slot: {m['Slot']} | Invalid PHV: {m['Invalid_PHV']}")

        print(f"\n📄 Full report saved to: {output_file}")
    else:
        print("\n✅ SUCCESS: All remote mappings are authorized by the Master Manifest.")


def main():
    """Run remote audit for all configured cohorts."""
    # Ensure proper encoding for console output
    import sys
    if sys.stdout.encoding != 'utf-8':
        import codecs
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("="*80)
    print("BDC REMOTE LOGIC AUDITOR - MULTI-COHORT RUN")
    print("="*80)
    print(f"\n🔍 Processing {len(COHORT_CONFIGS)} cohorts...\n")

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load the manifest once
    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ CRITICAL: Manifest file {MANIFEST_PATH} not found.")
        return

    manifest_df = pd.read_csv(MANIFEST_PATH)

    # Process each cohort
    for idx, (cohort_name, github_url) in enumerate(COHORT_CONFIGS.items(), 1):
        print("\n" + "="*80)
        print(f"COHORT {idx}/{len(COHORT_CONFIGS)}")
        print("="*80)

        try:
            run_remote_audit(cohort_name, github_url, manifest_df)
        except Exception as e:
            print(f"\n❌ ERROR processing {cohort_name}: {str(e)}")
            print("Continuing to next cohort...\n")

        # Add spacing between cohorts
        print("\n")

    print("="*80)
    print("✅ MULTI-COHORT AUDIT COMPLETE")
    print("="*80)
    print(f"\n📁 Results saved in: {OUTPUT_DIR}/")
    print(f"   {len(COHORT_CONFIGS)} cohort(s) processed\n")


if __name__ == "__main__":
    main()
