"""Tests for typing variables from the canonical data dictionary."""

import logging
from pathlib import Path

import pytest

from dm_bip.variable_lib.classify import VariableKind, classifier_for, classify_from_dd
from dm_bip.variable_lib.dbgap_metadata import load_tables

DEMO_DD = Path(__file__).parents[2] / "input" / "variable_lib" / "dd" / "phs000280.v8.pht000001.v1.DEMO.dd.tsv"
DEMO = "pht000001"

COLUMNS = ["name", "type", "description", "codes", "unit", "min", "max", "uri"]


def _dd(directory: Path, dataset: str, rows: list[tuple[str, str, str]]) -> dict:
    """Write a DD for ``dataset`` with (name, type, accession) rows, and load it."""
    path = directory / f"phs000007.v35.{dataset}.v1.TABLE.dd.tsv"
    lines = ["\t".join(COLUMNS)]
    for name, dd_type, accession in rows:
        lines.append("\t".join([name, dd_type, "", "", "", "", "", f"dbgap:{accession}.v1"]))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return load_tables([path])


@pytest.fixture()
def demo():
    """Provide the DEMO table, which covers the adapter's vocabulary as it should emit it."""
    return load_tables([DEMO_DD])


class TestClassifyFromDd:
    """The DD type is the adapter's decision; this only maps its vocabulary onto two classes."""

    @pytest.mark.parametrize(
        ("accession", "kind"),
        [
            ("phv00000001", VariableKind.continuous),  # HEIGHT, integer
            ("phv00000005", VariableKind.continuous),  # BOUNDED, integer with declared bounds
            ("phv00000006", VariableKind.continuous),  # SENTINEL, integer carrying a sentinel code
            ("phv00000002", VariableKind.categorical),  # SEX, permissible_values
            ("phv00000003", VariableKind.categorical),  # YEAR, permissible_values with a bareword code
        ],
    )
    def test_maps_the_demo_table(self, demo, accession, kind):
        """Numeric DD types are continuous; coded ones are categorical."""
        assert classify_from_dd(demo, DEMO, accession) is kind

    def test_maps_the_rest_of_the_vocabulary(self, tmp_path):
        """``decimal`` is the other quantity; boolean, string and temporal types are labels."""
        tables = _dd(
            tmp_path,
            "pht000002",
            [
                ("A", "decimal", "phv00000011"),
                ("B", "boolean", "phv00000012"),
                ("C", "string", "phv00000013"),
                ("D", "date", "phv00000014"),
                ("E", "Integer", "phv00000015"),
            ],
        )
        kinds = {acc: classify_from_dd(tables, "pht000002", acc) for acc in [f"phv0000001{i}" for i in range(1, 6)]}
        assert kinds == {
            "phv00000011": VariableKind.continuous,
            "phv00000012": VariableKind.categorical,
            "phv00000013": VariableKind.categorical,
            "phv00000014": VariableKind.categorical,
            "phv00000015": VariableKind.continuous,
        }

    def test_a_variable_the_dd_lacks_is_unknown(self, demo):
        """Absent entry or absent table: nothing to read, so nothing is asserted."""
        assert classify_from_dd(demo, DEMO, "phv99999999") is VariableKind.unknown
        assert classify_from_dd(demo, "pht999999", "phv00000001") is VariableKind.unknown

    def test_an_entry_without_a_type_is_unknown(self, tmp_path):
        """An untyped row is not a label by default; it is undecided."""
        tables = _dd(tmp_path, "pht000003", [("A", "", "phv00000021")])
        assert classify_from_dd(tables, "pht000003", "phv00000021") is VariableKind.unknown


class TestClassifierFor:
    """A classifier is a dictionary index, or nothing."""

    def test_types_what_the_dictionary_describes(self, demo, caplog):
        """Described variables get a class; undescribed ones stay unknown, without complaint."""
        with caplog.at_level(logging.WARNING):
            classify = classifier_for(demo)
        assert classify(DEMO, "phv00000001") is VariableKind.continuous
        assert classify(DEMO, "phv99999999") is VariableKind.unknown
        assert "cannot be typed" not in caplog.text

    @pytest.mark.parametrize("tables", [None, {}])
    def test_warns_when_there_is_no_dictionary(self, tables, caplog):
        """With nothing to read, every variable would be held back, and the run should say so."""
        with caplog.at_level(logging.WARNING):
            classify = classifier_for(tables)
        assert classify(DEMO, "phv00000001") is VariableKind.unknown
        assert "cannot be typed" in caplog.text
