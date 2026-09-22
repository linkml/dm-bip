"""Unit tests for variable_lib.dbgap digest XML reading."""

import logging
from pathlib import Path

import pytest

from dm_bip.variable_lib.dbgap import (
    CodedValue,
    _bare,
    load_tables,
    merge_var_report,
    read_data_dict,
)

FIXTURES = Path(__file__).parents[2] / "input" / "variable_lib" / "dbgap"
DEMO_DD = FIXTURES / "phs000280.v8.pht000001.v1.DEMO.data_dict.xml"
DEMO_VR = FIXTURES / "phs000280.v8.pht000001.v1.p2.DEMO.var_report.xml"
FOREIGN_DD = FIXTURES / "phs000090.v8.pht000002.v1.FOREIGN.data_dict.xml"


@pytest.fixture()
def merged():
    """Provide the demo table with its var_report folded in."""
    table = read_data_dict(DEMO_DD)
    merge_var_report(table, DEMO_VR)
    return table


class TestBareAccession:
    """Accessions join on their stem, since specs are unversioned and dbGaP is not."""

    @pytest.mark.parametrize(
        ("versioned", "expected"),
        [
            ("phv00202843.v2", "phv00202843"),
            ("phv00202843.v2.p2", "phv00202843"),
            ("phv00202843.v2.p2.c1", "phv00202843"),
            ("pht004027.v3", "pht004027"),
            ("phv00202843", "phv00202843"),
        ],
    )
    def test_strips_every_suffix(self, versioned, expected):
        """Version, participant-set, and consent-group suffixes all come off."""
        assert _bare(versioned) == expected


class TestReadDataDict:
    """The declared dictionary supplies name, description, type, unit, bounds, and codes."""

    def test_table_identity(self):
        """Dataset key is the bare pht from the XML; study_id comes from the XML too."""
        table = read_data_dict(DEMO_DD)
        assert table.dataset == "pht000001"
        assert table.versioned_id == "pht000001.v1"
        assert table.study_id == "phs000280.v8"
        assert table.source_file == DEMO_DD.name

    def test_variables_keyed_by_bare_accession(self):
        """Variables index on the stem, matching what the transformation specs name."""
        table = read_data_dict(DEMO_DD)
        assert set(table.variables) == {
            "phv00000001",
            "phv00000002",
            "phv00000003",
            "phv00000004",
            "phv00000005",
            "phv00000006",
        }
        assert table.variables["phv00000001"].versioned_id == "phv00000001.v1"

    def test_reads_slots_schema_automator_drops(self):
        """unit, logical bounds, and comment are the reason this module exists."""
        table = read_data_dict(DEMO_DD)
        height = table.variables["phv00000001"]
        assert height.unit == "cm"
        assert height.comment == "Measured to the nearest cm."
        bounded = table.variables["phv00000005"]
        assert (bounded.logical_min, bounded.logical_max) == ("10", "99")

    def test_coded_values_keep_document_order(self):
        """Values are ordered meaningfully by dbGaP, so the reader must not sort them."""
        table = read_data_dict(DEMO_DD)
        assert table.variables["phv00000002"].values == [
            CodedValue(code="2", label="Female"),
            CodedValue(code="1", label="Male"),
        ]

    def test_value_without_a_code_keeps_its_text(self):
        """A bare <value>1986</value> carries the value itself, so nothing may be dropped."""
        table = read_data_dict(DEMO_DD)
        assert table.variables["phv00000003"].values == [CodedValue(code=None, label="1986")]

    def test_duplicate_codes_are_preserved(self):
        """Echoing a dbGaP defect faithfully beats silently disagreeing with dbGaP."""
        table = read_data_dict(DEMO_DD)
        assert table.variables["phv00000004"].values == [
            CodedValue(code="1", label="Yes"),
            CodedValue(code="1", label="Affirmative"),
        ]

    def test_var_report_only_fields_are_unset(self):
        """Without a var_report there is no calculated_type, no observed bounds, no name."""
        table = read_data_dict(DEMO_DD)
        height = table.variables["phv00000001"]
        assert height.calculated_type is None
        assert (height.stat_min, height.stat_max) == (None, None)
        assert table.table_name is None

    def test_foreign_study_id_is_read_as_published(self):
        """A cohort's listing includes other studies' tables; they are content, not errors."""
        table = read_data_dict(FOREIGN_DD)
        assert table.dataset == "pht000002"
        assert table.study_id == "phs000090.v8"


class TestMergeVarReport:
    """The empirical report supplies calculated_type, observed bounds, and the table name."""

    def test_table_name_comes_from_var_report(self, merged):
        """The data_dict root has no name attribute at all; only var_report does."""
        assert merged.table_name == "DEMO"

    def test_adds_calculated_type_and_observed_bounds(self, merged):
        """These are what a declared dictionary cannot say."""
        height = merged.variables["phv00000001"]
        assert height.calculated_type == "integer"
        assert (height.stat_min, height.stat_max) == ("125", "199")

    def test_consent_group_rows_are_ignored(self, merged):
        """The .c1 row reports min=130; taking it would understate the true range."""
        assert merged.variables["phv00000001"].stat_min == "125"

    def test_missing_stat_leaves_bounds_unset(self, merged):
        """A row with no stat element must not clobber the declared logical bounds."""
        bounded = merged.variables["phv00000005"]
        assert bounded.calculated_type == "integer"
        assert (bounded.stat_min, bounded.stat_max) == (None, None)
        assert (bounded.logical_min, bounded.logical_max) == ("10", "99")

    def test_undeclared_variables_are_not_added(self, merged, caplog):
        """The declared dictionary is the authority on which columns exist."""
        with caplog.at_level(logging.DEBUG):
            merge_var_report(merged, DEMO_VR)
        assert "phv00009999" not in merged.variables
        assert "absent from the data dictionary" in caplog.text

    def test_declared_fields_survive_the_merge(self, merged):
        """Merging adds to the declared view rather than replacing it."""
        height = merged.variables["phv00000001"]
        assert height.unit == "cm"
        assert height.reported_type == "string"


class TestLoadTables:
    """Pairs are read into one index keyed by bare pht."""

    def test_indexes_by_dataset(self):
        """Both fixtures land under the pht their XML declares."""
        tables = load_tables([(DEMO_DD, DEMO_VR), (FOREIGN_DD, None)])
        assert set(tables) == {"pht000001", "pht000002"}
        assert tables["pht000001"].table_name == "DEMO"

    def test_var_report_is_optional(self):
        """data_dict-only mode is a supported degraded path, not an error."""
        tables = load_tables([(DEMO_DD, None)])
        assert tables["pht000001"].variables["phv00000001"].calculated_type is None

    def test_duplicate_dataset_keeps_the_first(self, caplog):
        """Two files declaring one pht is a dbGaP anomaly; resolve it deterministically."""
        with caplog.at_level(logging.WARNING):
            tables = load_tables([(DEMO_DD, DEMO_VR), (DEMO_DD, None)])
        assert tables["pht000001"].table_name == "DEMO"
        assert "keeping the first" in caplog.text

    def test_accepts_unsortable_pairs(self):
        """A None var_report must not break the sort that keeps loading deterministic."""
        tables = load_tables([(FOREIGN_DD, None), (DEMO_DD, DEMO_VR)])
        assert set(tables) == {"pht000001", "pht000002"}
