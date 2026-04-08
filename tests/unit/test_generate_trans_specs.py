"""Tests for the dm_bip.trans_spec_gen.generate_trans_specs module."""

from pathlib import Path

import yaml

from dm_bip.trans_spec_gen.generate_trans_specs import generate_yaml

SAMPLE_CSV = Path(__file__).parents[1] / "input" / "make_yaml" / "shortdata_sample.csv"


def _run(tmp_path, cohort="aric"):
    return generate_yaml(
        input_csv=SAMPLE_CSV,
        output_dir=tmp_path,
        entity="MeasurementObservation",
        cohort=cohort,
    )


def _read_yaml(tmp_path, cohort, quality, varname):
    path = tmp_path / cohort / quality / f"{varname}.yaml"
    content = path.read_text()
    parsed = yaml.safe_load(content)
    return content, parsed


class TestFileOutput:
    """Tests for file creation and organization."""

    def test_produces_expected_good_files(self, tmp_path):
        """Generates one YAML file per good bdchm_varname."""
        _run(tmp_path)
        good_dir = tmp_path / "aric" / "good"
        good_files = sorted(p.stem for p in good_dir.glob("*.yaml"))
        assert good_files == ["albumin_bld", "bdy_hgt", "bdy_wgt", "bp_systolic", "glucose_bld", "waist_circ"]

    def test_produces_expected_bad_files(self, tmp_path):
        """Generates one YAML file per bad bdchm_varname."""
        _run(tmp_path)
        bad_dir = tmp_path / "aric" / "bad"
        bad_files = sorted(p.stem for p in bad_dir.glob("*.yaml"))
        assert bad_files == ["hemo_a1c"]

    def test_filters_by_cohort(self, tmp_path):
        """Only produces files for the requested cohort."""
        _run(tmp_path, cohort="jhs")
        assert (tmp_path / "jhs" / "good" / "bp_systolic.yaml").exists()
        assert not (tmp_path / "aric").exists()

    def test_returns_empty_for_missing_cohort(self, tmp_path):
        """Returns empty list when cohort has no matching rows."""
        assert _run(tmp_path, cohort="nonexistent") == []

    def test_good_files_are_valid_yaml(self, tmp_path):
        """All good output files parse as valid YAML."""
        _run(tmp_path)
        for path in (tmp_path / "aric" / "good").glob("*.yaml"):
            yaml.safe_load(path.read_text())


class TestUnitMatch:
    """Tests for the unit_match template branch (direct unit assignment)."""

    def test_renders_populated_from_with_phv(self, tmp_path):
        """Sets value_decimal.populated_from to the row's phv and unit to bdchm_unit."""
        _run(tmp_path)
        content, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        quantity = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]["value_quantity"]
        slots = quantity["object_derivations"][0]["class_derivations"]["Quantity"]["slot_derivations"]
        assert slots["value_decimal"]["populated_from"] == "phv00000103"
        assert slots["unit"]["value"] == "g/dL"


class TestUnitConvert:
    """Tests for the unit_convert template branch (source/target conversion)."""

    def test_renders_unit_conversion(self, tmp_path):
        """Sets value_decimal.unit_conversion with source/target units."""
        _run(tmp_path)
        content, parsed = _read_yaml(tmp_path, "aric", "good", "bdy_hgt")
        quantity = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]["value_quantity"]
        slots = quantity["object_derivations"][0]["class_derivations"]["Quantity"]["slot_derivations"]
        assert slots["value_decimal"]["unit_conversion"] == {"source_unit": "in", "target_unit": "cm"}
        assert slots["unit"]["value"] == "cm"


class TestUnitExpr:
    """Tests for the unit_expr template branch (expression-based conversion)."""

    def test_renders_expr_with_conversion_rule(self, tmp_path):
        """Sets value_decimal.expr to a phv reference with conversion math."""
        _run(tmp_path)
        content, parsed = _read_yaml(tmp_path, "aric", "good", "bdy_wgt")
        quantity = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]["value_quantity"]
        slots = quantity["object_derivations"][0]["class_derivations"]["Quantity"]["slot_derivations"]
        assert slots["value_decimal"]["expr"] == "{phv00000303} * 0.453592"
        assert slots["unit"]["value"] == "kg"


class TestUnitCaseStmt:
    """Tests for the unit_casestmt template branch (custom case expression)."""

    def test_renders_case_expression(self, tmp_path):
        """Sets value_decimal.expr to a case() expression with unit."""
        _run(tmp_path)
        content, parsed = _read_yaml(tmp_path, "aric", "good", "waist_circ")
        quantity = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]["value_quantity"]
        slots = quantity["object_derivations"][0]["class_derivations"]["Quantity"]["slot_derivations"]
        assert "case(" in slots["value_decimal"]["expr"]
        assert slots["unit"]["value"] == "cm"


class TestVisitHandling:
    """Tests for visit-related template branches."""

    def test_has_visit_renders_value(self, tmp_path):
        """has_visit=1 renders associated_visit with a value."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        assert slots["associated_visit"]["value"] == "Visit_1"

    def test_has_visit_expr_renders_uuid5(self, tmp_path):
        """has_visit_expr=1 renders associated_visit with a uuid5 expression."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "bp_systolic")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        expr = slots["associated_visit"]["expr"]
        assert expr.startswith("uuid5(")
        assert "Visit_1_label" in expr
        assert expr.endswith(")")


class TestAgeHandling:
    """Tests for age-related template branches."""

    def test_has_age_renders_expr(self, tmp_path):
        """has_age=1 renders age_at_observation with a * 365 expression."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        assert slots["age_at_observation"]["expr"] == "{phv00000102} * 365"

    def test_no_age_omits_field(self, tmp_path):
        """has_age=0 omits age_at_observation entirely."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "glucose_bld")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        assert "age_at_observation" not in slots


class TestCommonFields:
    """Tests for fields present in all output regardless of branch."""

    def test_populated_from_uses_pht(self, tmp_path):
        """Top-level populated_from is set to the row's pht value."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        mo = parsed[0]["class_derivations"]["MeasurementObservation"]
        assert mo["populated_from"] == "pht000001"

    def test_observation_type_uses_onto_id(self, tmp_path):
        """observation_type.value is set to the row's onto_id (LOINC code)."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        assert slots["observation_type"]["value"] == "LOINC:1751-7"

    def test_associated_participant_uses_participantidphv(self, tmp_path):
        """associated_participant.populated_from is set to the row's participantidphv."""
        _run(tmp_path)
        _, parsed = _read_yaml(tmp_path, "aric", "good", "albumin_bld")
        slots = parsed[0]["class_derivations"]["MeasurementObservation"]["slot_derivations"]
        assert slots["associated_participant"]["populated_from"] == "phv00000101"
