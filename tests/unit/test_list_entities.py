"""Unit tests for the list_entities helper."""

from dm_bip.map_data.list_entities import list_entities


def test_extracts_entity_names_from_compact_list_specs(tmp_path):
    """Per-variable spec files (list of compact-key blocks) yield class names."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "a.yaml").write_text("- class_derivations:\n    Person:\n      populated_from: table_a\n")
    (spec_dir / "b.yaml").write_text("- class_derivations:\n    Visit:\n      populated_from: table_b\n")
    assert list_entities([spec_dir]) == ["Person", "Visit"]


def test_deduplicates_across_files(tmp_path):
    """Same class in multiple files produces one entry."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "a.yaml").write_text("- class_derivations:\n    Person:\n      populated_from: t1\n")
    (spec_dir / "b.yaml").write_text("- class_derivations:\n    Person:\n      populated_from: t2\n")
    assert list_entities([spec_dir]) == ["Person"]


def test_standard_dict_format(tmp_path):
    """A standard TransformationSpecification (dict, not list) also works."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "spec.yaml").write_text(
        "class_derivations:\n  Participant:\n    populated_from: t1\n  Demography:\n    populated_from: t1\n"
    )
    assert list_entities([spec_dir]) == ["Demography", "Participant"]


def test_recursive_discovery(tmp_path):
    """Specs in subdirectories are discovered."""
    spec_dir = tmp_path / "specs"
    nested = spec_dir / "cohort" / "phase1"
    nested.mkdir(parents=True)
    (nested / "v.yaml").write_text("- class_derivations:\n    Visit:\n      populated_from: t1\n")
    assert list_entities([spec_dir]) == ["Visit"]


def test_missing_dir_returns_empty(tmp_path):
    """A missing path returns an empty list (no exception)."""
    assert list_entities([tmp_path / "does-not-exist"]) == []


def test_empty_dir_returns_empty(tmp_path):
    """An empty directory returns an empty list."""
    (tmp_path / "specs").mkdir()
    assert list_entities([tmp_path / "specs"]) == []


def test_yml_extension(tmp_path):
    """Files with .yml extension are discovered."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "v.yml").write_text("- class_derivations:\n    Visit:\n      populated_from: t1\n")
    assert list_entities([spec_dir]) == ["Visit"]
