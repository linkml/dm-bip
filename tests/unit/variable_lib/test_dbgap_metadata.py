"""Unit tests for variable_lib.dbgap_metadata slot filling from canonical DD TSVs."""

import logging
from pathlib import Path

import pytest

from dm_bip.variable_lib.classify import VariableKind
from dm_bip.variable_lib.datamodel.variable_lib import DataTypeEnum
from dm_bip.variable_lib.dbgap_metadata import (
    Code,
    DbgapMetadata,
    DdEntry,
    _continuous_slots,
    _data_type,
    _ucum,
    load_tables,
    read_dd,
    table_name_from_filename,
    tables_from_digests,
)

FIXTURES = Path(__file__).parents[2] / "input" / "variable_lib" / "dd"
DEMO_DD = FIXTURES / "phs000280.v8.pht000001.v1.DEMO.dd.tsv"

DATASET = "pht000001"
HEIGHT = "phv00000001"
SEX = "phv00000002"
YEAR = "phv00000003"
DUPCODE = "phv00000004"
BOUNDED = "phv00000005"
SENTINEL = "phv00000006"

# The eight columns today's adapter writes, before comment and missing_values land upstream.
ADAPTER_COLUMNS = ["name", "type", "description", "codes", "unit", "min", "max", "uri"]


def _always(kind):
    """Build a stub classifier that answers the same way for every variable."""
    return lambda dataset, accession: kind


def _write_dd(directory: Path, filename: str, columns: list[str], rows: list[list[str]]) -> Path:
    """Write a small DD TSV and return its path."""
    path = directory / filename
    lines = ["\t".join(columns)] + ["\t".join(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture()
def tables():
    """Provide the demo table, as the adapter should write it once it carries every column."""
    return load_tables([DEMO_DD])


@pytest.fixture()
def continuous(tables):
    """Provide a metadata source whose classifier calls everything continuous."""
    return DbgapMetadata(tables, _always(VariableKind.continuous))


@pytest.fixture()
def categorical(tables):
    """Provide a metadata source whose classifier calls everything categorical."""
    return DbgapMetadata(tables, _always(VariableKind.categorical))


class TestTableNameFromFilename:
    """The pipeline names each DD after its data_dict, which carries dbGaP's table name."""

    def test_pipeline_naming(self):
        """The segment between the pht version and the .dd suffix is the table name."""
        assert table_name_from_filename("phs000280.v8.pht004027.v3.ABI04.dd.tsv") == "ABI04"

    def test_adapter_default_naming_has_none(self):
        """The adapter's own default output name carries no table name."""
        assert table_name_from_filename("phs000280.pht000001.dd.tsv") is None


class TestReadDd:
    """A DD file becomes a table keyed by bare accession, with the codes grammar parsed."""

    def test_table_identity_comes_from_the_filename(self, tables):
        """DD rows name variables but not their table, so the filename is the only source."""
        table = tables[DATASET]
        assert (table.dataset, table.table_name, table.source_file) == (DATASET, "DEMO", DEMO_DD.name)

    def test_entries_keyed_by_bare_accession(self, tables):
        """The uri cell is versioned; transformation specs are not."""
        assert set(tables[DATASET].entries) == {HEIGHT, SEX, YEAR, DUPCODE, BOUNDED, SENTINEL}

    def test_codes_keep_document_order(self, tables):
        """The grammar is parsed, not split; order is the adapter's, which is dbGaP's."""
        assert tables[DATASET].entries[SEX].codes == [Code("2", "Female"), Code("1", "Male")]

    def test_a_bareword_code_has_no_label(self, tables):
        """The bare <value>1986</value> that dbGaP emits serializes as a bareword token."""
        assert tables[DATASET].entries[YEAR].codes == [Code("1986")]

    def test_duplicate_codes_are_preserved(self, tables):
        """Two labels for one code, as dbGaP sometimes publishes, are both kept."""
        assert [c.code for c in tables[DATASET].entries[DUPCODE].codes] == ["1", "1"]

    def test_optional_columns_are_tolerated(self, tmp_path):
        """A DD written by today's adapter has neither comment nor missing_values."""
        path = _write_dd(
            tmp_path,
            "phs1.v1.pht000009.v1.T.dd.tsv",
            ADAPTER_COLUMNS,
            [["X", "integer", "d", "", "cm", "1", "2", "dbgap:phv00000009.v1"]],
        )
        entry = read_dd(path).entries["phv00000009"]
        assert (entry.comment, entry.missing_values) == (None, [])

    def test_a_missing_required_column_is_an_error(self, tmp_path):
        """A file that is not a canonical DD must fail, not quietly fill nothing."""
        path = _write_dd(tmp_path, "phs1.v1.pht000009.v1.T.dd.tsv", ["name", "type"], [["X", "integer"]])
        with pytest.raises(ValueError, match="missing column"):
            read_dd(path)

    def test_a_row_without_a_phv_uri_is_skipped(self, tmp_path, caplog):
        """There is nothing to join such a row to."""
        path = _write_dd(
            tmp_path,
            "phs1.v1.pht000009.v1.T.dd.tsv",
            ADAPTER_COLUMNS,
            [["X", "integer", "d", "", "", "", "", ""]],
        )
        with caplog.at_level(logging.WARNING):
            assert read_dd(path).entries == {}
        assert "no dbgap:phv uri" in caplog.text

    def test_an_unparsable_codes_cell_warns_and_yields_nothing(self, tmp_path, caplog):
        """An empty token violates the grammar; the rest of the row still loads."""
        path = _write_dd(
            tmp_path,
            "phs1.v1.pht000009.v1.T.dd.tsv",
            ADAPTER_COLUMNS,
            [["X", "permissible_values", "d", "1, Yes ||", "", "", "", "dbgap:phv00000009.v1"]],
        )
        with caplog.at_level(logging.WARNING):
            entry = read_dd(path).entries["phv00000009"]
        assert entry.codes == []
        assert entry.name == "X"
        assert "Unparsable codes" in caplog.text


class TestLoadTables:
    """Tables are indexed by the pht in the filename."""

    def test_indexes_by_dataset(self, tables):
        """One table, keyed by its bare pht."""
        assert list(tables) == [DATASET]

    def test_a_file_without_a_pht_is_skipped(self, tmp_path, caplog):
        """Nothing could ever look it up."""
        path = _write_dd(tmp_path, "notes.dd.tsv", ADAPTER_COLUMNS, [])
        with caplog.at_level(logging.WARNING):
            assert load_tables([path]) == {}
        assert "names no pht" in caplog.text

    def test_duplicate_dataset_keeps_the_first(self, tmp_path, caplog):
        """The pipeline writes one DD per table; a second is a stray."""
        first = _write_dd(tmp_path, "a.pht000009.v1.T.dd.tsv", ADAPTER_COLUMNS, [])
        second = _write_dd(tmp_path, "b.pht000009.v1.T.dd.tsv", ADAPTER_COLUMNS, [])
        with caplog.at_level(logging.WARNING):
            tables = load_tables([second, first])
        assert tables["pht000009"].source_file == first.name
        assert "second DD" in caplog.text


class TestUcum:
    """Units are normalized where the table knows them and left alone where it does not."""

    def test_normalizes_a_known_unit(self):
        """Years is spelled out by dbGaP; UCUM spells it a."""
        assert _ucum("Years") == "a"

    def test_passes_an_unknown_unit_through_unchanged(self):
        """normalize_unit would return the lowercased lookup key here, corrupting the unit."""
        assert _ucum("SI") == "SI"

    def test_passes_a_unit_that_is_already_ucum(self):
        """Absent from the table is not the same as wrong."""
        assert _ucum("cm") == "cm"

    def test_the_none_token_is_unitless(self):
        """The DD spec's explicit declaration of no unit yields no unit."""
        assert _ucum("none") is None

    def test_no_unit_is_none(self):
        """An unset unit stays unset rather than becoming an empty string."""
        assert _ucum(None) is None
        assert _ucum("") is None


class TestDataType:
    """The DD's canonical type vocabulary maps onto the BDC enum."""

    @pytest.mark.parametrize(
        ("dd_type", "expected"),
        [
            ("integer", DataTypeEnum.integer),
            ("decimal", DataTypeEnum.decimal),
            ("permissible_values", DataTypeEnum.enum),
            ("string", DataTypeEnum.string),
            ("boolean", DataTypeEnum.boolean),
            ("date", DataTypeEnum.string),
        ],
    )
    def test_maps_the_canonical_vocabulary(self, dd_type, expected):
        """Every DD type lands somewhere; temporal types have no BDC home beyond string."""
        assert _data_type(DdEntry(accession="phv1", data_type=dd_type)) == expected

    def test_unrecognized_type_warns(self, caplog):
        """A DD that widens the vocabulary must surface, not be silently mistyped."""
        with caplog.at_level(logging.WARNING):
            assert _data_type(DdEntry(accession="phv1", data_type="quaternion")) is None
        assert "Unrecognized DD type" in caplog.text

    def test_no_type_at_all_is_none(self):
        """Nothing to go on yields nothing, rather than a guess."""
        assert _data_type(DdEntry(accession="phv1")) is None


class TestCommonSlots:
    """Some slots are filled the same way whichever class an entry takes."""

    def test_fills_name_description_file_and_comment(self, continuous):
        """Name and description are DD columns; the table name comes from the filename."""
        fields = continuous.lookup(DATASET, HEIGHT)
        assert fields["variable_name"] == "HEIGHT"
        assert fields["source_variable_description"].startswith("Standing height")
        assert fields["file_name"] == "DEMO"
        assert fields["comment"] == "Measured to the nearest cm."

    def test_data_type_comes_from_the_dd(self, continuous):
        """HEIGHT is declared string in dbGaP; the adapter resolved it to integer."""
        assert continuous.lookup(DATASET, HEIGHT)["data_type"] == DataTypeEnum.integer

    def test_never_returns_associated_study(self, continuous, categorical):
        """Emit merges this over identity, so returning it would overwrite the spec's study."""
        assert "associated_study" not in continuous.lookup(DATASET, HEIGHT)
        assert "associated_study" not in categorical.lookup(DATASET, SEX)

    def test_unset_slots_are_omitted(self, continuous):
        """A variable with no comment yields no comment key, rather than an explicit None."""
        assert "comment" not in continuous.lookup(DATASET, BOUNDED)


class TestContinuousSlots:
    """The continuous class takes bounds and a unit, and has no coded_values."""

    def test_bounds_come_from_the_dd(self, continuous):
        """The adapter has already chosen between observed and declared bounds."""
        fields = continuous.lookup(DATASET, HEIGHT)
        assert (fields["minimum_value"], fields["maximum_value"]) == ("125", "199")

    def test_declared_bounds_arrive_the_same_way(self, continuous):
        """BOUNDED has only logical limits upstream; by the DD they are just min and max."""
        fields = continuous.lookup(DATASET, BOUNDED)
        assert (fields["minimum_value"], fields["maximum_value"]) == ("10", "99")

    def test_unit_is_normalized(self, continuous):
        """The sentinel variable declares Years, which UCUM spells a."""
        assert continuous.lookup(DATASET, SENTINEL)["unit"] == "a"

    def test_the_none_unit_token_is_omitted(self, continuous):
        """BOUNDED declares itself unitless with the DD's none token."""
        assert "unit" not in continuous.lookup(DATASET, BOUNDED)

    def test_coded_values_are_not_offered(self, continuous):
        """SingleContinuousVariable has no such slot; returning it would warn on every entry."""
        assert "coded_values" not in continuous.lookup(DATASET, SENTINEL)

    def test_sentinels_come_from_the_missing_values_column(self, continuous):
        """They are out-of-band markers, not the variable's domain, and must not be dropped."""
        missing = continuous.lookup(DATASET, SENTINEL)["missing_value"]
        assert [(m.indicator_char, m.indicator_meaning) for m in missing] == [("5", "Transport condition")]

    def test_sentinels_fall_back_to_codes_without_that_column(self, tmp_path):
        """Today's adapter types a numeric variable with codes as permissible_values."""
        path = _write_dd(
            tmp_path,
            "phs1.v1.pht000009.v1.T.dd.tsv",
            ADAPTER_COLUMNS,
            [["S", "permissible_values", "d", "5, Transport condition", "", "", "", "dbgap:phv00000009.v1"]],
        )
        metadata = DbgapMetadata(load_tables([path]), _always(VariableKind.continuous))
        missing = metadata.lookup("pht000009", "phv00000009")["missing_value"]
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

    def test_a_bareword_code_becomes_the_indicator(self, categorical):
        """In a bare <value>1986</value> the text is the value, not a label for one."""
        coded = categorical.lookup(DATASET, YEAR)["coded_values"]
        assert [(c.indicator_char, c.indicator_meaning) for c in coded] == [("1986", None)]

    def test_continuous_only_slots_are_not_offered(self, categorical):
        """SingleCategoricalVariable has none of these."""
        fields = categorical.lookup(DATASET, HEIGHT)
        assert not {"minimum_value", "maximum_value", "unit", "missing_value"} & set(fields)


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


class TestBounds:
    """The schema's bounds are decimals; the DD may say none, and a hand-edited one may be censored."""

    @staticmethod
    def _entry(**kwargs):
        """Build a bare entry carrying only the bounds under test."""
        return DdEntry(accession="phv1", **kwargs)

    def test_the_none_token_is_unbounded(self):
        """An explicit none is a declaration, not a value, and is not warned about."""
        slots = _continuous_slots(self._entry(min="none", max="99"))
        assert (slots["minimum_value"], slots["maximum_value"]) == (None, "99")

    def test_a_top_coded_maximum_is_dropped(self):
        """ARIC publishes max=">89" on age variables; decimal cannot hold it."""
        slots = _continuous_slots(self._entry(min="45", max=">89"))
        assert slots["maximum_value"] is None

    def test_the_rest_of_the_entry_survives(self):
        """Only the unrepresentable bound goes; the opposite bound is untouched."""
        slots = _continuous_slots(self._entry(min="45", max=">89"))
        assert slots["minimum_value"] == "45"

    def test_a_censored_minimum_is_dropped_too(self):
        """Nothing about the rule is specific to maxima."""
        slots = _continuous_slots(self._entry(min="<18", max="99"))
        assert (slots["minimum_value"], slots["maximum_value"]) == (None, "99")

    @pytest.mark.parametrize("value", ["45", "-3", "72.53", "1e3"])
    def test_decimals_pass_through_unchanged(self, value):
        """Negative, fractional, and exponent forms are all valid decimals."""
        assert _continuous_slots(self._entry(max=value))["maximum_value"] == value

    def test_the_drop_is_logged_with_the_published_value(self, caplog):
        """Censoring that cannot reach the YAML must still be visible in the run."""
        with caplog.at_level(logging.WARNING):
            _continuous_slots(self._entry(max=">89"))
        assert ">89" in caplog.text
        assert "phv1" in caplog.text


DIGESTS = Path(__file__).parents[2] / "input" / "variable_lib" / "dbgap"
MATCHING_DD = DIGESTS / "phs000007.v35.pht004063.v1.MATCHING.data_dict.xml"
MATCHING_VR = DIGESTS / "phs000007.v35.pht004063.v1.p16.MATCHING.var_report.xml"
COLLIDING_DD = DIGESTS / "phs000007.v35.pht004063.v1.COLLIDING.data_dict.xml"

BAREWORD_XML = """<?xml version="1.0" encoding="UTF-8"?>
<data_table id="pht000009.v1" study_id="phs000280.v8" participant_set="2">
  <variable id="phv00000031.v1">
    <name>YEAR</name>
    <description>dbGaP emits the value with no code attribute.</description>
    <type>integer</type>
    <value>1986</value>
  </variable>
  <variable id="phv00000032.v1">
    <name>SEX</name>
    <description>Reported sex.</description>
    <type>encoded value</type>
    <value code="2">Female</value>
    <value code="1">Male</value>
  </variable>
</data_table>
"""


class TestTablesFromDigests:
    """The in-memory path yields the same table shape ``read_dd`` builds from a TSV."""

    @pytest.fixture()
    def matching(self):
        """Adapt the MATCHING pair, whose var_report carries observed bounds for BMI01."""
        return tables_from_digests([(MATCHING_DD, MATCHING_VR)])

    def test_indexes_by_dataset_and_names_the_table_from_the_data_dict(self, matching):
        """Identity comes from the data_dict filename, as it does from a DD filename."""
        table = matching["pht004063"]
        assert table.source_file == MATCHING_DD.name
        assert table.table_name == "MATCHING"

    def test_entries_are_keyed_by_bare_accession(self, matching):
        """The adapter writes a versioned CURIE; the join needs the bare phv."""
        entry = matching["pht004063"].entries["phv00204719"]
        assert entry.name == "BMI01"
        assert entry.data_type == "decimal"

    def test_bounds_arrive_as_strings_like_a_tsv_cell(self, matching):
        """The adapter returns numbers; a DD cell is text, and the slot filler expects text."""
        entry = matching["pht004063"].entries["phv00204719"]
        assert (entry.min, entry.max) == ("13.1", "61.2")

    def test_a_data_dict_alone_has_no_bounds(self):
        """Without a var_report there is nothing observed, so the bounds stay unset."""
        entry = tables_from_digests([(MATCHING_DD, None)])["pht004063"].entries["phv00204719"]
        assert (entry.min, entry.max) == (None, None)

    def test_a_bareword_value_is_the_code(self, tmp_path):
        """
        DbGaP's ``<value>1986</value>`` has no code attribute.

        The adapter hands it over as a label-only record, which its TSV serializer rejects.
        The DD grammar reads a bareword as the value itself, so that is what it becomes
        here, and coded values beside it keep their labels.
        """
        path = tmp_path / "phs000280.v8.pht000009.v1.BARE.data_dict.xml"
        path.write_text(BAREWORD_XML, encoding="utf-8")
        entries = tables_from_digests([(path, None)])["pht000009"].entries
        assert entries["phv00000031"].codes == [Code(code="1986", label=None)]
        assert entries["phv00000032"].codes == [Code(code="2", label="Female"), Code(code="1", label="Male")]

    def test_a_second_data_dict_for_a_dataset_is_skipped(self, caplog):
        """Two data_dicts naming one pht is a stray, not a choice; the first one read wins."""
        with caplog.at_level(logging.WARNING):
            tables = tables_from_digests([(COLLIDING_DD, None), (MATCHING_DD, None)])
        assert tables["pht004063"].source_file == COLLIDING_DD.name
        assert "second data_dict for pht004063" in caplog.text
