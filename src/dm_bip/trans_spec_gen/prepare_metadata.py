"""
Prepare metadata for trans-spec generation.

Ported from the Stata pipeline (steps 1-4) in RTIInternational/NHLBI-BDC-DMC-HV.
Takes raw dbGaP metadata exports and reference files, produces the curated CSV
that generate_trans_specs consumes.
"""

import csv
import logging
import re
from pathlib import Path

import pandas as pd

from dm_bip.trans_spec_gen.units import normalize_unit

logger = logging.getLogger(__name__)


# --- Step 1: Import documentation files ---


def _clean_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Clean whitespace and linebreaks in all string columns (mirrors Stata strtrim/stritrim)."""
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.replace(r"\n", " ", regex=True)
        df[col] = df[col].str.strip()
        df[col] = df[col].str.replace(r"\s+", " ", regex=True)
    return df


def load_bdchv_defs(path: Path) -> pd.DataFrame:
    """
    Load BDC harmonized variable definitions.

    Creates onto_id from obacurie/omop and merge_bdchm_label for joining.
    """
    df = pd.read_csv(path, dtype=str)
    df = _clean_whitespace(df)
    df = df.dropna(axis=1, how="all")

    df["onto_id"] = df["obacurie"].fillna("")
    df.loc[df["onto_id"] == "", "onto_id"] = df["omop"].fillna("")
    df = df.drop(columns=["omop", "obacurie"], errors="ignore")

    df["merge_bdchm_label"] = df["bdchm_varlabel"].str.lower().str.replace(" ", "", regex=False)
    df = df.sort_values("merge_bdchm_label")
    return df


def load_contextual_vars(path: Path) -> pd.DataFrame:
    """Load contextual variables key (visit/participant info by pht)."""
    df = pd.read_csv(path, dtype=str)
    df = _clean_whitespace(df)
    df = df.dropna(axis=1, how="all")

    df = df[df["pht"].notna() & (df["pht"] != "")]
    if "associatedvisit" in df.columns:
        df["associatedvisit"] = df["associatedvisit"].str.upper()
    if "datatablename" in df.columns:
        df = df.drop(columns=["datatablename"])
    if "notes" in df.columns:
        df = df.rename(columns={"notes": "contextvars_notes"})

    df = df.sort_values("pht")
    df = df.drop_duplicates()
    return df


def load_unit_conversions(path: Path) -> pd.DataFrame:
    """Load unit conversion rules from unit_key.xlsx conversions tab."""
    conversions = pd.read_excel(path, sheet_name="conversions", dtype=str)
    conversions = conversions[
        conversions["conversion_condition"].isna() | (conversions["conversion_condition"] == "")
    ].copy()
    conversions["unit_merge_key"] = conversions["this_unit"] + "_" + conversions["that_unit"]

    ucum = pd.read_excel(path, sheet_name="ucum", dtype=str)
    ucum_set = set(ucum["ucum_code"].dropna())

    conversions["source_unit_valid"] = conversions["this_unit"].isin(ucum_set).astype(int)
    conversions["target_unit_valid"] = conversions["that_unit"].isin(ucum_set).astype(int)
    conversions = conversions.rename(columns={"this_unit": "source_unit", "that_unit": "target_unit"})
    both_valid = (conversions["source_unit_valid"] == 1) & (conversions["target_unit_valid"] == 1)
    conversions["both_valid_ucums"] = both_valid.astype(int)
    conversions = conversions.drop(columns=["conversion_formula"], errors="ignore")
    return conversions


def load_unit_equivalencies(path: Path) -> pd.DataFrame:
    """Load unit equivalency rules from unit_key.xlsx equivalencies tab."""
    equiv = pd.read_excel(path, sheet_name="equivalencies", dtype=str)
    equiv = equiv[equiv["equivalency_always"] == "1"].copy()
    equiv["unit_merge_key"] = equiv["this_unit"] + "_" + equiv["that_unit"]
    equiv = equiv[["unit_merge_key"]].drop_duplicates()
    equiv["equivalent_units"] = 1
    return equiv


# --- Step 2: Import raw data ---


def load_raw_data(raw_files: list[Path]) -> pd.DataFrame:
    """Load and combine raw metadata from multiple Excel files."""
    frames = []
    for path in raw_files:
        df = pd.read_excel(path, dtype=str)
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df = _clean_whitespace(df)
        df = df.dropna(axis=1, how="all")
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates()
    return df


def standardize_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize the combined raw data (step 2, section 5 of Stata).

    Splits accession IDs, lowercases values, normalizes units.
    """
    # Drop bdchm_variable if present (redundant)
    df = df.drop(columns=["bdchm_variable"], errors="ignore")

    # Split accession IDs (e.g. "phv00098579.v1.p1" → "phv00098579")
    for col, prefix in [("var_id", "phv"), ("study_id", "phs"), ("data_table_id", "pht")]:
        if col in df.columns:
            df[prefix] = df[col].str.split(".").str[0]
            df = df.drop(columns=[c for c in df.columns if c.startswith(col)], errors="ignore")

    df = df[df["phv"].notna() & (df["phv"] != "")]

    # Lowercase values
    for col in ["cohort", "var_units", "var_desc"]:
        if col in df.columns:
            df[col] = df[col].str.lower()
    if "bdchm_label" in df.columns:
        df["bdchm_label"] = df["bdchm_label"].str.lower()

    # Cohort name fix
    if "cohort" in df.columns:
        df["cohort"] = df["cohort"].str.replace("hchs/sol", "hchs_sol", regex=False)

    # Normalize units
    if "var_units" in df.columns:
        df["var_units"] = df["var_units"].fillna("").apply(normalize_unit)

    # Determine categorical type from enum/example columns
    enum_cols = [c for c in df.columns if c.startswith("enum_")]
    example_cols = [c for c in df.columns if c.startswith("example_")]
    if enum_cols or example_cols:
        has_enum = df[enum_cols].notna().any(axis=1) if enum_cols else False
        has_example = df[example_cols].fillna("").ne("").any(axis=1) if example_cols else False
        if "var_type" in df.columns:
            df.loc[has_enum | has_example, "var_type"] = "categorical"

    return df


# --- Step 3: Clean data ---


def clean_data(df: pd.DataFrame, fixes_file: Path | None = None) -> pd.DataFrame:
    """
    Clean data: exclude bad rows, fix labels, fix units, merge curator fixes.

    Faithful translation of DMCYAML_03_CleanData.do.
    """
    # ----- 1. Exclude rows/variables -----
    if "bdchm_label" in df.columns:
        df = df[df["bdchm_label"] != "medication adherence"].copy()

    # Drop bad mappings based on transform_comment
    if "transform_comment" in df.columns:
        df["transform_comment"] = df["transform_comment"].fillna("").str.lower()
        drop_mask = (
            df["transform_comment"].isin(["bad phv map", "not going to include", "phv doesn't exist"])
            | df["transform_comment"].str.contains("out of scope", na=False)
            | df["transform_comment"].str.contains("not a measurement", na=False)
        )
        df = df[~drop_mask].copy()

    # ----- 2. Correct BDCHM variable mappings (spot-fixes) -----
    if "bdchm_label" in df.columns:
        label_fixes = {
            "stroke status": "stroke",
            "copd status": "copd",
            "sleep apnea status": "sleep apnea",
            "alcohol consumption": "alcohol servings",
            "fruit consumption": "fruit servings",
            "vegetable consumption": "vegetable servings",
        }
        df["bdchm_label"] = df["bdchm_label"].replace(label_fixes)

        # Time indicator detection: clear label if time measurement mapped to non-time BDCHV
        if "var_desc" in df.columns:
            time_pattern = r"^days |days since| date$|^date |visit year|^age|age at|\(days\)|follow up days|\(years\)"
            time_mask = df["var_desc"].fillna("").str.contains(time_pattern, flags=re.IGNORECASE, na=False)
            allowed_time_labels = {"death", "age at follow-up"}
            df.loc[time_mask & ~df["bdchm_label"].isin(allowed_time_labels), "bdchm_label"] = ""
            df.loc[df["var_desc"] == "visit type", "bdchm_label"] = ""

            # Blood pressure diastolic/systolic disambiguation
            diastolic = df["var_desc"].str.contains("diastolic", case=False, na=False)
            systolic = df["var_desc"].str.contains("systolic", case=False, na=False)
            bp = df["bdchm_label"].str.contains("blood pressure", na=False)
            df.loc[bp & diastolic, "bdchm_label"] = "diastolic blood pressure"
            df.loc[bp & systolic, "bdchm_label"] = "systolic blood pressure"

    # ----- 3. Correct units (spot-fixes) -----
    if "var_desc" in df.columns and "var_units" in df.columns and "bdchm_label" in df.columns:
        servday = df["var_desc"].str.contains(r"serv/day|daily|per day", case=False, na=False)
        servweek = df["var_desc"].str.contains(r"per week|weekly|serv/week", case=False, na=False)
        serving_labels = {"alcohol servings", "fruit servings", "vegetable servings"}
        serving_mask = df["bdchm_label"].isin(serving_labels)
        empty_or_servings = df["var_units"].isin(["", "{servings}"])

        df.loc[servday & serving_mask & empty_or_servings, "var_units"] = "{#}/d"
        df.loc[servweek & serving_mask & empty_or_servings, "var_units"] = "{#}/wk"

        hrs = df["var_desc"].str.contains(r"how many hours|number of hours|hours", case=False, na=False)
        df.loc[hrs & (df["bdchm_label"] == "sleep hours") & (df["var_units"] == ""), "var_units"] = "h"

        kgm2 = df["var_desc"].str.contains(r"kg/m2", case=False, na=False)
        df.loc[kgm2 & (df["var_units"] == ""), "var_units"] = "kg/m2"

    # ----- 4. Merge in curator fixes -----
    if fixes_file and fixes_file.exists():
        fixes = pd.read_csv(fixes_file, dtype=str)
        if "phv" in fixes.columns and "bdchm_label" in fixes.columns:
            fixes["pair_id"] = fixes["phv"] + "|" + fixes["bdchm_label"]
            df["pair_id"] = df["phv"] + "|" + df["bdchm_label"]
            fix_cols = ["pair_id"] + [c for c in ["var_units_fixed", "bad_map"] if c in fixes.columns]
            df = df.merge(fixes[fix_cols].drop_duplicates(), on="pair_id", how="left")
            if "var_units_fixed" in df.columns:
                mask = df["var_units_fixed"].notna() & (df["var_units_fixed"] != "")
                df.loc[mask, "var_units"] = df.loc[mask, "var_units_fixed"]
                df = df.drop(columns=["var_units_fixed"])
            if "bad_map" in df.columns:
                df.loc[df["bad_map"] == "1", "bdchm_label"] = ""
                df = df.drop(columns=["bad_map"])
            df = df.drop(columns=["pair_id"])

    # ----- 5. Final cleanup -----
    df = df.drop_duplicates()
    df = df[df["phv"].notna() & (df["phv"] != "")]
    if "bdchm_label" in df.columns:
        df = df[df["bdchm_label"].notna() & (df["bdchm_label"] != "")]
        df["merge_bdchm_label"] = df["bdchm_label"].str.replace(" ", "", regex=False)

    return df


# --- Step 4: Merge data and documentation ---


def merge_data_docs(
    df: pd.DataFrame,
    bdchv_defs: pd.DataFrame,
    conversions: pd.DataFrame,
    equivalencies: pd.DataFrame,
    contextual_vars: pd.DataFrame,
    fixes_file: Path | None = None,
) -> pd.DataFrame:
    """
    Merge data with documentation files and compute quality flags.

    Faithful translation of DMCYAML_04_MergeDataDocs.do.
    """
    # Merge BDCHM definitions
    df = df.merge(bdchv_defs, on="merge_bdchm_label", how="left", suffixes=("", "_defs"))
    # Apply fixed values if present
    for col in ["bdchm_varname", "bdchm_unit"]:
        fixed_col = f"{col}_fixed"
        if fixed_col in df.columns:
            mask = df[fixed_col].notna() & (df[fixed_col] != "")
            df.loc[mask, col] = df.loc[mask, fixed_col]
            df = df.drop(columns=[fixed_col])

    # Merge unit conversions
    df["unit_merge_key"] = df["var_units"].fillna("") + "_" + df["bdchm_unit"].fillna("")
    conv_cols = [
        "unit_merge_key",
        "source_unit",
        "target_unit",
        "conversion_rule",
        "source_unit_valid",
        "target_unit_valid",
        "both_valid_ucums",
    ]
    conv_cols = [c for c in conv_cols if c in conversions.columns]
    df = df.merge(conversions[conv_cols].drop_duplicates(), on="unit_merge_key", how="left", suffixes=("", "_conv"))

    # Merge unit equivalencies
    df = df.merge(equivalencies, on="unit_merge_key", how="left", suffixes=("", "_equiv"))

    # Merge contextual variables by pht (Stata merges on pht only, not cohort)
    df = df.merge(contextual_vars, on="pht", how="left", suffixes=("", "_ctx"))

    # Track which rows matched on pht merge (participantidphv comes from contextual_vars)
    if "participantidphv" in df.columns:
        has_pht_merge = df["participantidphv"].notna()
    else:
        has_pht_merge = pd.Series(False, index=df.index)

    # Apply curator overrides for specific fields (Stata merges fixed_bdchm_mappings in step 4)
    if fixes_file and fixes_file.exists():
        fixes = pd.read_csv(fixes_file, dtype=str)
        if "phv" in fixes.columns and "bdchm_label" in fixes.columns:
            override_cols = [
                "participantidphv",
                "associatedvisit",
                "associatedvisit_expr",
                "ageinyearsphv",
                "conversion_rule",
                "unit_expr_custom",
                "unit_casestmt_custom",
            ]
            present_cols = [col for col in override_cols if col in fixes.columns]
            if present_cols:
                fixes["pair_id"] = fixes["phv"] + "|" + fixes["bdchm_label"]
                df["pair_id"] = df["phv"].fillna("") + "|" + df["bdchm_label"].fillna("")
                rename_map = {col: f"{col}_fixed" for col in present_cols}
                fixes_subset = fixes[["pair_id"] + present_cols].copy()
                fixes_subset = fixes_subset.rename(columns=rename_map).drop_duplicates()
                df = df.merge(fixes_subset, on="pair_id", how="left")
                for col in present_cols:
                    fixed_col = f"{col}_fixed"
                    if fixed_col in df.columns:
                        mask = df[fixed_col].notna() & (df[fixed_col] != "")
                        if col not in df.columns:
                            df[col] = ""
                        df.loc[mask, col] = df.loc[mask, fixed_col]
                        df = df.drop(columns=[fixed_col])
                df = df.drop(columns=["pair_id"])

    # Drop rows where table no longer exists in dbgap
    if "drop_table" in df.columns:
        df = df[df["drop_table"] != "1"]
        df = df.drop(columns=["drop_table"])

    # ----- Hardcoded conversion spot-fixes -----
    if all(c in df.columns for c in ["var_units", "bdchm_unit", "bdchm_label", "conversion_rule"]):
        df["conversion_rule"] = df["conversion_rule"].fillna("")
        # Cholesterol: mmol/L to mg/dL
        cholesterol_labels = ["hdl", "total cholesterol in blood"]
        mask = (
            (df["var_units"] == "mmol/L") & (df["bdchm_unit"] == "mg/dL") & df["bdchm_label"].isin(cholesterol_labels)
        )
        df.loc[mask, "conversion_rule"] = "* 38.67"
        # Factor VIII: % to IU/mL
        mask = (df["var_units"] == "%") & (df["bdchm_unit"] == "[IU]/mL") & (df["bdchm_label"] == "factor viii")
        df.loc[mask, "conversion_rule"] = "* 0.01"

    # Hardcoded equivalency spot-fixes
    if "equivalent_units" in df.columns and all(c in df.columns for c in ["var_units", "bdchm_unit", "bdchm_label"]):
        df["equivalent_units"] = df["equivalent_units"].fillna(0)
        # MCHC: % is equivalent to g/dL
        mask = (
            (df["var_units"] == "%")
            & (df["bdchm_unit"] == "g/dL")
            & (df["bdchm_label"] == "mean corpuscular hemoglobin concentration")
        )
        df.loc[mask, "equivalent_units"] = 1
        # Sodium: meq/L is equivalent to mmol/L
        mask = (df["bdchm_label"] == "sodium in blood") & (df["var_units"] == "meq/L") & (df["bdchm_unit"] == "mmol/L")
        df.loc[mask, "equivalent_units"] = 1

    # Manual conversion rule from curator fixes
    if fixes_file and fixes_file.exists() and "unit_expr_custom" in df.columns:
        mask = df["unit_expr_custom"].notna() & (df["unit_expr_custom"] != "")
        if "conversion_rule" in df.columns:
            df.loc[mask, "conversion_rule"] = df.loc[mask, "unit_expr_custom"]

    # ----- Compute quality flags -----
    df["has_pht"] = has_pht_merge.astype(int)
    df["has_onto"] = (df["onto_id"].fillna("") != "").astype(int)

    df["unit_match"] = 0
    if "var_units" in df.columns and "bdchm_unit" in df.columns:
        exact_match = (df["var_units"] == df["bdchm_unit"]) & (df["var_units"] != "")
        equiv_match = df["equivalent_units"].fillna(0).astype(int) == 1 if "equivalent_units" in df.columns else False
        df["unit_match"] = (exact_match | equiv_match).astype(int)

    df["unit_convert"] = 0
    if "both_valid_ucums" in df.columns:
        df["unit_convert"] = ((df["unit_match"] != 1) & (df["both_valid_ucums"].fillna(0).astype(int) == 1)).astype(int)

    df["unit_expr"] = 0
    df.loc[
        (df["unit_match"] != 1)
        & (df.get("both_valid_ucums", pd.Series(0, index=df.index)).fillna(0).astype(int) != 1)
        & (df["conversion_rule"].fillna("") != ""),
        "unit_expr",
    ] = 1

    df["unit_casestmt"] = 0
    if "unit_casestmt_custom" in df.columns:
        df.loc[df["unit_casestmt_custom"].fillna("") != "", "unit_casestmt"] = 1

    # Visit flags
    if "associatedvisit" in df.columns:
        df["has_visit"] = (df["associatedvisit"].fillna("").str.strip() != "").astype(int)
    else:
        df["has_visit"] = 0
    if "associatedvisit_expr" in df.columns:
        # Clear expr if direct visit exists
        has_both = (df["has_visit"] == 1) & (df["associatedvisit_expr"].fillna("").str.strip() != "")
        df.loc[has_both, "associatedvisit_expr"] = ""
        df["has_visit_expr"] = (df["associatedvisit_expr"].fillna("").str.strip() != "").astype(int)
    else:
        df["has_visit_expr"] = 0

    # Exam descriptor from var_desc
    if "var_desc" in df.columns:
        df["var_desc_exam"] = df["var_desc"].str.extract(r"(exam\s+\d+)", flags=re.IGNORECASE)[0]
    else:
        df["var_desc_exam"] = ""

    # Age flag
    if "ageinyearsphv" in df.columns:
        df["has_age"] = (df["ageinyearsphv"].fillna("").str.strip() != "").astype(int)
    else:
        df["has_age"] = 0

    # Row quality: good if has pht, has ontology, and has some unit handling
    df["row_good"] = 0
    unit_ok = (df["unit_match"] == 1) | (df["unit_convert"] == 1) | (df["unit_expr"] == 1) | (df["unit_casestmt"] == 1)
    df.loc[(df["has_pht"] == 1) & (df["has_onto"] == 1) & unit_ok, "row_good"] = 1

    # ----- Output: keep only relevant columns, MeasurementObservation only -----
    output_cols = [
        "row_good",
        "cohort",
        "bdchm_entity",
        "bdchm_label",
        "bdchm_varname",
        "has_onto",
        "onto_id",
        "bdchm_unit",
        "phv",
        "var_desc",
        "var_units",
        "has_pht",
        "pht",
        "participantidphv",
        "has_visit",
        "associatedvisit",
        "has_visit_expr",
        "associatedvisit_expr",
        "xassociatedvisit",
        "var_desc_exam",
        "has_age",
        "ageinyearsphv",
        "contextvars_notes",
        "unit_match",
        "unit_convert",
        "unit_expr",
        "conversion_rule",
        "unit_casestmt",
        "unit_casestmt_custom",
        "source_unit",
        "target_unit",
    ]
    # Keep only columns that exist
    output_cols = [c for c in output_cols if c in df.columns]
    df = df[output_cols]
    df = df.drop_duplicates()

    if "bdchm_entity" in df.columns:
        df = df[df["bdchm_entity"] == "MeasurementObservation"]

    return df


# --- Full pipeline ---


def prepare_metadata(
    raw_files: list[Path],
    bdchv_defs_path: Path,
    contextual_vars_path: Path,
    unit_key_path: Path,
    output_path: Path,
    fixes_file: Path | None = None,
) -> Path | None:
    """
    Run the full metadata preparation pipeline.

    Args:
        raw_files: Paths to raw metadata Excel files.
        bdchv_defs_path: Path to bdchv_defs.csv.
        contextual_vars_path: Path to contextual_variables_key.csv.
        unit_key_path: Path to unit_key.xlsx.
        output_path: Path for the output CSV.
        fixes_file: Optional path to curator fixes CSV.

    Returns:
        Path to the written output CSV, or None if no data was loaded.

    """
    logger.info("Loading documentation files...")
    bdchv_defs = load_bdchv_defs(bdchv_defs_path)
    contextual_vars = load_contextual_vars(contextual_vars_path)
    conversions = load_unit_conversions(unit_key_path)
    equivalencies = load_unit_equivalencies(unit_key_path)

    logger.info("Loading raw data from %d file(s)...", len(raw_files))
    df = load_raw_data(raw_files)
    if df.empty:
        logger.warning("No data loaded from raw files")
        return None

    logger.info("Standardizing raw data...")
    df = standardize_raw_data(df)

    logger.info("Cleaning data...")
    df = clean_data(df, fixes_file)

    logger.info("Merging with documentation...")
    df = merge_data_docs(df, bdchv_defs, conversions, equivalencies, contextual_vars, fixes_file)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    logger.info("Wrote %d rows to %s", len(df), output_path)
    return output_path
