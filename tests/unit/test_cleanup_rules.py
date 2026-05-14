"""Tests for the curator-maintained cleanup rules module."""

from pathlib import Path

import pandas as pd
import pytest

from dm_bip.trans_spec_gen.cleanup_rules import (
    apply_cleanup_rules,
    load_cleanup_rules,
)

TEST_DATA = Path(__file__).parent.parent / "input" / "prepare_metadata"


def _rule(**kwargs) -> pd.DataFrame:
    """Build a single-row rules DataFrame from kwargs."""
    base = {
        "rule_type": "",
        "match_field": "",
        "pattern": "",
        "is_regex": "",
        "when_label": "",
        "when_units": "",
        "except_labels": "",
        "target_value": "",
    }
    base.update(kwargs)
    return pd.DataFrame([base])


class TestLoadCleanupRules:
    """Tests for the cleanup rules CSV loader."""

    def test_loads_fixture_csv(self):
        """Loads the test fixture cleanup_rules.csv."""
        rules = load_cleanup_rules(TEST_DATA / "cleanup_rules.csv")
        assert "rule_type" in rules.columns
        assert len(rules) > 0

    def test_rejects_invalid_rule_type(self, tmp_path):
        """Raises if the CSV contains an unsupported rule_type value."""
        bad = tmp_path / "bad.csv"
        bad.write_text("rule_type,match_field,pattern\nfoo,bdchm_label,x\n")
        with pytest.raises(ValueError, match="invalid rule_type"):
            load_cleanup_rules(bad)

    def test_rejects_missing_required_columns(self, tmp_path):
        """Raises if the CSV is missing rule_type/match_field/pattern."""
        bad = tmp_path / "missing.csv"
        bad.write_text("rule_type,match_field\nalias,bdchm_label\n")
        with pytest.raises(ValueError, match="missing required columns"):
            load_cleanup_rules(bad)


class TestAlias:
    """Tests for alias rules — exact rewrite of a field value."""

    def test_alias_rewrites_label(self):
        """Exact match on bdchm_label rewrites to target_value."""
        df = pd.DataFrame({"bdchm_label": ["stroke status", "other"]})
        rules = _rule(rule_type="alias", match_field="bdchm_label", pattern="stroke status", target_value="stroke")
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == ["stroke", "other"]

    def test_alias_is_exact_not_substring(self):
        """An alias does not match substrings."""
        df = pd.DataFrame({"bdchm_label": ["stroke status today"]})
        rules = _rule(rule_type="alias", match_field="bdchm_label", pattern="stroke status", target_value="stroke")
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].iloc[0] == "stroke status today"


class TestDrop:
    """Tests for drop rules — remove matching rows."""

    def test_drop_exact_label(self):
        """Drops rows whose match_field equals pattern exactly."""
        df = pd.DataFrame({"bdchm_label": ["medication adherence", "albumin"]})
        rules = _rule(rule_type="drop", match_field="bdchm_label", pattern="medication adherence")
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == ["albumin"]

    def test_drop_with_regex(self):
        """Regex drop matches substrings/patterns."""
        df = pd.DataFrame({"transform_comment": ["out of scope flag", "ok"]})
        rules = _rule(rule_type="drop", match_field="transform_comment", pattern="out of scope", is_regex="1")
        result = apply_cleanup_rules(df, rules)
        assert result["transform_comment"].tolist() == ["ok"]


class TestClearLabel:
    """Tests for clear_label — set bdchm_label to empty when match_field matches pattern."""

    def test_exact_clear(self):
        """Exact match clears bdchm_label."""
        df = pd.DataFrame({"var_desc": ["visit type", "albumin"], "bdchm_label": ["foo", "bar"]})
        rules = _rule(rule_type="clear_label", match_field="var_desc", pattern="visit type")
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == ["", "bar"]

    def test_regex_with_except_labels(self):
        """Regex clear honors except_labels (rows with listed labels are skipped)."""
        df = pd.DataFrame(
            {
                "var_desc": ["days since visit", "days since visit", "albumin"],
                "bdchm_label": ["something", "death", "alb"],
            }
        )
        rules = _rule(
            rule_type="clear_label",
            match_field="var_desc",
            pattern="days since",
            is_regex="1",
            except_labels="death;age at follow-up",
        )
        result = apply_cleanup_rules(df, rules)
        # First row matches pattern, label not in except → cleared
        assert result["bdchm_label"].iloc[0] == ""
        # Second row matches pattern, label in except → preserved
        assert result["bdchm_label"].iloc[1] == "death"
        # Third row does not match → preserved
        assert result["bdchm_label"].iloc[2] == "alb"


class TestSetLabel:
    """Tests for set_label — set bdchm_label to target_value when match_field matches."""

    def test_set_label_with_when_label(self):
        """when_label restricts the rule to rows with a matching current label."""
        df = pd.DataFrame(
            {
                "var_desc": ["systolic blood pressure", "systolic measurement"],
                "bdchm_label": ["blood pressure", "other"],
            }
        )
        rules = _rule(
            rule_type="set_label",
            match_field="var_desc",
            pattern="systolic",
            is_regex="1",
            when_label="blood pressure",
            target_value="systolic blood pressure",
        )
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == ["systolic blood pressure", "other"]


class TestSetUnits:
    """Tests for set_units — set var_units to target_value when match_field matches."""

    def test_set_units_with_when_label_in(self):
        """when_label as a semicolon list uses isin against bdchm_label."""
        df = pd.DataFrame(
            {
                "var_desc": ["alcohol per week", "fruit per week", "tea per week"],
                "bdchm_label": ["alcohol servings", "fruit servings", "tea consumption"],
                "var_units": ["", "", ""],
            }
        )
        rules = _rule(
            rule_type="set_units",
            match_field="var_desc",
            pattern="per week",
            is_regex="1",
            when_label="alcohol servings;fruit servings",
            target_value="{#}/wk",
        )
        result = apply_cleanup_rules(df, rules)
        assert result["var_units"].tolist() == ["{#}/wk", "{#}/wk", ""]

    def test_set_units_when_units_empty(self):
        """when_units=';' restricts to rows where var_units is empty."""
        df = pd.DataFrame(
            {
                "var_desc": ["body mass index kg/m2", "body mass index kg/m2"],
                "bdchm_label": ["bmi", "bmi"],
                "var_units": ["", "kg"],
            }
        )
        rules = _rule(
            rule_type="set_units",
            match_field="var_desc",
            pattern="kg/m2",
            is_regex="1",
            when_units=";",
            target_value="kg/m2",
        )
        result = apply_cleanup_rules(df, rules)
        # First row had empty units → set; second already had kg → preserved
        assert result["var_units"].tolist() == ["kg/m2", "kg"]


class TestFixtureRules:
    """Sanity checks that the test fixture cleanup_rules.csv covers the original behaviors."""

    @pytest.fixture()
    def rules(self):
        """Load the fixture rules CSV."""
        return load_cleanup_rules(TEST_DATA / "cleanup_rules.csv")

    def test_medication_adherence_dropped(self, rules):
        """Pipeline must drop medication adherence rows via cleanup rules."""
        df = pd.DataFrame(
            {
                "bdchm_label": ["medication adherence", "albumin in blood"],
                "var_desc": ["", ""],
                "var_units": ["", ""],
                "cohort": ["aric", "aric"],
            }
        )
        result = apply_cleanup_rules(df, rules)
        assert "medication adherence" not in result["bdchm_label"].values

    def test_label_aliases(self, rules):
        """Stroke status / alcohol consumption aliases get rewritten."""
        df = pd.DataFrame(
            {
                "bdchm_label": ["stroke status", "alcohol consumption", "copd status"],
                "var_desc": ["", "", ""],
                "var_units": ["", "", ""],
                "cohort": ["aric", "aric", "aric"],
            }
        )
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == ["stroke", "alcohol servings", "copd"]

    def test_bp_disambiguation(self, rules):
        """BP rows pick up systolic/diastolic from var_desc."""
        df = pd.DataFrame(
            {
                "bdchm_label": ["blood pressure", "blood pressure"],
                "var_desc": ["systolic blood pressure", "diastolic blood pressure"],
                "var_units": ["", ""],
                "cohort": ["aric", "aric"],
            }
        )
        result = apply_cleanup_rules(df, rules)
        assert result["bdchm_label"].tolist() == [
            "systolic blood pressure",
            "diastolic blood pressure",
        ]
