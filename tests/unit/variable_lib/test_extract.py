"""Tests for indexing source variables from transformation specs."""

import logging
from pathlib import Path

import yaml

from dm_bip.variable_lib.extract import VariableUsage, collect_variables

INPUT_DIR = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_DIR = INPUT_DIR / "ARIC-ingest"
ARIC_BMI = ARIC_DIR / "bmi.yaml"


def _collect(*paths: Path) -> dict:
    """Collect variables with URL resolution off, so tests do not depend on git state."""
    return collect_variables(list(paths), resolve_urls=False)


def test_accumulates_every_usage_of_a_variable():
    """A variable feeding several target slots keeps all of them, not just the first."""
    records = _collect(ARIC_BMI)

    slots = {(u.target_class, u.slot) for u in records["phv00204812"].usages}
    assert slots == {
        ("MeasurementObservation", "associated_participant"),
        ("MeasurementObservation", "associated_visit"),
    }


def test_nested_derivation_variable_inherits_enclosing_dataset():
    """A variable in a nested derivation is found, and takes the dataset of its fragment."""
    records = _collect(ARIC_BMI)

    record = records["phv00204719"]
    assert record.datasets == {"pht004063"}
    assert [(u.target_class, u.slot) for u in record.usages] == [("Quantity", "value_decimal")]


def test_expression_references_are_marked():
    """Variables reached through expr strings are distinguished from directly populated ones."""
    records = _collect(ARIC_BMI)

    assert all(u.via_expression for u in records["phv00204812"].usages)
    assert not any(u.via_expression for u in records["phv00204719"].usages)


def test_study_identity_comes_from_researchstudy_yaml():
    """Variables carry the accession of the study whose directory their spec sits in."""
    records = _collect(ARIC_BMI)

    assert records["phv00204719"].study_id == "bdchm:Study/phs000280"


def test_placeholder_study_when_researchstudy_missing(tmp_path, caplog):
    """A spec directory with no researchstudy.yaml yields a placeholder id, and warns."""
    spec = tmp_path / "weight.yaml"
    spec.write_text(
        yaml.safe_dump(
            [
                {
                    "class_derivations": {
                        "Obs": {"populated_from": "pht1", "slot_derivations": {"v": {"populated_from": "phv1"}}}
                    }
                }
            ]
        )
    )

    with caplog.at_level(logging.WARNING):
        records = _collect(spec)

    assert records["phv1"].study_id == f"dmcprov:{tmp_path.name}"
    assert "placeholder study id" in caplog.text


def test_variable_under_two_datasets_is_recorded_not_overwritten(tmp_path, caplog):
    """Both datasets are kept, and collapsing to a single file_id warns rather than guessing."""
    spec = tmp_path / "split.yaml"
    spec.write_text(
        yaml.safe_dump(
            [
                {
                    "class_derivations": {
                        "Obs": {"populated_from": "phtB", "slot_derivations": {"v": {"populated_from": "phv1"}}}
                    }
                },
                {
                    "class_derivations": {
                        "Obs": {"populated_from": "phtA", "slot_derivations": {"v": {"populated_from": "phv1"}}}
                    }
                },
            ]
        )
    )

    record = _collect(spec)["phv1"]
    assert record.datasets == {"phtA", "phtB"}

    with caplog.at_level(logging.WARNING):
        assert record.sole_dataset() == "phtA"
    assert "multiple datasets" in caplog.text


def test_variable_without_enclosing_dataset_is_skipped(tmp_path, caplog):
    """A derivation with no populated_from anywhere cannot place its variables."""
    spec = tmp_path / "orphan.yaml"
    spec.write_text(
        yaml.safe_dump([{"class_derivations": {"Obs": {"slot_derivations": {"v": {"populated_from": "phv1"}}}}}])
    )

    with caplog.at_level(logging.WARNING):
        records = _collect(spec)

    assert records == {}
    assert "no enclosing dataset" in caplog.text


def test_usages_are_deduplicated_and_sorted():
    """Repeated identical references collapse, and ordering is stable across runs."""
    records = _collect(ARIC_BMI)

    for record in records.values():
        assert len(record.usages) == len(set(record.usages))
        assert record.usages == sorted(record.usages)


def test_records_sorted_by_accession():
    """Output order does not depend on the order specs happened to be read."""
    records = _collect(ARIC_BMI)

    assert list(records) == sorted(records)


def test_usage_ordering_is_total():
    """VariableUsage sorts on every field, so equal-prefix usages still order deterministically."""
    first = VariableUsage("A", "b", False, "spec")
    second = VariableUsage("A", "b", True, "spec")

    assert sorted([second, first]) == [first, second]
