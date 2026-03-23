"""Unit tests for the compose_specs module."""

import yaml

from dm_bip.map_data.compose_specs import compose_specs


def test_groups_derivations_by_class(tmp_path):
    """Derivation blocks with the same class name end up in one output file."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "a.yaml").write_text("- class_derivations:\n    Person:\n      populated_from: table_a\n")
    (spec_dir / "b.yaml").write_text("- class_derivations:\n    Person:\n      populated_from: table_b\n")
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert len(written) == 1
    assert written[0].name == "Person.yaml"
    data = yaml.safe_load(written[0].read_text())
    assert len(data["class_derivations"]) == 2


def test_multiple_entities(tmp_path):
    """Different class names produce separate output files."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "mixed.yaml").write_text(
        "- class_derivations:\n"
        "    Participant:\n"
        "      populated_from: t1\n"
        "- class_derivations:\n"
        "    Demography:\n"
        "      populated_from: t1\n"
    )
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    names = sorted(p.name for p in written)
    assert names == ["Demography.yaml", "Participant.yaml"]


def test_many_derivations_same_class(tmp_path):
    """Multiple blocks for MeasurementObservation are grouped correctly."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    blocks = []
    for i in range(9):
        blocks.append(f"- class_derivations:\n    MeasurementObservation:\n      populated_from: table_{i}\n")
    (spec_dir / "measurements.yaml").write_text("".join(blocks))
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert len(written) == 1
    data = yaml.safe_load(written[0].read_text())
    assert len(data["class_derivations"]) == 9


def test_preserves_nested_object_derivations(tmp_path):
    """Nested object_derivations (like Quantity) are preserved in output."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "measurement.yaml").write_text(
        "- class_derivations:\n"
        "    MeasurementObservation:\n"
        "      populated_from: pht000002\n"
        "      slot_derivations:\n"
        "        value_quantity:\n"
        "          object_derivations:\n"
        "          - class_derivations:\n"
        "              Quantity:\n"
        "                populated_from: pht000002\n"
        "                slot_derivations:\n"
        "                  value_decimal:\n"
        "                    populated_from: phv00000012\n"
    )
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert len(written) == 1
    assert written[0].name == "MeasurementObservation.yaml"
    data = yaml.safe_load(written[0].read_text())
    deriv = data["class_derivations"][0]["MeasurementObservation"]
    nested = deriv["slot_derivations"]["value_quantity"]["object_derivations"]
    assert "Quantity" in nested[0]["class_derivations"]


def test_empty_dir_produces_no_output(tmp_path):
    """An empty spec directory produces no output files."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert written == []
    assert out.exists()


def test_skips_non_list_yaml(tmp_path):
    """YAML files that are not lists are ignored."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "config.yaml").write_text("name: test\nversion: 1\n")
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert written == []


def test_handles_yml_extension(tmp_path):
    """Files with .yml extension are also processed."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "visit.yml").write_text("- class_derivations:\n    Visit:\n      populated_from: t1\n")
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert len(written) == 1
    assert written[0].name == "Visit.yaml"


def test_output_is_valid_transformation_spec(tmp_path):
    """Output files have class_derivations as a list of compact-key dicts."""
    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "spec.yaml").write_text(
        "- class_derivations:\n"
        "    Participant:\n"
        "      populated_from: t1\n"
        "      slot_derivations:\n"
        "        id:\n"
        "          populated_from: col1\n"
    )
    out = tmp_path / "out"
    compose_specs(spec_dir, out)
    data = yaml.safe_load((out / "Participant.yaml").read_text())
    assert "class_derivations" in data
    assert isinstance(data["class_derivations"], list)
    entry = data["class_derivations"][0]
    assert "Participant" in entry
    assert entry["Participant"]["populated_from"] == "t1"


def test_recursive_spec_discovery(tmp_path):
    """Specs in subdirectories are discovered."""
    spec_dir = tmp_path / "specs"
    subdir = spec_dir / "temporal" / "FHS"
    subdir.mkdir(parents=True)
    (subdir / "visit.yaml").write_text("- class_derivations:\n    Visit:\n      populated_from: t1\n")
    out = tmp_path / "out"
    written = compose_specs(spec_dir, out)
    assert len(written) == 1
    assert written[0].name == "Visit.yaml"
