"""Tests for the metadata preparation pipeline (Stata steps 1-4 port)."""

from pathlib import Path

import pandas as pd
import pytest

from dm_bip.trans_spec_gen.prepare_metadata import (
    _normalize_columns,
    clean_data,
    load_bdchv_defs,
    load_contextual_vars,
    load_raw_data,
    load_unit_conversions,
    load_unit_equivalencies,
    merge_data_docs,
    prepare_metadata,
    standardize_raw_data,
)
from dm_bip.trans_spec_gen.units import normalize_unit

TEST_DATA = Path(__file__).parent.parent / "input" / "prepare_metadata"


# --- Unit normalization tests ---


class TestUnitNormalization:
    """Tests for the unit normalization lookup table."""

    def test_lowercase_mapping(self):
        """Maps lowercase variant to canonical UCUM."""
        assert normalize_unit("percent") == "%"

    def test_case_insensitive(self):
        """Handles mixed-case input."""
        assert normalize_unit("Percent") == "%"

    def test_spaces_stripped(self):
        """Strips spaces before lookup."""
        assert normalize_unit("mg / dL") == "mg/dL"

    def test_pounds(self):
        """Maps pound variants to [lb_av]."""
        assert normalize_unit("lbs") == "[lb_av]"
        assert normalize_unit("pounds") == "[lb_av]"

    def test_inches(self):
        """Maps inch variants to [in_us]."""
        assert normalize_unit("inches") == "[in_us]"

    def test_mmhg(self):
        """Maps mmHg variants to mm[Hg]."""
        assert normalize_unit("mmhg") == "mm[Hg]"
        assert normalize_unit("mm/hg") == "mm[Hg]"

    def test_none_maps_to_empty(self):
        """Values like n/a and codes map to empty string via 'none'."""
        assert normalize_unit("n/a") == ""
        assert normalize_unit("codes") == ""

    def test_unknown_passthrough(self):
        """Values not in the lookup table pass through after lowering and space removal."""
        assert normalize_unit("mg/dL") == "mg/dL"

    def test_empty_input(self):
        """Empty and None inputs return empty string."""
        assert normalize_unit("") == ""
        assert normalize_unit(None) == ""


# --- Documentation loading tests ---


class TestLoadBdchvDefs:
    """Tests for loading BDC harmonized variable definitions."""

    def test_loads_and_creates_onto_id(self):
        """Creates onto_id and merge_bdchm_label columns."""
        df = load_bdchv_defs(TEST_DATA / "bdchv_defs.csv")
        assert "onto_id" in df.columns
        assert "merge_bdchm_label" in df.columns

    def test_onto_id_prefers_obacurie(self):
        """Uses obacurie when available."""
        df = load_bdchv_defs(TEST_DATA / "bdchv_defs.csv")
        albumin = df[df["bdchm_varname"] == "albumin_bld"].iloc[0]
        assert albumin["onto_id"] == "OBA:2050068"

    def test_onto_id_falls_back_to_omop(self):
        """Falls back to omop when obacurie is empty."""
        df = load_bdchv_defs(TEST_DATA / "bdchv_defs.csv")
        bdy_hgt = df[df["bdchm_varname"] == "bdy_hgt"].iloc[0]
        assert bdy_hgt["onto_id"] == "OMOP:4177340"

    def test_merge_label_lowercase_no_spaces(self):
        """Creates merge key as lowercase with no spaces."""
        df = load_bdchv_defs(TEST_DATA / "bdchv_defs.csv")
        albumin = df[df["bdchm_varname"] == "albumin_bld"].iloc[0]
        assert albumin["merge_bdchm_label"] == "albumininblood"


class TestLoadContextualVars:
    """Tests for loading contextual variables key."""

    def test_loads_and_renames(self):
        """Renames notes column and drops datatablename."""
        df = load_contextual_vars(TEST_DATA / "contextual_variables_key.csv")
        assert "contextvars_notes" in df.columns
        assert "notes" not in df.columns
        assert "datatablename" not in df.columns

    def test_drops_empty_pht(self):
        """Drops rows with empty pht."""
        df = load_contextual_vars(TEST_DATA / "contextual_variables_key.csv")
        assert df["pht"].notna().all()

    def test_uppercases_visits(self):
        """Uppercases associatedvisit values."""
        df = load_contextual_vars(TEST_DATA / "contextual_variables_key.csv")
        aric = df[df["pht"] == "pht004027"].iloc[0]
        assert aric["associatedvisit"] == "ARIC EXAM 1"


class TestLoadUnitData:
    """Tests for loading unit conversion and equivalency data."""

    def test_conversions_have_merge_key(self):
        """Conversion table has unit_merge_key and validity flags."""
        df = load_unit_conversions(TEST_DATA / "unit_key.xlsx")
        assert "unit_merge_key" in df.columns
        assert "both_valid_ucums" in df.columns

    def test_equivalencies_have_merge_key(self):
        """Equivalency table has unit_merge_key and flag."""
        df = load_unit_equivalencies(TEST_DATA / "unit_key.xlsx")
        assert "unit_merge_key" in df.columns
        assert "equivalent_units" in df.columns


# --- Raw data standardization tests ---


class TestStandardizeRawData:
    """Tests for raw data standardization (accession splitting, lowercasing, unit normalization)."""

    @pytest.fixture()
    def raw_df(self):
        """Load raw test metadata."""
        df = pd.read_excel(TEST_DATA / "raw_metadata.xlsx", dtype=str)
        return df

    def test_splits_accession_ids(self, raw_df):
        """Splits dotted accession IDs into phv/phs/pht columns."""
        result = standardize_raw_data(raw_df)
        assert "phv" in result.columns
        assert "phs" in result.columns
        assert "pht" in result.columns
        assert result["phv"].iloc[0] == "phv00202900"

    def test_lowercases_values(self, raw_df):
        """Lowercases cohort, var_units, var_desc."""
        result = standardize_raw_data(raw_df)
        assert (result["cohort"] == result["cohort"].str.lower()).all()

    def test_normalizes_units(self, raw_df):
        """Applies unit normalization (gm/dl -> g/dL)."""
        result = standardize_raw_data(raw_df)
        albumin_row = result[result["phv"] == "phv00202900"].iloc[0]
        assert albumin_row["var_units"] == "g/dL"


# --- Cleaning tests ---


class TestCleanData:
    """Tests for data cleaning (label fixes, unit inference, BP disambiguation)."""

    @pytest.fixture()
    def standardized_df(self):
        """Load and standardize raw test metadata."""
        df = pd.read_excel(TEST_DATA / "raw_metadata.xlsx", dtype=str)
        return standardize_raw_data(df)

    def test_drops_medication_adherence(self, standardized_df):
        """Excludes medication adherence rows."""
        result = clean_data(standardized_df)
        if "bdchm_label" in result.columns:
            assert "medication adherence" not in result["bdchm_label"].values

    def test_fixes_label_stroke_status(self, standardized_df):
        """Corrects 'stroke status' to 'stroke'."""
        result = clean_data(standardized_df)
        assert "stroke status" not in result["bdchm_label"].values
        assert "stroke" in result["bdchm_label"].values

    def test_fixes_label_alcohol_consumption(self, standardized_df):
        """Corrects 'alcohol consumption' to 'alcohol servings'."""
        result = clean_data(standardized_df)
        assert "alcohol consumption" not in result["bdchm_label"].values
        assert "alcohol servings" in result["bdchm_label"].values

    def test_bp_disambiguation(self, standardized_df):
        """Splits 'blood pressure' into systolic/diastolic based on var_desc."""
        result = clean_data(standardized_df)
        assert "systolic blood pressure" in result["bdchm_label"].values
        assert "diastolic blood pressure" in result["bdchm_label"].values
        assert "blood pressure" not in result["bdchm_label"].values

    def test_infers_sleep_hours_unit(self, standardized_df):
        """Infers 'h' unit for sleep hours from description."""
        result = clean_data(standardized_df)
        sleep = result[result["bdchm_label"] == "sleep hours"]
        assert not sleep.empty, "Expected sleep hours row in output"
        assert sleep.iloc[0]["var_units"] == "h"

    def test_infers_bmi_unit(self, standardized_df):
        """Infers 'kg/m2' unit from description containing kg/m2."""
        result = clean_data(standardized_df)
        bmi = result[result["bdchm_label"] == "bmi"]
        assert not bmi.empty, "Expected bmi row in output"
        assert bmi.iloc[0]["var_units"] == "kg/m2"

    def test_infers_alcohol_weekly_unit(self, standardized_df):
        """Infers '{#}/wk' unit for alcohol servings from 'per week' description."""
        result = clean_data(standardized_df)
        alcohol = result[result["bdchm_label"] == "alcohol servings"]
        assert not alcohol.empty, "Expected alcohol servings row in output"
        assert alcohol.iloc[0]["var_units"] == "{#}/wk"


# --- Full pipeline test ---


class TestFullPipeline:
    """Tests for the full prepare_metadata pipeline end-to-end."""

    def test_produces_output_csv(self, tmp_path):
        """Pipeline produces a non-empty output CSV."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        assert output.exists()
        df = pd.read_csv(output)
        assert len(df) > 0

    def test_output_has_required_columns(self, tmp_path):
        """Output CSV contains all expected columns."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        required_cols = ["row_good", "cohort", "bdchm_entity", "bdchm_varname", "phv", "unit_match"]
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"

    def test_only_measurement_observation(self, tmp_path):
        """Output contains only MeasurementObservation rows."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        assert (df["bdchm_entity"] == "MeasurementObservation").all()

    def test_dropped_table_excluded(self, tmp_path):
        """Rows with drop_table=1 in contextual_vars are excluded."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        # pht009999 has drop_table=1 in contextual_vars
        assert "pht009999" not in df["pht"].values

    def test_unit_match_flag(self, tmp_path):
        """Sets unit_match=1 when source and target units match exactly."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        # albumin: var_units=g/dL, bdchm_unit=g/dL -> unit_match=1
        albumin = df[df["bdchm_varname"] == "albumin_bld"]
        assert not albumin.empty, "Expected albumin_bld row in output"
        assert albumin.iloc[0]["unit_match"] == 1

    def test_unit_convert_flag(self, tmp_path):
        """Sets unit_convert=1 when both units are valid UCUM with a conversion."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        # height: var_units=inches->[in_us], bdchm_unit=cm, both in UCUM -> unit_convert=1
        height = df[df["bdchm_varname"] == "bdy_hgt"]
        assert not height.empty, "Expected bdy_hgt row in output"
        assert height.iloc[0]["unit_convert"] == 1

    def test_row_good_flag(self, tmp_path):
        """Sets row_good=1 when has_pht, has_onto, and unit handling are all present."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        assert df["row_good"].sum() > 0
        aric_albumin = df[(df["bdchm_varname"] == "albumin_bld") & (df["cohort"] == "aric")]
        assert not aric_albumin.empty, "Expected aric albumin_bld row in output"
        assert aric_albumin.iloc[0]["row_good"] == 1

    def test_curator_fixes_applied(self, tmp_path):
        """Curator fixes CSV overrides unit and marks bad maps."""
        fixes_csv = tmp_path / "fixes.csv"
        fixes_csv.write_text(
            "phv,bdchm_label,var_units_fixed,bad_map\nphv00202900,albumin in blood,mg/dL,\nphv00202901,bmi,,1\n"
        )
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
            fixes_file=fixes_csv,
        )
        df = pd.read_csv(output)
        # albumin should have overridden var_units
        albumin = df[df["phv"] == "phv00202900"]
        assert not albumin.empty
        assert albumin.iloc[0]["var_units"] == "mg/dL"
        # bmi should be excluded (bad_map=1 clears bdchm_label, then filtered out)
        assert "phv00202901" not in df["phv"].values


# --- Column normalization tests ---


class TestNormalizeColumns:
    """Characterization tests for _normalize_columns: FHS detection, backfill, label correction."""

    def test_lowercases_and_strips(self):
        """Column names are lowercased and surrounding whitespace stripped."""
        df = pd.DataFrame(columns=["  Cohort  ", "VAR_DESC"])
        result = _normalize_columns(df)
        assert "cohort" in result.columns
        assert "var_desc" in result.columns

    def test_renames_data_table_dotted(self):
        """FHS-style data_table.* columns are renamed to standardized names."""
        df = pd.DataFrame(columns=["data_table.study_id", "data_table.variable.id", "data_table.variable.units"])
        result = _normalize_columns(df)
        assert "study_id" in result.columns
        assert "var_id" in result.columns
        assert "var_units" in result.columns

    def test_renames_var_report_dotted(self):
        """Non-FHS var_report.* columns are renamed to standardized names."""
        df = pd.DataFrame(columns=["var_report.study_id", "var_report.variable.description"])
        result = _normalize_columns(df)
        assert "study_id" in result.columns
        assert "var_desc" in result.columns

    def test_unknown_dotted_columns_get_underscores(self):
        """Columns not in the rename map have dots and spaces replaced with underscores."""
        df = pd.DataFrame(columns=["some.weird.col", "another col"])
        result = _normalize_columns(df)
        assert "some_weird_col" in result.columns
        assert "another_col" in result.columns

    def test_renames_bracketed_columns(self):
        """Bracketed first[...] aggregate columns are renamed to first_<field>."""
        df = pd.DataFrame(columns=["first[data_table.study_id]", "first[data_table.variable.id]"])
        result = _normalize_columns(df)
        assert "first_study_id" in result.columns
        assert "first_variable_id" in result.columns

    def test_fhs_detection_adds_cohort(self):
        """variable_accession present and cohort absent → cohort = 'fhs'."""
        df = pd.DataFrame({"variable_accession": ["phv001"], "var_desc": ["x"]})
        result = _normalize_columns(df)
        assert "cohort" in result.columns
        assert (result["cohort"] == "fhs").all()

    def test_fhs_detection_skipped_when_cohort_present(self):
        """If a cohort column already exists, FHS detection does not overwrite it."""
        df = pd.DataFrame({"variable_accession": ["phv001"], "Cohort": ["aric"]})
        result = _normalize_columns(df)
        assert (result["cohort"] == "aric").all()

    def test_fhs_backfill_when_target_missing(self):
        """If primary accession columns are absent, source alternates supply them."""
        df = pd.DataFrame(
            {
                "dbgap_study_accession": ["phs000001"],
                "variable_accession": ["phv00001"],
                "dataset_accession": ["pht00001"],
            }
        )
        result = _normalize_columns(df)
        assert result["study_id"].iloc[0] == "phs000001"
        assert result["var_id"].iloc[0] == "phv00001"
        assert result["data_table_id"].iloc[0] == "pht00001"

    def test_fhs_backfill_fills_na_when_target_present(self):
        """When primary column has NaN, backfill from accession alternate."""
        df = pd.DataFrame(
            {
                "data_table.study_id": [None, "phs000002"],
                "dbgap_study_accession": ["phs000001", "phs999"],
            }
        )
        result = _normalize_columns(df)
        # First row has NaN study_id → filled from dbgap_study_accession
        assert result["study_id"].iloc[0] == "phs000001"
        # Second row had value → not overwritten
        assert result["study_id"].iloc[1] == "phs000002"

    def test_bdchm_label_corrected_overrides_label(self):
        """A non-empty bdchm_label_(corrected) value replaces bdchm_label; empty/NaN does not."""
        df = pd.DataFrame(
            {
                "bdchm_label": ["original", "original2", "original3"],
                "bdchm_label_(corrected)": ["fixed", None, ""],
            }
        )
        result = _normalize_columns(df)
        assert result["bdchm_label"].iloc[0] == "fixed"
        # NaN and empty leave label alone
        assert result["bdchm_label"].iloc[1] == "original2"
        assert result["bdchm_label"].iloc[2] == "original3"

    def test_note_and_notes_collapse_to_curator_note(self):
        """Both 'note' and 'notes' source columns map to 'curator_note'."""
        df = pd.DataFrame(columns=["note", "var_desc"])
        result = _normalize_columns(df)
        assert "curator_note" in result.columns


# --- merge_data_docs internal characterization tests ---


@pytest.fixture()
def docs():
    """Load documentation tables for merge_data_docs tests."""
    return {
        "bdchv_defs": load_bdchv_defs(TEST_DATA / "bdchv_defs.csv"),
        "contextual_vars": load_contextual_vars(TEST_DATA / "contextual_variables_key.csv"),
        "conversions": load_unit_conversions(TEST_DATA / "unit_key.xlsx"),
        "equivalencies": load_unit_equivalencies(TEST_DATA / "unit_key.xlsx"),
    }


def _make_clean_row(**overrides):
    """Build a single cleaned-data row with sensible defaults for merge_data_docs."""
    base = {
        "cohort": "aric",
        "bdchm_label": "albumin in blood",
        "merge_bdchm_label": "albumininblood",
        "phv": "phv001",
        "phs": "phs001",
        "pht": "pht004027",
        "var_desc": "albumin",
        "var_units": "g/dL",
        "var_type": "decimal",
        "bdchm_entity": "MeasurementObservation",
    }
    base.update(overrides)
    return base


class TestMergeDataDocsFlags:
    """Pin behavior of quality flag computation in merge_data_docs."""

    def test_has_pht_set_when_contextual_match(self, docs):
        """has_pht=1 when row's pht matches contextual_vars (joined participantidphv non-null)."""
        df = pd.DataFrame([_make_clean_row(pht="pht004027")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_pht"] == 1

    def test_has_pht_zero_when_no_contextual_match(self, docs):
        """has_pht=0 when row's pht does not appear in contextual_vars."""
        df = pd.DataFrame([_make_clean_row(pht="pht999999")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_pht"] == 0

    def test_has_onto_from_obacurie(self, docs):
        """has_onto=1 and onto_id populated from bdchv_defs join (obacurie wins over omop)."""
        df = pd.DataFrame([_make_clean_row()])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_onto"] == 1
        assert result.iloc[0]["onto_id"] == "OBA:2050068"

    def test_has_onto_zero_when_no_match(self, docs):
        """No bdchv_defs match → onto_id empty → has_onto=0 (entity filter keeps the row)."""
        df = pd.DataFrame([_make_clean_row(bdchm_label="totally unknown", merge_bdchm_label="totallyunknown")])
        result = merge_data_docs(df, **docs)
        assert not result.empty
        assert result.iloc[0]["has_onto"] == 0

    def test_unit_match_exact(self, docs):
        """Exact unit string equality sets unit_match=1 and prevents unit_convert."""
        df = pd.DataFrame([_make_clean_row(var_units="g/dL")])  # bdchm_unit for albumin = g/dL
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["unit_match"] == 1
        assert result.iloc[0]["unit_convert"] == 0

    def test_unit_convert_when_both_ucum(self, docs):
        """height: inches→cm — both valid UCUM, should set unit_convert=1."""
        df = pd.DataFrame(
            [
                _make_clean_row(
                    bdchm_label="body height",
                    merge_bdchm_label="bodyheight",
                    var_units="[in_us]",
                )
            ]
        )
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["unit_match"] == 0
        assert result.iloc[0]["unit_convert"] == 1

    def test_unit_expr_via_curator_fix(self, docs, tmp_path):
        """unit_expr=1 when conversion_rule comes from a curator unit_expr_custom override."""
        df = pd.DataFrame(
            [
                _make_clean_row(
                    phv="phv999",
                    var_units="weird_unit",
                )
            ]
        )
        fixes = tmp_path / "fixes.csv"
        fixes.write_text(
            "phv,bdchm_label,unit_expr_custom\nphv999,albumin in blood,* 0.5\n",
        )
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["conversion_rule"] == "* 0.5"
        assert result.iloc[0]["unit_expr"] == 1

    def test_unit_casestmt_via_curator_fix(self, docs, tmp_path):
        """A curator-supplied unit_casestmt_custom value sets unit_casestmt=1."""
        df = pd.DataFrame([_make_clean_row(phv="phv888")])
        fixes = tmp_path / "fixes.csv"
        fixes.write_text(
            "phv,bdchm_label,unit_casestmt_custom\nphv888,albumin in blood,case when x then y end\n",
        )
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["unit_casestmt"] == 1

    def test_has_visit_from_contextual_vars(self, docs):
        """pht004027 → 'ARIC EXAM 1' in contextual_vars → has_visit=1."""
        df = pd.DataFrame([_make_clean_row(pht="pht004027")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_visit"] == 1
        assert result.iloc[0]["associatedvisit"] == "ARIC EXAM 1"

    def test_has_visit_expr(self, docs):
        """pht001201 has associatedvisit_expr='Visit_2_label' but no associatedvisit → has_visit_expr=1."""
        df = pd.DataFrame(
            [
                _make_clean_row(
                    cohort="jhs",
                    pht="pht001201",
                )
            ]
        )
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_visit"] == 0
        assert result.iloc[0]["has_visit_expr"] == 1
        assert result.iloc[0]["associatedvisit_expr"] == "Visit_2_label"

    def test_has_age_from_contextual_vars(self, docs):
        """pht004027 has ageinyearsphv populated → has_age=1."""
        df = pd.DataFrame([_make_clean_row(pht="pht004027")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["has_age"] == 1

    def test_row_good_requires_pht_onto_and_unit(self, docs):
        """row_good=1 requires has_pht and has_onto and (unit_match or unit_convert or unit_expr or unit_casestmt)."""
        df = pd.DataFrame([_make_clean_row()])
        result = merge_data_docs(df, **docs)
        row = result.iloc[0]
        assert row["has_pht"] == 1 and row["has_onto"] == 1 and row["unit_match"] == 1
        assert row["row_good"] == 1

    def test_row_good_zero_without_pht(self, docs):
        """Missing pht context drops row_good to 0 even when other flags are good."""
        df = pd.DataFrame([_make_clean_row(pht="pht999999")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["row_good"] == 0

    def test_var_desc_exam_extraction(self, docs):
        """'exam N' substring extracted from var_desc into var_desc_exam."""
        df = pd.DataFrame([_make_clean_row(var_desc="serum albumin exam 3")])
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["var_desc_exam"] == "exam 3"


class TestMergeDataDocsSpotFixes:
    """Pin the hardcoded conversion/equivalency spot-fixes (cholesterol, factor VIII, MCHC, sodium)."""

    def test_cholesterol_hdl_mmol_to_mgdl(self, docs):
        """HDL with mmol/L → conversion_rule overridden to '* 38.67'."""
        df = pd.DataFrame(
            [
                _make_clean_row(
                    bdchm_label="hdl",
                    merge_bdchm_label="hdl",
                    var_units="mmol/L",
                )
            ]
        )
        result = merge_data_docs(df, **docs)
        assert result.iloc[0]["conversion_rule"] == "* 38.67"

    def test_factor_viii_pct_to_iuml(self, docs):
        """Factor VIII spot-fix: % → [IU]/mL gets conversion_rule '* 0.01' (synthesizes a defs row)."""
        bdchv = pd.concat(
            [
                docs["bdchv_defs"],
                pd.DataFrame(
                    [
                        {
                            "bdchm_entity": "MeasurementObservation",
                            "bdchm_varlabel": "Factor VIII",
                            "bdchm_varname": "factor_viii",
                            "bdchm_vartype": "decimal",
                            "bdchm_unit": "[IU]/mL",
                            "onto_id": "OMOP:0000000",
                            "merge_bdchm_label": "factorviii",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        df = pd.DataFrame(
            [
                _make_clean_row(
                    bdchm_label="factor viii",
                    merge_bdchm_label="factorviii",
                    var_units="%",
                )
            ]
        )
        result = merge_data_docs(
            df,
            bdchv_defs=bdchv,
            conversions=docs["conversions"],
            equivalencies=docs["equivalencies"],
            contextual_vars=docs["contextual_vars"],
        )
        assert result.iloc[0]["conversion_rule"] == "* 0.01"

    def test_mchc_pct_equiv_to_gdl(self, docs):
        """MCHC: % is equivalent to g/dL — equivalent_units forced to 1, sets unit_match=1."""
        bdchv = pd.concat(
            [
                docs["bdchv_defs"],
                pd.DataFrame(
                    [
                        {
                            "bdchm_entity": "MeasurementObservation",
                            "bdchm_varlabel": "MCHC",
                            "bdchm_varname": "mchc",
                            "bdchm_vartype": "decimal",
                            "bdchm_unit": "g/dL",
                            "onto_id": "OMOP:0000001",
                            "merge_bdchm_label": "meancorpuscularhemoglobinconcentration",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        df = pd.DataFrame(
            [
                _make_clean_row(
                    bdchm_label="mean corpuscular hemoglobin concentration",
                    merge_bdchm_label="meancorpuscularhemoglobinconcentration",
                    var_units="%",
                )
            ]
        )
        result = merge_data_docs(
            df,
            bdchv_defs=bdchv,
            conversions=docs["conversions"],
            equivalencies=docs["equivalencies"],
            contextual_vars=docs["contextual_vars"],
        )
        assert result.iloc[0]["unit_match"] == 1

    def test_sodium_meq_equiv_to_mmol(self, docs):
        """Sodium: meq/L is equivalent to mmol/L — sets unit_match=1."""
        bdchv = pd.concat(
            [
                docs["bdchv_defs"],
                pd.DataFrame(
                    [
                        {
                            "bdchm_entity": "MeasurementObservation",
                            "bdchm_varlabel": "Sodium in blood",
                            "bdchm_varname": "sodium_bld",
                            "bdchm_vartype": "decimal",
                            "bdchm_unit": "mmol/L",
                            "onto_id": "OMOP:0000002",
                            "merge_bdchm_label": "sodiuminblood",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        df = pd.DataFrame(
            [
                _make_clean_row(
                    bdchm_label="sodium in blood",
                    merge_bdchm_label="sodiuminblood",
                    var_units="meq/L",
                )
            ]
        )
        result = merge_data_docs(
            df,
            bdchv_defs=bdchv,
            conversions=docs["conversions"],
            equivalencies=docs["equivalencies"],
            contextual_vars=docs["contextual_vars"],
        )
        assert result.iloc[0]["unit_match"] == 1


class TestMergeDataDocsCuratorOverrides:
    """Curator fixes can override participant/visit/age/conversion fields in the merge step."""

    def test_associatedvisit_override(self, docs, tmp_path):
        """Curator fix overrides the associatedvisit value from contextual_vars."""
        df = pd.DataFrame([_make_clean_row(phv="phv777", pht="pht004027")])
        fixes = tmp_path / "fixes.csv"
        fixes.write_text("phv,bdchm_label,associatedvisit\nphv777,albumin in blood,CUSTOM VISIT\n")
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["associatedvisit"] == "CUSTOM VISIT"

    def test_participantidphv_override(self, docs, tmp_path):
        """Curator fix supplies participantidphv when no pht-based match exists."""
        df = pd.DataFrame([_make_clean_row(phv="phv777", pht="pht999999")])
        fixes = tmp_path / "fixes.csv"
        fixes.write_text("phv,bdchm_label,participantidphv\nphv777,albumin in blood,phvCUSTOM\n")
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["participantidphv"] == "phvCUSTOM"

    def test_ageinyears_override(self, docs, tmp_path):
        """Curator fix on ageinyearsphv supplies the value and sets has_age=1."""
        df = pd.DataFrame([_make_clean_row(phv="phv777", pht="pht999999")])
        fixes = tmp_path / "fixes.csv"
        fixes.write_text("phv,bdchm_label,ageinyearsphv\nphv777,albumin in blood,phvAGE\n")
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["has_age"] == 1
        assert result.iloc[0]["ageinyearsphv"] == "phvAGE"

    def test_visit_expr_cleared_when_direct_visit_present(self, docs, tmp_path):
        """If has_visit==1 and curator also sets associatedvisit_expr, the expr is cleared."""
        df = pd.DataFrame([_make_clean_row(phv="phv777", pht="pht004027")])
        fixes = tmp_path / "fixes.csv"
        fixes.write_text("phv,bdchm_label,associatedvisit_expr\nphv777,albumin in blood,SOME_EXPR\n")
        result = merge_data_docs(df, **docs, fixes_file=fixes)
        assert result.iloc[0]["has_visit"] == 1
        assert result.iloc[0]["has_visit_expr"] == 0


# --- Golden-file regression test ---


class TestPipelineGoldenOutput:
    """Pin full pipeline output shape so refactors / replacements can't silently regress."""

    def test_output_columns_are_stable(self, tmp_path):
        """Lock the exact column set produced by the pipeline."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        expected_columns = {
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
            "var_desc_exam",
            "has_age",
            "ageinyearsphv",
            "contextvars_notes",
            "unit_match",
            "unit_convert",
            "unit_expr",
            "conversion_rule",
            "unit_casestmt",
            "source_unit",
            "target_unit",
        }
        assert set(df.columns) == expected_columns

    def test_output_row_count_is_stable(self, tmp_path):
        """Lock the exact row count for the synthetic fixture."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        df = pd.read_csv(output)
        # Fixture has 11 aric measurement rows + 1 jhs measurement row + 1 condition row.
        # Filters: medication-adherence dropped, glucose dropped (pht009999 drop_table=1),
        # stroke dropped (Condition entity). 12 - 2 = 10.
        assert len(df) == 10

    def test_output_matches_golden_file(self, tmp_path):
        """Compare full pipeline output against checked-in golden CSV."""
        output = tmp_path / "shortdata.csv"
        prepare_metadata(
            raw_files=[TEST_DATA / "raw_metadata.xlsx"],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
        )
        actual = pd.read_csv(output, dtype=str).fillna("")
        golden = pd.read_csv(TEST_DATA / "golden_pipeline_output.csv", dtype=str).fillna("")

        # Sort both deterministically before comparison so row order doesn't matter.
        sort_cols = ["cohort", "bdchm_varname", "phv"]
        actual = actual.sort_values(sort_cols).reset_index(drop=True)
        golden = golden.sort_values(sort_cols).reset_index(drop=True)
        actual = actual[sorted(actual.columns)]
        golden = golden[sorted(golden.columns)]

        pd.testing.assert_frame_equal(actual, golden)


# --- load_raw_data tests (sheet-name detection) ---


class TestLoadRawData:
    """Exercise the multi-file load + sheet selection path directly."""

    def test_loads_excel_default_sheet(self):
        """Loads the only sheet in the fixture file when no known_sheets match."""
        df = load_raw_data([TEST_DATA / "raw_metadata.xlsx"])
        assert not df.empty
        # standardize_raw_data hasn't run yet, so var_id is still the raw column
        assert "var_id" in df.columns or "data_table_id" in df.columns

    def test_returns_empty_for_no_files(self):
        """Empty input list returns an empty DataFrame instead of erroring."""
        assert load_raw_data([]).empty

    def test_concatenates_multiple_files(self, tmp_path):
        """Two copies of the same fixture concatenate; duplicates are dropped."""
        first = pd.read_excel(TEST_DATA / "raw_metadata.xlsx")
        second_path = tmp_path / "second.xlsx"
        first.to_excel(second_path, index=False)

        combined = load_raw_data([TEST_DATA / "raw_metadata.xlsx", second_path])
        single = load_raw_data([TEST_DATA / "raw_metadata.xlsx"])
        # Duplicates dropped → same row count
        assert len(combined) == len(single)

    def test_known_sheets_param_selects_alternate_sheet(self, tmp_path):
        """Custom known_sheets list lets callers point at non-default sheet names."""
        custom_path = tmp_path / "custom.xlsx"
        with pd.ExcelWriter(custom_path) as writer:
            pd.DataFrame({"junk": [1]}).to_excel(writer, sheet_name="junk", index=False)
            pd.read_excel(TEST_DATA / "raw_metadata.xlsx").to_excel(writer, sheet_name="my_custom_sheet", index=False)

        # Without the override, the loader picks the first sheet ("junk").
        defaulted = load_raw_data([custom_path])
        assert "junk" in defaulted.columns

        # With the override, the loader picks the named sheet.
        overridden = load_raw_data([custom_path], known_sheets=["my_custom_sheet"])
        assert "var_id" in overridden.columns or "data_table_id" in overridden.columns


# --- Parameterization regression tests ---


class TestParameterization:
    """Verify newly-added parameters work without changing default behavior."""

    def test_unit_conversions_custom_sheet_names(self, tmp_path):
        """load_unit_conversions accepts custom sheet names."""
        renamed = tmp_path / "renamed_unit_key.xlsx"
        original = pd.ExcelFile(TEST_DATA / "unit_key.xlsx")
        with pd.ExcelWriter(renamed) as writer:
            pd.read_excel(original, sheet_name="conversions").to_excel(writer, sheet_name="my_conv", index=False)
            pd.read_excel(original, sheet_name="ucum").to_excel(writer, sheet_name="my_ucum", index=False)
            pd.read_excel(original, sheet_name="equivalencies").to_excel(writer, sheet_name="my_equiv", index=False)

        conv = load_unit_conversions(renamed, conversions_sheet="my_conv", ucum_sheet="my_ucum")
        assert "unit_merge_key" in conv.columns

        equiv = load_unit_equivalencies(renamed, equivalencies_sheet="my_equiv")
        assert "unit_merge_key" in equiv.columns

    def test_entity_filter_none_keeps_all_entities(self, docs):
        """When entity_filter=None, Condition rows are not dropped."""
        df = pd.DataFrame(
            [
                _make_clean_row(),
                _make_clean_row(
                    bdchm_label="stroke",
                    merge_bdchm_label="stroke",
                    bdchm_entity="Condition",
                ),
            ]
        )
        result = merge_data_docs(df, **docs, entity_filter=None)
        assert "Condition" in result["bdchm_entity"].values
        assert "MeasurementObservation" in result["bdchm_entity"].values

    def test_entity_filter_custom_value(self, docs):
        """Custom entity_filter value selects rows with that entity only."""
        df = pd.DataFrame(
            [
                _make_clean_row(),
                _make_clean_row(
                    bdchm_label="stroke",
                    merge_bdchm_label="stroke",
                    bdchm_entity="Condition",
                ),
            ]
        )
        result = merge_data_docs(df, **docs, entity_filter="Condition")
        assert (result["bdchm_entity"] == "Condition").all()

    def test_prepare_metadata_passes_known_sheets_through(self, tmp_path):
        """prepare_metadata threads known_sheets to load_raw_data."""
        custom_path = tmp_path / "custom.xlsx"
        with pd.ExcelWriter(custom_path) as writer:
            pd.DataFrame({"junk": [1]}).to_excel(writer, sheet_name="junk", index=False)
            pd.read_excel(TEST_DATA / "raw_metadata.xlsx").to_excel(writer, sheet_name="real_data", index=False)

        output = tmp_path / "out.csv"
        result = prepare_metadata(
            raw_files=[custom_path],
            bdchv_defs_path=TEST_DATA / "bdchv_defs.csv",
            contextual_vars_path=TEST_DATA / "contextual_variables_key.csv",
            unit_key_path=TEST_DATA / "unit_key.xlsx",
            output_path=output,
            known_sheets=["real_data"],
        )
        assert result is not None
        df = pd.read_csv(output)
        assert len(df) > 0
