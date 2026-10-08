"""Tests for classifying variables and expressing them as variable library entries."""

import logging
from pathlib import Path

from dm_bip.variable_lib.classify import always_unknown, classifier_for
from dm_bip.variable_lib.dbgap_metadata import load_tables
from dm_bip.variable_lib.emit import describe, to_entries, to_yaml
from dm_bip.variable_lib.extract import VariableUsage, collect_variables

MAPPING_INPUT = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_BMI = MAPPING_INPUT / "ARIC-ingest" / "bmi.yaml"
MATCHING_DD = Path(__file__).parents[2] / "input" / "variable_lib" / "dd" / "phs000007.v35.pht004063.v1.MATCHING.dd.tsv"


def _records() -> dict:
    return collect_variables([ARIC_BMI], resolve_urls=False)


def _classify():
    """Type from the MATCHING DD, which declares BMI01 (phv00204719) as a decimal."""
    return classifier_for(load_tables([MATCHING_DD]))


def test_unclassified_variables_are_not_emitted(caplog):
    """source_id and file_id only exist on the two typed classes, so untyped entries are held back."""
    with caplog.at_level(logging.WARNING):
        entries = to_entries(_records(), always_unknown)

    assert len(entries) == 0
    assert entries.unclassified == sorted(_records())
    assert "could not be typed" in caplog.text


def test_identity_triple_populated_from_specs_alone():
    """The phv/pht/phs join issue #352 asks to preserve survives into the entry."""
    entries = to_entries(_records(), _classify())

    entry = next(e for e in entries.continuous if e.source_id == "phv00204719")
    assert entry.id == "dbgap:phv00204719"
    assert entry.file_id == "pht004063"
    assert entry.associated_study == "bdchm:Study/phs000280"


def test_descriptive_slots_left_empty_without_a_metadata_source():
    """Data-dictionary slots stay unset rather than being invented from the specs."""
    entries = to_entries(_records(), _classify())

    entry = next(e for e in entries.continuous if e.source_id == "phv00204719")
    assert entry.variable_name is None
    assert entry.source_variable_description is None
    assert entry.minimum_value is None
    assert entry.unit is None


def test_metadata_source_fills_descriptive_slots():
    """The seam to dbGaP data dictionaries is one lookup, not a restructure."""

    class Dictionary:
        def lookup(self, dataset: str, accession: str) -> dict:
            return {"variable_name": "BMI01", "unit": "kg/m2"} if accession == "phv00204719" else {}

    entries = to_entries(_records(), _classify(), metadata=Dictionary())

    entry = next(e for e in entries.continuous if e.source_id == "phv00204719")
    assert entry.variable_name == "BMI01"
    assert entry.unit == "kg/m2"


def test_metadata_slots_unknown_to_the_class_are_dropped_with_a_warning(caplog):
    """A dictionary field with no home in the schema is reported, not silently discarded."""

    class Dictionary:
        def lookup(self, dataset: str, accession: str) -> dict:
            return {"not_a_slot": "x"}

    with caplog.at_level(logging.WARNING):
        to_entries(_records(), _classify(), metadata=Dictionary())

    assert "has no slot not_a_slot" in caplog.text


def test_description_records_every_use():
    """The rendered description names each target slot, marking expression references."""
    assert (
        describe([VariableUsage("Demography", "sex", False, "spec"), VariableUsage("Demography", "id", True, "spec")])
        == "Source for Demography.sex; Demography.id (via expression)"
    )


def test_output_is_grouped_by_class():
    """Grouping keeps the output self-describing while descriptive slots are still empty."""
    document = to_yaml(to_entries(_records(), _classify()))

    assert "single_continuous_variables:" in document
    assert "single_categorical_variables:" in document


def test_output_is_deterministic():
    """Repeated runs over unchanged specs produce byte-identical output."""
    first = to_yaml(to_entries(_records(), _classify()))
    second = to_yaml(to_entries(_records(), _classify()))

    assert first == second
