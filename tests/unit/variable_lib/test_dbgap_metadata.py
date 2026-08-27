"""Unit tests for variable_lib.dbgap_metadata slot filling."""

import logging
from pathlib import Path

import pytest

from dm_bip.variable_lib.classify import VariableKind
from dm_bip.variable_lib.datamodel.variable_lib import DataTypeEnum
from dm_bip.variable_lib.dbgap import DbgapVariable, load_tables
from dm_bip.variable_lib.dbgap_metadata import DbgapMetadata, _data_type, _ucum

FIXTURES = Path(__file__).parents[2] / "input" / "variable_lib" / "dbgap"
DEMO_DD = FIXTURES / "phs000280.v8.pht000001.v1.DEMO.data_dict.xml"
DEMO_VR = FIXTURES / "phs000280.v8.pht000001.v1.p2.DEMO.var_report.xml"

DATASET = "pht000001"
HEIGHT = "phv00000001"
SEX = "phv00000002"
YEAR = "phv00000003"
BOUNDED = "phv00000005"
SENTINEL = "phv00000006"


def _always(kind):
    """Build a stub classifier that answers the same way for every variable."""
    return lambda dataset, accession: kind


@pytest.fixture()
def tables():
    """Provide the demo table, data_dict merged with var_report."""
    return load_tables([(DEMO_DD, DEMO_VR)])


@pytest.fixture()
def continuous(tables):
    """Provide a metadata source whose classifier calls everything continuous."""
    return DbgapMetadata(tables, _always(VariableKind.continuous))


@pytest.fixture()
def categorical(tables):
    """Provide a metadata source whose classifier calls everything categorical."""
    return DbgapMetadata(tables, _always(VariableKind.categorical))


class TestUcum:
    """Units are normalized where the table knows them and left alone where it does not."""

    def test_normalizes_a_known_unit(self):
        """DbGaP spells years out; UCUM does not."""
        assert _ucum("Years") == "a"

    def test_passes_an_unknown_unit_through_unchanged(self):
        """normalize_unit would return the lowercased lookup key here, corrupting the unit."""
        assert _ucum("SI") == "SI"

    def test_passes_a_unit_that_is_already_ucum(self):
        """Absent from the table is not the same as wrong."""
        assert _ucum("cm") == "cm"

    def test_no_unit_is_none(self):
        """An unset unit stays unset rather than becoming an empty string."""
        assert _ucum(None) is None
        assert _ucum("") is None


class TestDataType:
    """calculated_type is preferred; the declared type is the fallback."""

    @pytest.mark.parametrize(
        ("calculated", "expected"),
        [
            ("integer", DataTypeEnum.integer),
            ("decimal", DataTypeEnum.decimal),
            ("enum_integer", DataTypeEnum.enum),
            ("string", DataTypeEnum.string),
        ],
    )
    def test_maps_every_observed_calculated_type(self, calculated, expected):
        """These four are the whole vocabulary across the ARIC var_reports."""
        variable = DbgapVariable(accession="phv1", versioned_id="phv1.v1", calculated_type=calculated)
        assert _data_type(variable) == expected

    @pytest.mark.parametrize(
        ("reported", "expected"),
        [
            ("encoded value", DataTypeEnum.code),
            ("continuous integer", DataTypeEnum.numeric),
            ("decimal", DataTypeEnum.numeric),
            ("string", DataTypeEnum.string),
        ],
    )
    def test_falls_back_to_the_declared_type(self, reported, expected):
        """Without a var_report the declared type still narrows the data type."""
        variable = DbgapVariable(accession="phv1", versioned_id="phv1.v1", reported_type=reported)
        assert _data_type(variable) == expected

    def test_unrecognized_calculated_type_warns_and_falls_back(self, caplog):
        """A study that widens the vocabulary must surface, not be silently mistyped."""
        variable = DbgapVariable(
            accession="phv1", versioned_id="phv1.v1", calculated_type="quaternion", reported_type="decimal"
        )
        with caplog.at_level(logging.WARNING):
            assert _data_type(variable) == DataTypeEnum.numeric
        assert "Unrecognized dbGaP calculated_type" in caplog.text

    def test_no_type_at_all_is_none(self):
        """Nothing to go on yields nothing, rather than a guess."""
        assert _data_type(DbgapVariable(accession="phv1", versioned_id="phv1.v1")) is None


class TestCommonSlots:
    """Some slots are filled the same way whichever class an entry takes."""

    def test_fills_name_description_and_file(self, continuous):
        """These come straight off the declared dictionary."""
        fields = continuous.lookup(DATASET, HEIGHT)
        assert fields["variable_name"] == "HEIGHT"
        assert fields["source_variable_description"].startswith("Standing height")
        assert fields["file_name"] == "DEMO"
        assert fields["comment"] == "Measured to the nearest cm."

    def test_never_returns_associated_study(self, continuous, categorical):
        """Emit merges this over identity, so returning it would overwrite the spec's study."""
        assert "associated_study" not in continuous.lookup(DATASET, HEIGHT)
        assert "associated_study" not in categorical.lookup(DATASET, SEX)

    def test_unset_slots_are_omitted(self, continuous):
        """A variable with no comment yields no comment key, rather than an explicit None."""
        assert "comment" not in continuous.lookup(DATASET, BOUNDED)


class TestContinuousSlots:
    """The continuous class takes bounds and a unit, and has no coded_values."""

    def test_bounds_come_from_the_observed_stat(self, continuous):
        """var_report's stat is the only place observed min and max exist."""
        fields = continuous.lookup(DATASET, HEIGHT)
        assert (fields["minimum_value"], fields["maximum_value"]) == ("125", "199")

    def test_bounds_fall_back_to_declared_logical_limits(self, continuous):
        """A variable whose report carries no stat still has its declared bounds."""
        fields = continuous.lookup(DATASET, BOUNDED)
        assert (fields["minimum_value"], fields["maximum_value"]) == ("10", "99")

    def test_unit_is_normalized(self, continuous):
        """The sentinel variable declares Years, which UCUM spells a."""
        assert continuous.lookup(DATASET, SENTINEL)["unit"] == "a"

    def test_coded_values_are_not_offered(self, continuous):
        """SingleContinuousVariable has no such slot; returning it would warn on every entry."""
        assert "coded_values" not in continuous.lookup(DATASET, SENTINEL)

    def test_codes_on_a_numeric_variable_become_missing_values(self, continuous):
        """They are out-of-band markers, not the variable's domain, and must not be dropped."""
        missing = continuous.lookup(DATASET, SENTINEL)["missing_value"]
        assert [(m.indicator_char, m.indicator_meaning) for m in missing] == [("5", "Transport condition")]

    def test_no_codes_means_no_missing_value(self, continuous):
        """Most continuous variables carry none."""
        assert "missing_value" not in continuous.lookup(DATASET, HEIGHT)


class TestCategoricalSlots:
    """The categorical class takes coded values, and has no bounds or unit."""

    def test_coded_values_keep_document_order(self, categorical):
        """The fixture lists Female before Male; sorting would lose the study's ordering."""
        coded = categorical.lookup(DATASET, SEX)["coded_values"]
        assert [(c.indicator_char, c.indicator_meaning) for c in coded] == [("2", "Female"), ("1", "Male")]

    def test_a_value_without_a_code_becomes_the_indicator(self, categorical):
        """In a bare <value>1986</value> the text is the value, not a label for one."""
        coded = categorical.lookup(DATASET, YEAR)["coded_values"]
        assert [(c.indicator_char, c.indicator_meaning) for c in coded] == [("1986", None)]

    def test_continuous_only_slots_are_not_offered(self, categorical):
        """SingleCategoricalVariable has none of these."""
        fields = categorical.lookup(DATASET, HEIGHT)
        assert not {"minimum_value", "maximum_value", "unit"} & set(fields)


class TestLookupMisses:
    """A variable the dictionaries do not describe is a real condition, not an error."""

    def test_unknown_dataset(self, continuous, caplog):
        """A spec may name a pht dbGaP does not publish."""
        with caplog.at_level(logging.DEBUG):
            assert continuous.lookup("pht999999", HEIGHT) == {}
        assert "No dbGaP data dictionary" in caplog.text

    def test_unknown_accession(self, continuous, caplog):
        """A spec may name a phv the table does not declare."""
        with caplog.at_level(logging.DEBUG):
            assert continuous.lookup(DATASET, "phv99999999") == {}
        assert "does not declare" in caplog.text

    def test_unclassified_variables_get_only_the_common_slots(self, tables):
        """When the classifier cannot type it, emit holds it back; offer nothing class-specific."""
        metadata = DbgapMetadata(tables, _always(VariableKind.unknown))
        fields = metadata.lookup(DATASET, HEIGHT)
        assert fields["variable_name"] == "HEIGHT"
        assert not {"minimum_value", "unit", "coded_values"} & set(fields)


class TestDegradedMode:
    """Without a var_report the descriptive slots still fill; the observed bounds do not."""

    @pytest.fixture()
    def continuous_dd_only(self):
        """Provide a metadata source built from the data dictionary alone."""
        return DbgapMetadata(load_tables([(DEMO_DD, None)]), _always(VariableKind.continuous))

    def test_declared_slots_survive(self, continuous_dd_only):
        """Name, description, unit, and comment are all data_dict-only anyway."""
        fields = continuous_dd_only.lookup(DATASET, HEIGHT)
        assert fields["variable_name"] == "HEIGHT"
        assert fields["unit"] == "cm"

    def test_observed_bounds_are_lost(self, continuous_dd_only):
        """Losing these is the cost of --no-var-report, and why it is not the default."""
        assert "minimum_value" not in continuous_dd_only.lookup(DATASET, HEIGHT)

    def test_data_type_degrades_to_the_declared_type(self, continuous_dd_only):
        """HEIGHT is declared string, so without calculated_type it types as string."""
        assert continuous_dd_only.lookup(DATASET, HEIGHT)["data_type"] == DataTypeEnum.string


class TestDeterminism:
    """Two runs over the same inputs must produce the same entries."""

    def test_repeated_lookups_are_identical(self, tables):
        """Nothing here may depend on dict iteration order or object identity."""
        first = DbgapMetadata(tables, _always(VariableKind.categorical)).lookup(DATASET, SEX)
        second = DbgapMetadata(tables, _always(VariableKind.categorical)).lookup(DATASET, SEX)
        assert [(c.indicator_char, c.indicator_meaning) for c in first["coded_values"]] == [
            (c.indicator_char, c.indicator_meaning) for c in second["coded_values"]
        ]
        assert {k: v for k, v in first.items() if k != "coded_values"} == {
            k: v for k, v in second.items() if k != "coded_values"
        }
