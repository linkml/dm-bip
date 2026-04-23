"""Tests for the metadata preparation pipeline (Stata steps 1-4 port)."""

from pathlib import Path

import pandas as pd
import pytest

from dm_bip.trans_spec_gen.prepare_metadata import (
    clean_data,
    load_bdchv_defs,
    load_contextual_vars,
    load_unit_conversions,
    load_unit_equivalencies,
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
        """Unknown values pass through unchanged."""
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
        if not sleep.empty:
            assert sleep.iloc[0]["var_units"] == "h"

    def test_infers_bmi_unit(self, standardized_df):
        """Infers 'kg/m2' unit from description containing kg/m2."""
        result = clean_data(standardized_df)
        bmi = result[result["bdchm_label"] == "bmi"]
        if not bmi.empty:
            assert bmi.iloc[0]["var_units"] == "kg/m2"

    def test_infers_alcohol_weekly_unit(self, standardized_df):
        """Infers '{#}/wk' unit for alcohol servings from 'per week' description."""
        result = clean_data(standardized_df)
        alcohol = result[result["bdchm_label"] == "alcohol servings"]
        if not alcohol.empty:
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
        if not albumin.empty:
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
        if not height.empty:
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
        # At least some rows should be good
        assert df["row_good"].sum() > 0
        # Rows with unit handling and pht should be good
        albumin = df[df["bdchm_varname"] == "albumin_bld"]
        if not albumin.empty:
            aric_albumin = albumin[albumin["cohort"] == "aric"]
            if not aric_albumin.empty:
                assert aric_albumin.iloc[0]["row_good"] == 1
