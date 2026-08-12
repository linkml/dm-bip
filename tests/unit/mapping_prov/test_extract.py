"""Tests for mapping-provenance extraction from transformation specs."""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import git
import yaml

from dm_bip.mapping_prov.extract import extract_provenance, iter_class_derivations, read_study, run_activity

INPUT_DIR = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_DIR = INPUT_DIR / "ARIC-ingest"
MESA_DIR = INPUT_DIR / "MESA-ingest"

TEST_COMMITTER = git.Actor("Test", "test@example.org")


def _make_spec_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create a git repo containing the ARIC bmi spec, returning its path and commit sha."""
    repo_dir = tmp_path / "specs"
    (repo_dir / "ARIC-ingest").mkdir(parents=True)
    shutil.copy(ARIC_DIR / "bmi.yaml", repo_dir / "ARIC-ingest" / "bmi.yaml")
    repo = git.Repo.init(repo_dir)
    repo.create_remote("origin", "git@github.com:example/specs.git")
    repo.index.add(["ARIC-ingest/bmi.yaml"])
    commit = repo.index.commit("Add spec", author=TEST_COMMITTER, committer=TEST_COMMITTER)
    return repo_dir, commit.hexsha


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
    assert study.entity_type == "study"
    assert study.name == "Atherosclerosis Risk in Communities (ARIC)"


def test_read_study_missing_file():
    """A directory without researchstudy.yaml yields no study."""
    assert read_study(MESA_DIR) is None


def test_extract_provenance_builds_study_document():
    """A study document nests datasets, variables, specs, and derived entities under the study."""
    [study] = extract_provenance(
        [ARIC_DIR / "bmi.yaml", ARIC_DIR / "researchstudy.yaml"], base_dir=INPUT_DIR, resolve_urls=False
    )

    assert study.id == "bdchm:Study/phs000280"

    parts = {e.id: e for e in study.has_part}
    dataset = parts["dbgap:pht004063"]
    assert dataset.entity_type == "dataset"
    variables = {v.id: v for v in dataset.has_part}
    assert set(variables) == {"dbgap:phv00204719", "dbgap:phv00204812"}
    assert all(v.entity_type == "variable" for v in variables.values())
    assert variables["dbgap:phv00204719"].description == "Source for Quantity.value_decimal"
    assert (
        variables["dbgap:phv00204812"].description
        == "Source for MeasurementObservation.associated_participant (via expression)"
    )

    spec_ids = [e.id for e in study.has_part if e.entity_type == "transformation_spec"]
    assert spec_ids == ["dmcprov:ARIC-ingest/bmi.yaml", "dmcprov:ARIC-ingest/researchstudy.yaml"]

    derived = {e.id: e for e in study.has_part if e.derived_from}
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
        [study] = extract_provenance([MESA_DIR / "bmi.yaml"], base_dir=INPUT_DIR, resolve_urls=False)
    assert study.id == "dmcprov:MESA-ingest"
    assert study.name == "MESA-ingest"
    assert any("researchstudy.yaml" in record.message for record in caplog.records)


def test_multiple_studies_sorted_by_directory():
    """Specs from several directories produce one study document each, in directory order."""
    studies = extract_provenance([ARIC_DIR / "bmi.yaml", MESA_DIR / "bmi.yaml"], base_dir=INPUT_DIR, resolve_urls=False)
    assert [s.id for s in studies] == ["bdchm:Study/phs000280", "dmcprov:MESA-ingest"]


def test_fragments_deriving_same_class_and_dataset_merge():
    """Two fragments deriving the same class from the same dataset merge into one derived entity."""
    [study] = extract_provenance([ARIC_DIR / "hypertension.yaml"], base_dir=INPUT_DIR, resolve_urls=False)
    [entity] = [e for e in study.has_part if e.derived_from]
    assert "dbgap:phv00204800" in entity.derived_from
    assert "dbgap:phv00204801" in entity.derived_from


def test_run_activity_documents_the_extraction():
    """The run activity records timing, the dm-bip agent, and the specs read as inputs."""
    studies = extract_provenance([ARIC_DIR / "bmi.yaml", MESA_DIR / "bmi.yaml"], base_dir=INPUT_DIR, resolve_urls=False)
    started = datetime(2026, 8, 12, 15, 0, 0, tzinfo=timezone.utc)
    ended = datetime(2026, 8, 12, 15, 0, 5, tzinfo=timezone.utc)

    activity = run_activity(studies, started, ended)

    assert activity.id.startswith("dmcprov:run/")
    assert activity.started_at_time == started
    assert activity.ended_at_time == ended
    assert activity.associated_with.name.startswith("dm-bip ")
    assert "linkml_map" in activity.associated_with.description
    assert activity.has_input == ["dmcprov:ARIC-ingest/bmi.yaml", "dmcprov:MESA-ingest/bmi.yaml"]


def test_spec_ids_are_commit_pinned_urls_in_git_checkouts(tmp_path):
    """Specs read from a clean git checkout with a GitHub remote are identified by permalink URLs."""
    repo, sha = _make_spec_repo(tmp_path)

    [study] = extract_provenance([repo / "ARIC-ingest" / "bmi.yaml"], base_dir=repo)

    url = f"https://github.com/example/specs/blob/{sha}/ARIC-ingest/bmi.yaml"
    [spec] = [e for e in study.has_part if e.entity_type == "transformation_spec"]
    assert spec.id == url
    assert spec.name == "ARIC-ingest/bmi.yaml"  # repo-relative, matching the URL's path
    derived = [e for e in study.has_part if e.derived_from]
    assert url in derived[0].derived_from
    # derived-entity ids stay local: they are this tool's records, not repo artifacts
    assert derived[0].id == "dmcprov:ARIC-ingest/bmi/MeasurementObservation/pht004063"


def test_locally_modified_specs_fall_back_to_path_ids(tmp_path, caplog):
    """A spec with uncommitted changes gets a local path id, since a commit URL would misstate its content."""
    repo, _ = _make_spec_repo(tmp_path)
    spec = repo / "ARIC-ingest" / "bmi.yaml"
    spec.write_text(spec.read_text() + "\n# local edit\n")

    with caplog.at_level(logging.WARNING):
        [study] = extract_provenance([spec], base_dir=repo)

    spec_ids = [e.id for e in study.has_part if e.entity_type == "transformation_spec"]
    assert spec_ids == ["dmcprov:ARIC-ingest/bmi.yaml"]
    assert any("untracked or locally modified" in record.message for record in caplog.records)
