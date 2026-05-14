"""
Apply per-row curator overrides to a prepared-metadata CSV.

The mechanical pipeline produces a curated CSV from raw inputs and reference
data. Curators iterate on a separate fixes CSV that supplies per-(phv, label)
overrides. This module merges those fixes into the pipeline output and
recomputes quality flags so the corrected CSV remains consistent.

Recognized override columns in the fixes CSV (any subset; ``phv`` and
``bdchm_label`` are required as the composite key):

    var_units_fixed         override var_units
    bad_map                 if "1", drop the row entirely
    participantidphv        override participantidphv
    associatedvisit         override associatedvisit
    associatedvisit_expr    override associatedvisit_expr
    ageinyearsphv           override ageinyearsphv
    conversion_rule         override conversion_rule
    unit_expr_custom        alias for conversion_rule
    unit_casestmt_custom    override unit_casestmt_custom

The curator owns override completeness: this step does not re-run unit
conversion/equivalency lookups. If you change ``var_units`` you should also
supply any conversion-related overrides the new unit requires.
"""

import csv
import logging
from pathlib import Path

import pandas as pd

from dm_bip.trans_spec_gen.prepare_metadata import compute_quality_flags

logger = logging.getLogger(__name__)


_OVERRIDE_COLUMNS = {
    "var_units_fixed": "var_units",
    "participantidphv": "participantidphv",
    "associatedvisit": "associatedvisit",
    "associatedvisit_expr": "associatedvisit_expr",
    "ageinyearsphv": "ageinyearsphv",
    "conversion_rule": "conversion_rule",
    "unit_expr_custom": "conversion_rule",
    "unit_casestmt_custom": "unit_casestmt_custom",
}


def apply_curator_overrides(
    pipeline_csv: Path,
    fixes_csv: Path,
    output_csv: Path,
) -> Path:
    """
    Apply curator overrides from ``fixes_csv`` to ``pipeline_csv`` and write to ``output_csv``.

    Recomputes quality flags after applying overrides so derived columns
    stay consistent.
    """
    df = pd.read_csv(pipeline_csv, dtype=str).fillna("")
    fixes = pd.read_csv(fixes_csv, dtype=str).fillna("")

    if "phv" not in fixes.columns or "bdchm_label" not in fixes.columns:
        raise ValueError("fixes CSV must contain 'phv' and 'bdchm_label' columns")

    df["_pair_id"] = df["phv"] + "|" + df["bdchm_label"]
    fixes["_pair_id"] = fixes["phv"] + "|" + fixes["bdchm_label"]

    duplicates = fixes["_pair_id"][fixes["_pair_id"].duplicated()].unique().tolist()
    if duplicates:
        raise ValueError(
            f"fixes CSV has duplicate (phv, bdchm_label) keys: {duplicates}. "
            f"Each row in the fixes CSV must have a unique key."
        )

    for fix_col, target_col in _OVERRIDE_COLUMNS.items():
        if fix_col not in fixes.columns:
            continue
        mapping = dict(zip(fixes["_pair_id"], fixes[fix_col], strict=False))
        applied = df["_pair_id"].map(mapping)
        mask = applied.notna() & (applied != "")
        if not mask.any():
            continue
        if target_col not in df.columns:
            df[target_col] = ""
        df.loc[mask, target_col] = applied[mask]
        logger.info("Applied %d %s overrides", int(mask.sum()), fix_col)

    if "bad_map" in fixes.columns:
        bad_map_pairs = set(fixes.loc[fixes["bad_map"] == "1", "_pair_id"])
        bad_mask = df["_pair_id"].isin(bad_map_pairs)
        if bad_mask.any():
            logger.info("Dropping %d rows flagged bad_map=1", int(bad_mask.sum()))
            df = df[~bad_mask].copy()

    df = df.drop(columns=["_pair_id"])

    df = _recompute_quality_flags(df)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False, quoting=csv.QUOTE_ALL)
    logger.info("Wrote %d corrected rows to %s", len(df), output_csv)
    return output_csv


def _recompute_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Cast pipeline-derived columns back to numeric, recompute flags, restore string repr."""
    numeric_cols = [
        "has_pht",
        "has_onto",
        "unit_match",
        "unit_convert",
        "unit_expr",
        "unit_casestmt",
        "has_visit",
        "has_visit_expr",
        "has_age",
        "row_good",
        "equivalent_units",
        "both_valid_ucums",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    df = compute_quality_flags(df)

    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(int).astype(str)

    return df
