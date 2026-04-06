"""Tests for the make_yaml generate_trans_specs module."""

from pathlib import Path

from dm_bip.make_yaml.generate_trans_specs import generate_yaml

SAMPLE_CSV = Path(__file__).parents[1] / "input" / "make_yaml" / "shortdata_sample.csv"


class TestGenerateYaml:
    """Tests for the generate_yaml function."""

    def test_generates_yaml_files_for_cohort(self, tmp_path):
        """Generates YAML files for filtered entity/cohort rows."""
        result = generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="aric",
        )
        assert len(result) > 0
        for path in result:
            assert path.exists()
            content = path.read_text()
            assert "MeasurementObservation" in content

    def test_separates_good_and_bad(self, tmp_path):
        """Good rows go to good/ dir, bad rows go to bad/ dir."""
        generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="aric",
        )
        good_dir = tmp_path / "aric" / "good"
        bad_dir = tmp_path / "aric" / "bad"
        assert good_dir.exists()
        assert bad_dir.exists()
        assert (good_dir / "albumin_bld.yaml").exists()
        assert (bad_dir / "hemo_a1c.yaml").exists()

    def test_returns_empty_for_missing_cohort(self, tmp_path):
        """Returns empty list when cohort has no matching rows."""
        result = generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="nonexistent",
        )
        assert result == []

    def test_unit_match_renders_populated_from(self, tmp_path):
        """unit_match rows render populated_from for value_decimal."""
        generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="aric",
        )
        content = (tmp_path / "aric" / "good" / "albumin_bld.yaml").read_text()
        assert "populated_from: phv00000103" in content
        assert 'value: "g/dL"' in content

    def test_unit_convert_renders_conversion(self, tmp_path):
        """unit_convert rows render source/target unit conversion."""
        generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="aric",
        )
        content = (tmp_path / "aric" / "good" / "bdy_hgt.yaml").read_text()
        assert 'source_unit: "in"' in content
        assert 'target_unit: "cm"' in content

    def test_unit_expr_renders_expression(self, tmp_path):
        """unit_expr rows render an expression for value_decimal."""
        generate_yaml(
            input_csv=SAMPLE_CSV,
            output_dir=tmp_path,
            entity="MeasurementObservation",
            cohort="aric",
        )
        content = (tmp_path / "aric" / "good" / "bdy_wgt.yaml").read_text()
        assert "expr:" in content
        assert "0.453592" in content
