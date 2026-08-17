"""Tests for classifying variables and expressing them as variable library entries."""

import logging
from pathlib import Path

from linkml_runtime import SchemaView

from dm_bip.variable_lib.classify import VariableKind, always_unknown, classifier_for, classify_from_source_schema
from dm_bip.variable_lib.emit import describe, to_entries, to_yaml
from dm_bip.variable_lib.extract import VariableUsage, collect_variables

MAPPING_INPUT = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_BMI = MAPPING_INPUT / "ARIC-ingest" / "bmi.yaml"
SOURCE_SCHEMA = Path(__file__).parents[2] / "input" / "variable_lib" / "source_schema.yaml"


def _records() -> dict:
    return collect_variables([ARIC_BMI], resolve_urls=False)


def test_numeric_ranges_classify_as_continuous():
    """A slot declared float or integer describes a quantity."""
    view = SchemaView(str(SOURCE_SCHEMA))

    assert classify_from_source_schema(view, "pht004063", "phv00204719") is VariableKind.continuous
    assert classify_from_source_schema(view, "pht004063", "phv00204901") is VariableKind.continuous


def test_string_ranges_classify_as_categorical():
    """Non-numeric ranges describe labels, including schema-automator's minted identifier types."""
    view = SchemaView(str(SOURCE_SCHEMA))

    # Both are declared `typeof: string`, so the range has to be followed to its base.
    assert classify_from_source_schema(view, "pht004063", "phv00204812") is VariableKind.categorical
    assert classify_from_source_schema(view, "pht004063", "phv00204900") is VariableKind.categorical


def test_variable_absent_from_source_schema_is_unknown():
    """A spec may name a variable the ingest never produced; that is not a guessable case."""
    view = SchemaView(str(SOURCE_SCHEMA))

    assert classify_from_source_schema(view, "pht004063", "phv99999999") is VariableKind.unknown
    assert classify_from_source_schema(view, "pht000000", "phv00204719") is VariableKind.unknown


def test_no_source_schema_classifies_nothing(caplog):
    """Without schema-automator output there is no typing signal, and that is said out loud."""
    with caplog.at_level(logging.WARNING):
        classify = classifier_for(None)

    assert classify("pht004063", "phv00204719") is VariableKind.unknown
    assert "No source schema supplied" in caplog.text


def test_unclassified_variables_are_not_emitted(caplog):
    """source_id and file_id only exist on the two typed classes, so untyped entries are held back."""
    with caplog.at_level(logging.WARNING):
        entries = to_entries(_records(), always_unknown)

    assert len(entries) == 0
    assert entries.unclassified == sorted(_records())
    assert "could not be typed" in caplog.text


def test_identity_triple_populated_from_specs_alone():
    """The phv/pht/phs join issue #352 asks to preserve survives into the entry."""
    entries = to_entries(_records(), classifier_for(SOURCE_SCHEMA))

    entry = next(e for e in entries.continuous if e.source_id == "phv00204719")
    assert entry.id == "dbgap:phv00204719"
    assert entry.file_id == "pht004063"
    assert entry.associated_study == "bdchm:Study/phs000280"


def test_descriptive_slots_left_empty_without_a_metadata_source():
    """Data-dictionary slots stay unset rather than being invented from the specs."""
    entries = to_entries(_records(), classifier_for(SOURCE_SCHEMA))

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

    entries = to_entries(_records(), classifier_for(SOURCE_SCHEMA), metadata=Dictionary())

    entry = next(e for e in entries.continuous if e.source_id == "phv00204719")
    assert entry.variable_name == "BMI01"
    assert entry.unit == "kg/m2"


def test_metadata_slots_unknown_to_the_class_are_dropped_with_a_warning(caplog):
    """A dictionary field with no home in the schema is reported, not silently discarded."""

    class Dictionary:
        def lookup(self, dataset: str, accession: str) -> dict:
            return {"not_a_slot": "x"}

    with caplog.at_level(logging.WARNING):
        to_entries(_records(), classifier_for(SOURCE_SCHEMA), metadata=Dictionary())

    assert "has no slot not_a_slot" in caplog.text


def test_description_records_every_use():
    """The rendered description names each target slot, marking expression references."""
    assert (
        describe([VariableUsage("Demography", "sex", False, "spec"), VariableUsage("Demography", "id", True, "spec")])
        == "Source for Demography.sex; Demography.id (via expression)"
    )


def test_output_is_grouped_by_class():
    """Grouping keeps the output self-describing while descriptive slots are still empty."""
    document = to_yaml(to_entries(_records(), classifier_for(SOURCE_SCHEMA)))

    assert "single_continuous_variables:" in document
    assert "single_categorical_variables:" in document


def test_output_is_deterministic():
    """Repeated runs over unchanged specs produce byte-identical output."""
    first = to_yaml(to_entries(_records(), classifier_for(SOURCE_SCHEMA)))
    second = to_yaml(to_entries(_records(), classifier_for(SOURCE_SCHEMA)))

    assert first == second
