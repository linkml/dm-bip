"""Tests for the post-pipeline curator override utility."""

from pathlib import Path

import pandas as pd
import pytest

from dm_bip.trans_spec_gen.apply_overrides import apply_curator_overrides
from dm_bip.trans_spec_gen.prepare_metadata import prepare_metadata

TEST_DATA = Path(__file__).parent.parent / "input" / "prepare_metadata"
CLEANUP_RULES = TEST_DATA / "cleanup_rules.csv"


def _run_pipeline(out: Path) -> None:
    prepare_metadata(
        raw_files=[TEST_DATA / "raw_metadata.xlsx"],
        bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
        contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
        unit_key_path=TEST_DATA / "unit_key.xlsx",
        output_path=out,
        cleanup_rules_path=CLEANUP_RULES,
    )


def test_var_units_fixed_overrides_units(tmp_path):
    """A var_units_fixed override updates var_units in the corrected output."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,bdchm_label,var_units_fixed\nphv00202900,albumin in blood,mg/dL\n")
    corrected = tmp_path / "corrected.csv"
    apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=corrected)

    df = pd.read_csv(corrected)
    albumin = df[df["phv"] == "phv00202900"]
    assert not albumin.empty
    assert albumin.iloc[0]["var_units"] == "mg/dL"


def test_bad_map_drops_row(tmp_path):
    """bad_map=1 in fixes drops the matching row from the corrected output."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,bdchm_label,bad_map\nphv00202901,bmi,1\n")
    corrected = tmp_path / "corrected.csv"
    apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=corrected)

    df = pd.read_csv(corrected)
    assert "phv00202901" not in df["phv"].values


def test_associated_visit_override_recomputes_has_visit(tmp_path):
    """Overriding associatedvisit causes has_visit to be recomputed (still 1 here)."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,bdchm_label,associatedvisit\nphv00202900,albumin in blood,CUSTOM VISIT\n")
    corrected = tmp_path / "corrected.csv"
    apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=corrected)

    df = pd.read_csv(corrected)
    albumin = df[df["phv"] == "phv00202900"]
    assert albumin.iloc[0]["associatedvisit"] == "CUSTOM VISIT"
    assert albumin.iloc[0]["has_visit"] == 1


def test_unit_expr_custom_aliases_to_conversion_rule(tmp_path):
    """unit_expr_custom in fixes maps to conversion_rule and triggers unit_expr=1."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    # Pick a row with no unit_match: hdl already has unit_convert/conversion_rule.
    # Use albumin (unit_match=1) and override conversion_rule via unit_expr_custom.
    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,bdchm_label,var_units_fixed,unit_expr_custom\nphv00202900,albumin in blood,weird,* 0.5\n")
    corrected = tmp_path / "corrected.csv"
    apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=corrected)

    df = pd.read_csv(corrected)
    row = df[df["phv"] == "phv00202900"].iloc[0]
    assert row["conversion_rule"] == "* 0.5"
    # var_units now "weird", no longer matches, but conversion_rule present → unit_expr=1
    assert row["unit_expr"] == 1


def test_fixes_file_missing_required_columns(tmp_path):
    """Raises if fixes CSV is missing phv or bdchm_label."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,var_units_fixed\nphv00202900,mg/dL\n")
    with pytest.raises(ValueError, match="phv.*bdchm_label"):
        apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=tmp_path / "out.csv")


def test_duplicate_pair_id_in_fixes_raises(tmp_path):
    """Duplicate (phv, bdchm_label) keys in fixes CSV raise with the duplicate listed."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text(
        "phv,bdchm_label,var_units_fixed\nphv00202900,albumin in blood,mg/dL\nphv00202900,albumin in blood,g/L\n"
    )
    with pytest.raises(ValueError, match="duplicate"):
        apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=tmp_path / "out.csv")


def test_no_matching_fixes_passes_through(tmp_path):
    """Fixes file with non-matching keys produces output identical to input (modulo recomputed flags)."""
    pipeline_out = tmp_path / "pipeline.csv"
    _run_pipeline(pipeline_out)

    fixes = tmp_path / "fixes.csv"
    fixes.write_text("phv,bdchm_label,var_units_fixed\nphvNOMATCH,nope,mg/dL\n")
    corrected = tmp_path / "corrected.csv"
    apply_curator_overrides(pipeline_csv=pipeline_out, fixes_csv=fixes, output_csv=corrected)

    original = pd.read_csv(pipeline_out, dtype=str).fillna("")
    result = pd.read_csv(corrected, dtype=str).fillna("")
    assert len(original) == len(result)
