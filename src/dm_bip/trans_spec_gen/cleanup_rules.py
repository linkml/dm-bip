"""
Curator-maintained cleanup rules for raw metadata.

Loads a CSV of rules and applies them to a DataFrame before the mechanical
join/quality-flag pipeline runs. This isolates editorial decisions (label
corrections, label-from-description disambiguation, unit inference, row
exclusions) from the deterministic pipeline.

Rule grammar (one per row):

    rule_type      one of: alias, drop, clear_label, set_label, set_units
    match_field    column name to test (e.g. bdchm_label, var_desc, var_units, cohort)
    pattern        value to match against match_field; exact equality by default
    is_regex       1 if pattern is a case-insensitive regex (default 0)
    when_label     additional condition: bdchm_label must equal one of these (semicolon list)
    when_units     additional condition: var_units must equal one of these (semicolon list, "" allowed)
    except_labels  inverse condition: skip rows whose bdchm_label is in this semicolon list
    target_value   value to set when rule_type is alias, set_label, or set_units

A leading or trailing semicolon includes the empty string in the list, e.g.
when_units=";" matches only empty units, when_units=";{servings}" matches
empty or "{servings}".

Rule semantics:

    alias         exact rewrite of match_field (match_field == pattern → match_field = target_value)
    drop          remove rows where pattern matches match_field
    clear_label   set bdchm_label = "" where pattern matches match_field
    set_label     set bdchm_label = target_value where pattern matches match_field
    set_units     set var_units = target_value where pattern matches match_field

The when_label / when_units / except_labels columns are AND'd onto the match.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


VALID_RULE_TYPES = {"alias", "drop", "clear_label", "set_label", "set_units"}


def load_cleanup_rules(path: Path) -> pd.DataFrame:
    """Load and validate a cleanup rules CSV."""
    rules = pd.read_csv(path, dtype=str).fillna("")
    required = {"rule_type", "match_field", "pattern"}
    missing = required - set(rules.columns)
    if missing:
        raise ValueError(f"cleanup_rules CSV missing required columns: {sorted(missing)}")
    invalid = set(rules["rule_type"]) - VALID_RULE_TYPES
    if invalid:
        raise ValueError(f"cleanup_rules CSV has invalid rule_type values: {sorted(invalid)}")
    return rules


def apply_cleanup_rules(df: pd.DataFrame, rules: pd.DataFrame) -> pd.DataFrame:
    """Apply each cleanup rule to df in order, returning the modified DataFrame."""
    df = df.copy()
    for _, rule in rules.iterrows():
        df = _apply_one(df, rule)
    return df


def _apply_one(df: pd.DataFrame, rule: pd.Series) -> pd.DataFrame:
    rule_type = rule["rule_type"]
    field = rule["match_field"]

    if field not in df.columns:
        logger.debug("Skipping rule (column %r not present): %s", field, rule.to_dict())
        return df

    match = _match_mask(df, rule)
    match &= _condition_mask(df, rule)

    if not match.any():
        return df

    if rule_type == "alias":
        df.loc[match, field] = rule["target_value"]
    elif rule_type == "drop":
        df = df[~match].copy()
    elif rule_type == "clear_label":
        if "bdchm_label" in df.columns:
            df.loc[match, "bdchm_label"] = ""
    elif rule_type == "set_label":
        if "bdchm_label" in df.columns:
            df.loc[match, "bdchm_label"] = rule["target_value"]
    elif rule_type == "set_units":
        if "var_units" in df.columns:
            df.loc[match, "var_units"] = rule["target_value"]

    return df


def _match_mask(df: pd.DataFrame, rule: pd.Series) -> pd.Series:
    field = rule["match_field"]
    pattern = rule["pattern"]
    is_regex = rule.get("is_regex", "") == "1"
    series = df[field].fillna("")

    if is_regex:
        try:
            return series.str.contains(pattern, flags=re.IGNORECASE, regex=True, na=False)
        except re.error as e:
            raise ValueError(
                f"Invalid regex in cleanup rule "
                f"(rule_type={rule['rule_type']!r}, match_field={field!r}, pattern={pattern!r}): {e}"
            ) from e
    return series == pattern


def _condition_mask(df: pd.DataFrame, rule: pd.Series) -> pd.Series:
    mask = pd.Series(True, index=df.index)

    when_label = rule.get("when_label", "")
    if when_label and "bdchm_label" in df.columns:
        allowed = when_label.split(";")
        mask &= df["bdchm_label"].fillna("").isin(allowed)

    when_units = rule.get("when_units", "")
    if when_units and "var_units" in df.columns:
        allowed = when_units.split(";")
        mask &= df["var_units"].fillna("").isin(allowed)

    except_labels = rule.get("except_labels", "")
    if except_labels and "bdchm_label" in df.columns:
        excluded = [lbl for lbl in except_labels.split(";") if lbl]
        mask &= ~df["bdchm_label"].fillna("").isin(excluded)

    return mask
