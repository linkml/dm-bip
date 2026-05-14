"""
Prepare metadata for trans-spec generation.

Mechanical pipeline: load raw dbGaP exports, normalize columns, apply
curator-maintained cleanup rules, join with reference tables, compute
quality flags, emit the curated CSV that generate_trans_specs consumes.

Curator decisions live outside this module:

- Pre-pipeline cleanups (label aliases, label/unit inference, row drops)
  come from a CSV consumed by ``cleanup_rules.apply_cleanup_rules``.
- Reference-data overrides (label-keyed conversion/equivalency rules)
  live under ``trans_spec_gen/data/`` and join in mechanically.
- Per-row curator overrides (visit, age, custom conversion rules,
  ``bad_map``) are applied post-pipeline by ``apply_overrides``.
"""

import csv
import logging
import re
from pathlib import Path

import pandas as pd

from dm_bip.trans_spec_gen.cleanup_rules import apply_cleanup_rules, load_cleanup_rules
from dm_bip.trans_spec_gen.units import normalize_unit

logger = logging.getLogger(__name__)


REFERENCE_DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CONVERSION_OVERRIDES = REFERENCE_DATA_DIR / "conversion_overrides.csv"
DEFAULT_EQUIVALENCY_OVERRIDES = REFERENCE_DATA_DIR / "equivalency_overrides.csv"


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


def load_unit_conversions(
    path: Path,
    conversions_sheet: str = "conversions",
    ucum_sheet: str = "ucum",
) -> pd.DataFrame:
    """Load unit conversion rules from unit_key.xlsx conversions tab."""
    conversions = pd.read_excel(path, sheet_name=conversions_sheet, dtype=str)
    conversions = conversions[
        conversions["conversion_condition"].isna() | (conversions["conversion_condition"] == "")
    ].copy()
    conversions["unit_merge_key"] = conversions["this_unit"] + "_" + conversions["that_unit"]

    ucum = pd.read_excel(path, sheet_name=ucum_sheet, dtype=str)
    ucum_set = set(ucum["ucum_code"].dropna())

    conversions["source_unit_valid"] = conversions["this_unit"].isin(ucum_set).astype(int)
    conversions["target_unit_valid"] = conversions["that_unit"].isin(ucum_set).astype(int)
    conversions = conversions.rename(columns={"this_unit": "source_unit", "that_unit": "target_unit"})
    both_valid = (conversions["source_unit_valid"] == 1) & (conversions["target_unit_valid"] == 1)
    conversions["both_valid_ucums"] = both_valid.astype(int)
    conversions = conversions.drop(columns=["conversion_formula"], errors="ignore")
    return conversions


def load_unit_equivalencies(
    path: Path,
    equivalencies_sheet: str = "equivalencies",
) -> pd.DataFrame:
    """Load unit equivalency rules from unit_key.xlsx equivalencies tab."""
    equiv = pd.read_excel(path, sheet_name=equivalencies_sheet, dtype=str)
    equiv = equiv[equiv["equivalency_always"] == "1"].copy()
    equiv["unit_merge_key"] = equiv["this_unit"] + "_" + equiv["that_unit"]
    equiv = equiv[["unit_merge_key"]].drop_duplicates()
    equiv["equivalent_units"] = 1
    return equiv


_CONVERSION_OVERRIDE_COLUMNS = {"bdchm_label", "var_units", "bdchm_unit", "conversion_rule"}
_EQUIVALENCY_OVERRIDE_COLUMNS = {"bdchm_label", "var_units", "bdchm_unit"}


def load_conversion_overrides(path: Path = DEFAULT_CONVERSION_OVERRIDES) -> pd.DataFrame:
    """
    Load label-keyed conversion overrides.

    Columns: bdchm_label, var_units, bdchm_unit, conversion_rule.
    """
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = _CONVERSION_OVERRIDE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"conversion overrides CSV {path} missing required columns: {sorted(missing)}")
    return df


def load_equivalency_overrides(path: Path = DEFAULT_EQUIVALENCY_OVERRIDES) -> pd.DataFrame:
    """
    Load label-keyed equivalency overrides.

    Columns: bdchm_label, var_units, bdchm_unit. Presence implies equivalent_units=1.
    """
    df = pd.read_csv(path, dtype=str).fillna("")
    missing = _EQUIVALENCY_OVERRIDE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"equivalency overrides CSV {path} missing required columns: {sorted(missing)}")
    return df


# --- Step 2: Import raw data ---

# Column rename mappings from real Excel formats to the standardized names
# the pipeline expects. Derived from the Stata ImportData step.
_COLUMN_RENAMES = {
    # FHS format (data_table.* prefix)
    "data_table.study_id": "study_id",
    "data_table.dataset_id": "data_table_id",
    "data_table.variable.id": "var_id",
    "data_table.variable.description": "var_desc",
    "data_table.variable.units": "var_units",
    "data_table.variable.calculated_type": "var_type",
    "data_table.variable.comment": "var_comment",
    "data_table.name": "data_table_name",
    "data_table.description": "data_table_descr",
    "data_table.study_name": "cohort_long",
    # Non-FHS format (var_report.* prefix)
    "var_report.study_id": "study_id",
    "var_report.dataset_id": "data_table_id",
    "var_report.variable.id": "var_id",
    "var_report.variable.description": "var_desc",
    "var_report.variable.units": "var_units",
    "var_report.variable.calculated_type": "var_type",
    "var_report.variable.comment": "var_comment",
    "var_report.name": "data_table_name",
    "var_report.description": "data_table_descr",
    "var_report.study_name": "cohort_long",
    # Common columns across formats
    "bdchm_label": "bdchm_label",
    "bdchm_variable": "bdchm_variable",
    "source_variable_name": "var_name",
    "source_variable_description": "var_desc",
    "note": "curator_note",
    "notes": "curator_note",
    "transform_comment": "transform_comment",
    "topmed_harmonized_variable": "topmed_varname",
    "bdchm_label_(corrected)": "bdchm_label_corrected",
    # FHS-specific alternate accession columns
    "dbgap_study_accession": "dbgap_study_accession",
    "dataset_accession": "dataset_accession",
    "variable_accession": "variable_accession",
    # Non-FHS bracketed columns
    "first[data_table.study_id]": "first_study_id",
    "first[data_table.dataset_id]": "first_dataset_id",
    "first[data_table.variable.id]": "first_variable_id",
    "vlookupresults": "vlookup_results",
    # Stats/enum columns get passed through with prefix normalization
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names from real Excel formats to standardized names."""
    # Lowercase all column names first
    df.columns = [c.lower().strip() for c in df.columns]

    # Apply known renames
    rename_map = {}
    for col in df.columns:
        if col in _COLUMN_RENAMES:
            rename_map[col] = _COLUMN_RENAMES[col]
        else:
            # Normalize remaining columns: replace spaces/dots with underscores
            rename_map[col] = col.replace(".", "_").replace(" ", "_")
    df = df.rename(columns=rename_map)

    # Detect FHS format: has variable_accession but no cohort column
    if "variable_accession" in df.columns and "cohort" not in df.columns:
        df["cohort"] = "fhs"

    # FHS backfill: use alternate accession columns when primary is empty
    for target, source in [
        ("study_id", "dbgap_study_accession"),
        ("var_id", "variable_accession"),
        ("data_table_id", "dataset_accession"),
    ]:
        if target in df.columns and source in df.columns:
            df[target] = df[target].fillna(df[source])
        elif source in df.columns and target not in df.columns:
            df[target] = df[source]

    # Non-FHS: apply corrected label if present
    if "bdchm_label_corrected" in df.columns and "bdchm_label" in df.columns:
        mask = df["bdchm_label_corrected"].notna() & (df["bdchm_label_corrected"] != "")
        df.loc[mask, "bdchm_label"] = df.loc[mask, "bdchm_label_corrected"]

    return df


# Default sheet names from the Stata pipeline source formats. Callers can supply
# alternates via load_raw_data(known_sheets=...).
DEFAULT_KNOWN_SHEETS = ["right_join_full", "Export_BDCHM_noFHS-noCOPDGene_p"]


def load_raw_data(raw_files: list[Path], known_sheets: list[str] | None = None) -> pd.DataFrame:
    """
    Load and combine raw metadata from multiple Excel files.

    Args:
        raw_files: Paths to raw metadata Excel files.
        known_sheets: Sheet names to look for in each file, in priority order. If none
            of the listed names is present, falls back to the first sheet. Defaults to
            DEFAULT_KNOWN_SHEETS.

    """
    sheet_candidates = DEFAULT_KNOWN_SHEETS if known_sheets is None else known_sheets
    frames = []
    for path in raw_files:
        # Try known sheet names first, fall back to first sheet
        sheet = 0
        xl = pd.ExcelFile(path)
        for known in sheet_candidates:
            if known in xl.sheet_names:
                sheet = known
                break
        df = pd.read_excel(xl, sheet_name=sheet, dtype=str)
        df = _clean_whitespace(df)
        df = df.dropna(axis=1, how="all")
        df = _normalize_columns(df)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates()
    return df


def standardize_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize the combined raw data.

    Splits accession IDs, lowercases values, normalizes units. Mechanical
    only — no editorial corrections.
    """
    # Drop bdchm_variable if present (redundant)
    df = df.drop(columns=["bdchm_variable"], errors="ignore")

    # Split accession IDs (e.g. "phv00098579.v1.p1" → "phv00098579")
    for col, prefix in [("var_id", "phv"), ("study_id", "phs"), ("data_table_id", "pht")]:
        if col in df.columns:
            df[prefix] = df[col].str.split(".").str[0]
            df = df.drop(columns=[c for c in df.columns if c.startswith(col)], errors="ignore")

    df = df[df["phv"].notna() & (df["phv"] != "")]

    # Lowercase free-text columns used as join keys or filter values
    for col in ["cohort", "var_units", "var_desc", "transform_comment"]:
        if col in df.columns:
            df[col] = df[col].str.lower()
    if "bdchm_label" in df.columns:
        df["bdchm_label"] = df["bdchm_label"].str.lower()

    # Normalize units via the canonical UCUM lookup
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


# --- Step 3: Final shape after curator cleanup ---


def finalize_cleaned_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows with empty join keys, deduplicate, build the merge_bdchm_label join key.

    Runs after curator cleanup rules have been applied.
    """
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
    conversion_overrides: pd.DataFrame | None = None,
    equivalency_overrides: pd.DataFrame | None = None,
    entity_filter: str | None = "MeasurementObservation",
) -> pd.DataFrame:
    """
    Merge data with reference tables and compute quality flags.

    Mechanical only — joins reference data, applies label-keyed
    overrides, computes derived flags. No editorial logic.

    Args:
        df: Cleaned data rows from finalize_cleaned_data.
        bdchv_defs: BDC harmonized variable definitions (from load_bdchv_defs).
        conversions: Unit conversion table (from load_unit_conversions).
        equivalencies: Unit equivalency table (from load_unit_equivalencies).
        contextual_vars: Contextual variables key (from load_contextual_vars).
        conversion_overrides: Label-keyed conversion rules (from load_conversion_overrides).
        equivalency_overrides: Label-keyed equivalency rules (from load_equivalency_overrides).
        entity_filter: Restrict the output to rows whose bdchm_entity matches.
            Pass None to keep all entity types. Defaults to "MeasurementObservation".

    """
    df = df.merge(bdchv_defs, on="merge_bdchm_label", how="left", suffixes=("", "_defs"))

    # Unit conversion lookup keyed on (var_units, bdchm_unit)
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

    df = df.merge(equivalencies, on="unit_merge_key", how="left", suffixes=("", "_equiv"))

    # Apply label-keyed overrides for unit conversions/equivalencies that the
    # generic unit-pair lookup can't express on its own.
    if conversion_overrides is not None and not conversion_overrides.empty:
        df = _apply_conversion_overrides(df, conversion_overrides)
    if equivalency_overrides is not None and not equivalency_overrides.empty:
        df = _apply_equivalency_overrides(df, equivalency_overrides)

    df = df.merge(contextual_vars, on="pht", how="left", suffixes=("", "_ctx"))

    # Track which rows matched on pht merge (participantidphv comes from contextual_vars)
    if "participantidphv" in df.columns:
        has_pht_merge = df["participantidphv"].notna()
    else:
        has_pht_merge = pd.Series(False, index=df.index)

    # Drop rows where table no longer exists in dbgap
    if "drop_table" in df.columns:
        df = df[df["drop_table"] != "1"]
        df = df.drop(columns=["drop_table"])
        has_pht_merge = has_pht_merge.loc[df.index]

    df = compute_quality_flags(df, has_pht_merge=has_pht_merge)

    # ----- Output: keep only relevant columns -----
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
        # Internal lookup state surfaced so apply_curator_overrides can
        # recompute quality flags without re-loading reference data.
        "equivalent_units",
        "both_valid_ucums",
    ]
    for col in ("equivalent_units", "both_valid_ucums"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    output_cols = [c for c in output_cols if c in df.columns]
    df = df[output_cols]
    df = df.drop_duplicates()

    if entity_filter is not None and "bdchm_entity" in df.columns:
        df = df[df["bdchm_entity"] == entity_filter]

    return df


def _apply_conversion_overrides(df: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Set conversion_rule from a (bdchm_label, var_units, bdchm_unit) lookup."""
    if "conversion_rule" not in df.columns:
        df["conversion_rule"] = ""
    df["conversion_rule"] = df["conversion_rule"].fillna("")
    keyed = overrides.set_index(["bdchm_label", "var_units", "bdchm_unit"])["conversion_rule"]
    triple = df.set_index(["bdchm_label", "var_units", "bdchm_unit"]).index
    matches = triple.map(keyed.to_dict()).to_series(index=df.index)
    mask = matches.notna()
    df.loc[mask, "conversion_rule"] = matches[mask]
    return df


def _apply_equivalency_overrides(df: pd.DataFrame, overrides: pd.DataFrame) -> pd.DataFrame:
    """Force equivalent_units=1 for any (bdchm_label, var_units, bdchm_unit) listed."""
    if "equivalent_units" not in df.columns:
        df["equivalent_units"] = 0
    df["equivalent_units"] = df["equivalent_units"].fillna(0)
    keyed = set(zip(overrides["bdchm_label"], overrides["var_units"], overrides["bdchm_unit"], strict=False))
    triples = list(zip(df["bdchm_label"], df["var_units"], df["bdchm_unit"], strict=False))
    mask = pd.Series([t in keyed for t in triples], index=df.index)
    df.loc[mask, "equivalent_units"] = 1
    return df


# --- Step 5: Quality flag computation ---


def compute_quality_flags(df: pd.DataFrame, has_pht_merge: pd.Series | None = None) -> pd.DataFrame:
    """
    Compute derived quality/structural flags.

    has_pht, has_onto, unit_match, unit_convert, unit_expr, unit_casestmt,
    has_visit, has_visit_expr, has_age, var_desc_exam, row_good.

    Args:
        df: DataFrame after reference data has been joined in.
        has_pht_merge: Optional pre-computed pht-match mask. If None, derived
            from participantidphv presence. Pass-through is needed because
            apply_curator_overrides may overwrite participantidphv after the
            initial join.

    """
    df = df.copy()

    if has_pht_merge is None:
        if "participantidphv" in df.columns:
            has_pht_merge = df["participantidphv"].fillna("").astype(str).str.strip() != ""
        else:
            has_pht_merge = pd.Series(False, index=df.index)

    df["has_pht"] = has_pht_merge.astype(int)
    df["has_onto"] = (df["onto_id"].fillna("") != "").astype(int) if "onto_id" in df.columns else 0

    df["unit_match"] = 0
    if "var_units" in df.columns and "bdchm_unit" in df.columns:
        exact_match = (df["var_units"] == df["bdchm_unit"]) & (df["var_units"] != "")
        equiv_match = df["equivalent_units"].fillna(0).astype(int) == 1 if "equivalent_units" in df.columns else False
        df["unit_match"] = (exact_match | equiv_match).astype(int)

    df["unit_convert"] = 0
    if "both_valid_ucums" in df.columns:
        df["unit_convert"] = ((df["unit_match"] != 1) & (df["both_valid_ucums"].fillna(0).astype(int) == 1)).astype(int)

    df["unit_expr"] = 0
    if "conversion_rule" in df.columns:
        df.loc[
            (df["unit_match"] != 1)
            & (df.get("both_valid_ucums", pd.Series(0, index=df.index)).fillna(0).astype(int) != 1)
            & (df["conversion_rule"].fillna("") != ""),
            "unit_expr",
        ] = 1

    df["unit_casestmt"] = 0
    if "unit_casestmt_custom" in df.columns:
        df.loc[df["unit_casestmt_custom"].fillna("") != "", "unit_casestmt"] = 1

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

    if "var_desc" in df.columns:
        df["var_desc_exam"] = df["var_desc"].str.extract(r"(exam\s+\d+)", flags=re.IGNORECASE)[0]
    else:
        df["var_desc_exam"] = ""

    if "ageinyearsphv" in df.columns:
        df["has_age"] = (df["ageinyearsphv"].fillna("").str.strip() != "").astype(int)
    else:
        df["has_age"] = 0

    df["row_good"] = 0
    unit_ok = (df["unit_match"] == 1) | (df["unit_convert"] == 1) | (df["unit_expr"] == 1) | (df["unit_casestmt"] == 1)
    df.loc[(df["has_pht"] == 1) & (df["has_onto"] == 1) & unit_ok, "row_good"] = 1

    return df


# --- Full pipeline ---


def prepare_metadata(
    raw_files: list[Path],
    bdchv_defs_path: Path,
    contextual_vars_path: Path,
    unit_key_path: Path,
    output_path: Path,
    cleanup_rules_path: Path | None = None,
    conversion_overrides_path: Path | None = DEFAULT_CONVERSION_OVERRIDES,
    equivalency_overrides_path: Path | None = DEFAULT_EQUIVALENCY_OVERRIDES,
    known_sheets: list[str] | None = None,
    entity_filter: str | None = "MeasurementObservation",
) -> Path | None:
    """
    Run the full mechanical metadata preparation pipeline.

    Curator decisions enter through cleanup_rules (pre-pipeline) and the
    label-keyed override tables (reference data). Per-row curator fixes
    happen post-pipeline via apply_curator_overrides.

    Args:
        raw_files: Paths to raw metadata Excel files.
        bdchv_defs_path: Path to bdchv_defs.csv.
        contextual_vars_path: Path to contextual_variables_key.csv.
        unit_key_path: Path to unit_key.xlsx.
        output_path: Path for the output CSV.
        cleanup_rules_path: Optional path to a curator cleanup rules CSV.
        conversion_overrides_path: Path to label-keyed conversion overrides CSV.
            Defaults to the in-repo file.
        equivalency_overrides_path: Path to label-keyed equivalency overrides CSV.
            Defaults to the in-repo file.
        known_sheets: Excel sheet names to look for when loading raw data.
        entity_filter: Restrict output to rows with this bdchm_entity value.

    Returns:
        Path to the written output CSV, or None if no data was loaded.

    """
    logger.info("Loading documentation files...")
    bdchv_defs = load_bdchv_defs(bdchv_defs_path)
    contextual_vars = load_contextual_vars(contextual_vars_path)
    conversions = load_unit_conversions(unit_key_path)
    equivalencies = load_unit_equivalencies(unit_key_path)

    conversion_overrides = load_conversion_overrides(conversion_overrides_path) if conversion_overrides_path else None
    equivalency_overrides = (
        load_equivalency_overrides(equivalency_overrides_path) if equivalency_overrides_path else None
    )

    logger.info("Loading raw data from %d file(s)...", len(raw_files))
    df = load_raw_data(raw_files, known_sheets=known_sheets)
    if df.empty:
        logger.warning("No data loaded from raw files")
        return None

    logger.info("Standardizing raw data...")
    df = standardize_raw_data(df)

    if cleanup_rules_path is not None:
        logger.info("Applying curator cleanup rules from %s...", cleanup_rules_path)
        rules = load_cleanup_rules(cleanup_rules_path)
        df = apply_cleanup_rules(df, rules)

    logger.info("Finalizing cleaned data...")
    df = finalize_cleaned_data(df)

    logger.info("Merging with documentation...")
    df = merge_data_docs(
        df,
        bdchv_defs,
        conversions,
        equivalencies,
        contextual_vars,
        conversion_overrides=conversion_overrides,
        equivalency_overrides=equivalency_overrides,
        entity_filter=entity_filter,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_ALL)
    logger.info("Wrote %d rows to %s", len(df), output_path)
    return output_path
