"""Tests for mapping-provenance extraction from transformation specs."""

import logging
from pathlib import Path

import yaml

from dm_bip.mapping_prov.extract import extract_provenance, iter_class_derivations, read_study

INPUT_DIR = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_DIR = INPUT_DIR / "ARIC-ingest"
MESA_DIR = INPUT_DIR / "MESA-ingest"


def test_iter_class_derivations_walks_nested_blocks():
    """The walker yields every class derivation, including ones nested inside slot derivations."""
    spec = yaml.safe_load((ARIC_DIR / "bmi.yaml").read_text())
    derivations = list(iter_class_derivations(spec))

    class_names = [d.target_class for d in derivations]
    assert class_names.count("MeasurementObservation") == 3
    assert class_names.count("Quantity") == 3
    assert derivations[0].dataset == "pht004063"


def test_populated_from_variables_collected():
    """Slot-level populated_from values are collected as variables."""
    spec = yaml.safe_load((ARIC_DIR / "bmi.yaml").read_text())
    variables = {var for d in iter_class_derivations(spec) for _, var in d.variables}
    assert "phv00204719" in variables
    assert "phv00204812" not in variables  # appears only inside expr strings


def test_expr_variables_collected_separately():
    """Variables referenced in braced expr strings are collected, per referencing slot."""
    spec = yaml.safe_load((ARIC_DIR / "bmi.yaml").read_text())
    first = next(iter_class_derivations(spec))
    assert ("associated_participant", "phv00204812") in first.expr_variables
    assert ("associated_visit", "phv00204812") in first.expr_variables


def test_read_study_from_researchstudy_yaml():
    """Study identity comes from the accession_number value slot of researchstudy.yaml."""
    study = read_study(ARIC_DIR)
    assert study is not None
    assert study.id == "bdchm:Study/phs000280"
    assert study.name == "Atherosclerosis Risk in Communities (ARIC)"


def test_read_study_missing_file():
    """A directory without researchstudy.yaml yields no study."""
    assert read_study(MESA_DIR) is None


def test_extract_provenance_builds_study_document():
    """A study document nests datasets, variables, specs, and derived entities under the study."""
    [study] = extract_provenance([ARIC_DIR / "bmi.yaml", ARIC_DIR / "researchstudy.yaml"], base_dir=INPUT_DIR)

    assert study.id == "bdchm:Study/phs000280"

    datasets = {d.id: d for d in study.datasets}
    variables = {v.id: v for v in datasets["dbgap:pht004063"].variables}
    assert set(variables) == {"dbgap:phv00204719", "dbgap:phv00204812"}
    assert variables["dbgap:phv00204719"].description == "Source for Quantity.value_decimal"
    assert (
        variables["dbgap:phv00204812"].description
        == "Source for MeasurementObservation.associated_participant (via expression)"
    )

    spec_ids = [s.id for s in study.transformation_specs]
    assert spec_ids == ["dmcprov:ARIC-ingest/bmi.yaml", "dmcprov:ARIC-ingest/researchstudy.yaml"]

    derived = {e.id: e for e in study.derived_entities}
    target = derived["dmcprov:ARIC-ingest/bmi/MeasurementObservation/pht004063"]
    assert "dbgap:pht004063" in target.derived_from
    assert "dbgap:phv00204719" in target.derived_from
    assert "dbgap:phv00204812" in target.derived_from  # referenced via expression
    assert "dmcprov:ARIC-ingest/bmi.yaml" in target.derived_from
    # researchstudy.yaml is also an ordinary spec with its own derived entity
    assert "dmcprov:ARIC-ingest/researchstudy/ResearchStudy/pht001440" in derived


def test_placeholder_study_when_no_researchstudy(caplog):
    """Spec directories without researchstudy.yaml fall back to a placeholder study, with a warning."""
    with caplog.at_level(logging.WARNING):
        [study] = extract_provenance([MESA_DIR / "bmi.yaml"], base_dir=INPUT_DIR)
    assert study.id == "dmcprov:MESA-ingest"
    assert study.name == "MESA-ingest"
    assert any("researchstudy.yaml" in record.message for record in caplog.records)


def test_multiple_studies_sorted_by_directory():
    """Specs from several directories produce one study document each, in directory order."""
    studies = extract_provenance([ARIC_DIR / "bmi.yaml", MESA_DIR / "bmi.yaml"], base_dir=INPUT_DIR)
    assert [s.id for s in studies] == ["bdchm:Study/phs000280", "dmcprov:MESA-ingest"]


def test_fragments_deriving_same_class_and_dataset_merge():
    """Two fragments deriving the same class from the same dataset merge into one derived entity."""
    [study] = extract_provenance([ARIC_DIR / "hypertension.yaml"], base_dir=INPUT_DIR)
    [entity] = study.derived_entities
    assert "dbgap:phv00204800" in entity.derived_from
    assert "dbgap:phv00204801" in entity.derived_from
