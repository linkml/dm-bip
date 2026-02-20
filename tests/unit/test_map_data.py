"""Unit tests for the map_data module."""

import json
import os
import tempfile
from pathlib import Path

import pytest
import yaml
from linkml_runtime import SchemaView

from dm_bip.map_data.map_data import (
    DataLoader,
    discover_entities,
    get_schema,
    get_spec_files,
    main,
    multi_spec_transform,
    process_entities,
)
from dm_bip.map_data.streams import (
    JSONLStream,
    JSONStream,
    TSVStream,
    YAMLStream,
)

# Path to toy_data directory
TOY_DATA = Path(__file__).parent.parent.parent / "toy_data"


# --- Fixtures ---


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is cleaned up after the test."""
    import shutil

    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture
def data_loader_dir(temp_dir):
    """Create a temp directory with a test TSV file for DataLoader tests."""
    test_file = os.path.join(temp_dir, "test_data.tsv")
    with open(test_file, "w") as f:
        f.write("id\tname\tvalue\n")
        f.write("1\tAlice\t100\n")
        f.write("2\tBob\t200\n")
    return temp_dir


@pytest.fixture
def spec_files_dir(temp_dir):
    """Create a temp directory with test YAML/YML files for get_spec_files tests."""
    # YAML file with search string
    yaml_match = os.path.join(temp_dir, "match_spec.yaml")
    with open(yaml_match, "w") as f:
        f.write("- class_derivations:\n")
        f.write("    Participant:\n")
        f.write("      populated_from: test_data\n")

    # Another YAML file with search string
    yaml_match2 = os.path.join(temp_dir, "another_spec.yaml")
    with open(yaml_match2, "w") as f:
        f.write("- class_derivations:\n")
        f.write("    Participant:\n")
        f.write("      populated_from: other_data\n")

    # YAML file without the search string
    yaml_no_match = os.path.join(temp_dir, "no_match.yaml")
    with open(yaml_no_match, "w") as f:
        f.write("- class_derivations:\n")
        f.write("    Person:\n")
        f.write("      populated_from: person_data\n")

    # Non-YAML file with search string (should be ignored)
    txt_match = os.path.join(temp_dir, "match.txt")
    with open(txt_match, "w") as f:
        f.write("    Participant:\n")

    return temp_dir


# --- DataLoader Tests ---


def test_dataloader_init_stores_base_path(data_loader_dir):
    """Test that __init__ stores the base path correctly."""
    loader = DataLoader(Path(data_loader_dir))
    assert loader.base_path == Path(data_loader_dir)


def test_dataloader_contains_returns_true_for_existing_file(data_loader_dir):
    """Test __contains__ returns True when file exists."""
    loader = DataLoader(Path(data_loader_dir))
    assert "test_data" in loader


def test_dataloader_contains_returns_false_for_missing_file(data_loader_dir):
    """Test __contains__ returns False when file does not exist."""
    loader = DataLoader(Path(data_loader_dir))
    assert "nonexistent" not in loader


def test_dataloader_getitem_returns_iterator_for_existing_file(data_loader_dir):
    """Test __getitem__ returns an iterator of instances from TSV."""
    loader = DataLoader(Path(data_loader_dir))
    instances = list(loader["test_data"])
    assert len(instances) == 2
    # TsvLoader may coerce types, so check values loosely
    assert str(instances[0]["id"]) == "1"
    assert instances[0]["name"] == "Alice"
    assert str(instances[0]["value"]) == "100"
    assert str(instances[1]["id"]) == "2"
    assert instances[1]["name"] == "Bob"


def test_dataloader_getitem_raises_for_missing_file(data_loader_dir):
    """Test __getitem__ raises FileNotFoundError for missing files."""
    loader = DataLoader(Path(data_loader_dir))
    with pytest.raises(FileNotFoundError) as exc_info:
        loader["nonexistent"]
    assert "nonexistent" in str(exc_info.value)


# --- get_spec_files Tests ---


def test_get_spec_files_finds_yaml_with_search_string(spec_files_dir):
    """Test finding YAML files containing the search string."""
    result = get_spec_files(spec_files_dir, "    Participant:")
    assert len(result) == 2
    stems = [p.stem for p in result]
    assert "match_spec" in stems
    assert "another_spec" in stems


def test_get_spec_files_returns_sorted_by_stem(spec_files_dir):
    """Test that results are sorted by stem."""
    result = get_spec_files(spec_files_dir, "    Participant:")
    stems = [p.stem for p in result]
    assert stems == sorted(stems)


def test_get_spec_files_returns_empty_when_no_matches(spec_files_dir):
    """Test returns empty list when no files match."""
    result = get_spec_files(spec_files_dir, "NonexistentString")
    assert result == []


def test_get_spec_files_excludes_non_yaml_files(spec_files_dir):
    """Test that non-YAML files are excluded from results."""
    result = get_spec_files(spec_files_dir, "    Participant:")
    extensions = [p.suffix for p in result]
    assert all(ext in [".yaml", ".yml"] for ext in extensions)


def test_get_spec_files_handles_yml_extension(spec_files_dir):
    """Test that .yml files are also found."""
    yml_file = os.path.join(spec_files_dir, "test_spec.yml")
    with open(yml_file, "w") as f:
        f.write("    Participant:\n")
    result = get_spec_files(spec_files_dir, "    Participant:")
    stems = [p.stem for p in result]
    assert "test_spec" in stems


# --- discover_entities Tests ---


def test_discover_entities_finds_top_level_classes(spec_files_dir):
    """Test that discover_entities finds entity names from class_derivations."""
    result = discover_entities(Path(spec_files_dir))
    assert "Participant" in result
    assert "Person" in result


def test_discover_entities_returns_sorted(spec_files_dir):
    """Test that results are sorted alphabetically."""
    result = discover_entities(Path(spec_files_dir))
    assert result == sorted(result)


def test_discover_entities_ignores_nested_object_derivations(temp_dir):
    """Test that nested class_derivations inside object_derivations are excluded."""
    spec_file = os.path.join(temp_dir, "measurement.yaml")
    with open(spec_file, "w") as f:
        f.write(
            "- class_derivations:\n"
            "    MeasurementObservation:\n"
            "      populated_from: test_data\n"
            "      slot_derivations:\n"
            "        value_quantity:\n"
            "          object_derivations:\n"
            "          - class_derivations:\n"
            "              Quantity:\n"
            "                populated_from: test_data\n"
        )
    result = discover_entities(Path(temp_dir))
    assert "MeasurementObservation" in result
    assert "Quantity" not in result


def test_discover_entities_empty_directory(temp_dir):
    """Test that an empty directory returns an empty list."""
    result = discover_entities(Path(temp_dir))
    assert result == []


def test_discover_entities_skips_non_list_yaml(temp_dir):
    """Test that YAML files with non-list content are skipped."""
    spec_file = os.path.join(temp_dir, "config.yaml")
    with open(spec_file, "w") as f:
        f.write("name: test\nversion: 1\n")
    result = discover_entities(Path(temp_dir))
    assert result == []


def test_discover_entities_deduplicates(temp_dir):
    """Test that duplicate entity names across files are deduplicated."""
    for name in ["spec1.yaml", "spec2.yaml"]:
        with open(os.path.join(temp_dir, name), "w") as f:
            f.write("- class_derivations:\n    Person:\n      populated_from: test_data\n")
    result = discover_entities(Path(temp_dir))
    assert result.count("Person") == 1


def test_discover_entities_finds_yml_extension(temp_dir):
    """Test that .yml files are also discovered."""
    yml_file = os.path.join(temp_dir, "visit_spec.yml")
    with open(yml_file, "w") as f:
        f.write("- class_derivations:\n    Visit:\n      populated_from: test_data\n")
    result = discover_entities(Path(temp_dir))
    assert "Visit" in result


def test_discover_entities_finds_specs_in_subdirectories(temp_dir):
    """Test that specs in subdirectories are discovered recursively."""
    subdir = os.path.join(temp_dir, "temporal", "FHS")
    os.makedirs(subdir)
    spec_file = os.path.join(subdir, "visit.yaml")
    with open(spec_file, "w") as f:
        f.write("- class_derivations:\n    Visit:\n      populated_from: test_data\n")
    result = discover_entities(Path(temp_dir))
    assert "Visit" in result


# --- JSONStream Tests ---


def test_json_stream_single_chunk():
    """Test JSON output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]]
    stream = JSONStream(key_name="persons")
    result = list(stream.process(iter(chunks)))
    assert len(result) == 1
    parsed = json.loads(result[0])
    assert parsed["persons"] == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


def test_json_stream_multiple_chunks():
    """Test JSON output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    stream = JSONStream(key_name="items")
    result = list(stream.process(iter(chunks)))
    assert len(result) == 2
    assert '"items"' in result[0]


def test_json_stream_empty():
    """Test JSON output with no chunks."""
    stream = JSONStream(key_name="items")
    result = list(stream.process(iter([])))
    assert result == []


# --- JSONLStream Tests ---


def test_jsonl_stream_single_chunk():
    """Test JSONL output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]]
    stream = JSONLStream()
    result = list(stream.process(iter(chunks)))
    assert len(result) == 1
    lines = result[0].strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "Alice"}
    assert json.loads(lines[1]) == {"id": 2, "name": "Bob"}


def test_jsonl_stream_multiple_chunks():
    """Test JSONL output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    stream = JSONLStream()
    result = list(stream.process(iter(chunks)))
    assert len(result) == 2
    assert json.loads(result[0].strip()) == {"id": 1}
    assert json.loads(result[1].strip()) == {"id": 2}


def test_jsonl_stream_each_object_on_own_line():
    """Test that each object is on its own line."""
    chunks = [[{"a": 1}, {"b": 2}, {"c": 3}]]
    stream = JSONLStream()
    result = list(stream.process(iter(chunks)))
    lines = result[0].strip().split("\n")
    assert len(lines) == 3


# --- YAMLStream Tests ---


def test_yaml_stream_single_chunk():
    """Test YAML output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}]]
    stream = YAMLStream(key_name="persons")
    result = list(stream.process(iter(chunks)))
    assert len(result) == 1
    parsed = yaml.safe_load(result[0])
    assert parsed["persons"] == [{"id": 1, "name": "Alice"}]


def test_yaml_stream_multiple_chunks():
    """Test YAML output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    stream = YAMLStream(key_name="items")
    result = list(stream.process(iter(chunks)))
    assert len(result) == 2
    assert "items:" in result[0]


# --- TSVStream Tests ---


def test_tsv_stream_basic_output():
    """Test basic TSV output with flat objects."""
    chunks = [[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]]
    stream = TSVStream(sep="\t", reducer_str="__")
    result = list(stream.process(iter(chunks)))
    lines = "".join(result).strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    headers = lines[0].split("\t")
    assert "id" in headers
    assert "name" in headers


def test_tsv_stream_nested_objects_flattened():
    """Test that nested objects are flattened with separator."""
    chunks = [[{"id": "1", "person": {"name": "Alice", "age": 30}}]]
    stream = TSVStream(sep="\t", reducer_str="__")
    result = list(stream.process(iter(chunks)))
    lines = "".join(result).strip().split("\n")
    headers = lines[0].split("\t")
    assert "person__name" in headers
    assert "person__age" in headers


def test_tsv_stream_custom_separator():
    """Test custom column separator."""
    chunks = [[{"id": "1", "name": "Alice"}]]
    stream = TSVStream(sep=",", reducer_str="__")
    result = list(stream.process(iter(chunks)))
    lines = "".join(result).strip().split("\n")
    assert "," in lines[0]


def test_tsv_stream_missing_values_empty_string():
    """Test that missing values become empty strings when key is in headers."""
    # First object establishes headers, second object is missing a key
    chunks = [[{"id": "1", "name": "Alice"}, {"id": "2"}]]
    stream = TSVStream(sep="\t", reducer_str="__")
    result = list(stream.process(iter(chunks)))
    # Parse without strip() to preserve empty trailing columns
    lines = "".join(result).rstrip("\n").split("\n")
    headers = lines[0].split("\t")
    # Headers include both id and name from first object
    assert "name" in headers
    # Second data row should have empty value for name
    row2_values = lines[2].split("\t")
    name_idx = headers.index("name")
    assert row2_values[name_idx] == ""


def test_tsv_stream_must_update_headers_when_headers_change():
    """Test that must_update_headers is set when new columns appear after first row."""
    chunks = [[{"id": "1"}], [{"id": "2", "new_col": "value"}]]
    stream = TSVStream(sep="\t", reducer_str="__")
    list(stream.process(iter(chunks)))
    # must_update_headers should be True because new columns appeared
    assert stream.must_update_headers
    assert "new_col" in stream.next_headers


def test_tsv_stream_must_update_headers_false_when_consistent():
    """Test that must_update_headers is False when columns are consistent."""
    chunks = [[{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]]
    stream = TSVStream(sep="\t", reducer_str="__")
    list(stream.process(iter(chunks)))
    assert not stream.must_update_headers


# --- TSVStream.rewrite_header_and_pad Tests ---


def test_rewrite_header_and_pad_rewrites_header():
    """Test that the header is rewritten with final columns."""
    original_lines = ["a\tb\n", "1\t2\n", "3\t4\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(TSVStream.rewrite_header_and_pad(chunks, final_header))
    combined = "".join(result)
    lines = combined.strip().split("\n")
    assert lines[0] == "a\tb\tc"


def test_rewrite_header_and_pad_pads_short_rows():
    """Test that rows with fewer columns are padded."""
    # Original file has 2 columns, final header has 3
    original_lines = ["a\tb\n", "1\t2\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(TSVStream.rewrite_header_and_pad(chunks, final_header))
    combined = "".join(result)
    # Parse without strip() to preserve empty trailing columns
    lines = combined.rstrip("\n").split("\n")
    # Data row "1\t2" should be padded to have 3 columns
    row_values = lines[1].split("\t")
    assert len(row_values) == 3
    assert row_values == ["1", "2", ""]


def test_rewrite_header_and_pad_multiple_chunks():
    """Test handling multiple chunks."""
    chunk1 = ["a\tb\n", "1\t2\n"]
    chunk2 = ["3\t4\n"]
    chunks = iter([chunk1, chunk2])
    final_header = ["a", "b", "c"]
    result = list(TSVStream.rewrite_header_and_pad(chunks, final_header))
    combined = "".join(result)
    lines = combined.strip().split("\n")
    assert len(lines) == 3  # header + 2 data rows


def test_rewrite_header_and_pad_custom_separator():
    """Test with a custom separator."""
    original_lines = ["a,b\n", "1,2\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(TSVStream.rewrite_header_and_pad(chunks, final_header, sep=","))
    combined = "".join(result)
    lines = combined.strip().split("\n")
    assert lines[0] == "a,b,c"


# --- get_schema Tests ---


def test_get_schema_loads_valid_schema():
    """Test that get_schema loads a LinkML schema from file."""
    schema = get_schema(TOY_DATA / "schemas/source-schema.yaml")
    assert schema.name == "ToySourceSchema"
    assert "demographics" in schema.classes
    assert "subject" in schema.classes


# --- multi_spec_transform Tests ---


@pytest.fixture
def linkml_test_setup():
    """Set up LinkML schemas and data loader for transformation tests."""
    source_schema = get_schema(TOY_DATA / "schemas/source-schema.yaml")
    target_schema = get_schema(TOY_DATA / "schemas/target-schema.yaml")
    source_sv = SchemaView(source_schema)
    target_sv = SchemaView(target_schema)
    data_loader = DataLoader(TOY_DATA / "raw_data")
    return {
        "source_sv": source_sv,
        "target_sv": target_sv,
        "data_loader": data_loader,
        "spec_dir": TOY_DATA / "specs",
    }


def test_multi_spec_transform_transforms_data(linkml_test_setup):
    """Test that multi_spec_transform applies transformations correctly."""
    spec_files = get_spec_files(linkml_test_setup["spec_dir"], "^    Person:")
    results = list(
        multi_spec_transform(
            linkml_test_setup["data_loader"],
            spec_files,
            linkml_test_setup["source_sv"],
            linkml_test_setup["target_sv"],
        )
    )
    # demographics.tsv has 110 records
    assert len(results) == 110
    # Check first record transformed correctly
    assert results[0]["id"] == "SUBJ001"
    assert results[0]["gender"] == "Male"
    assert results[0]["race"] == "asian"
    assert results[0]["age"] == 74


def test_multi_spec_transform_participant(linkml_test_setup):
    """Test transformation of Participant entity."""
    spec_files = get_spec_files(linkml_test_setup["spec_dir"], "^    Participant:")
    results = list(
        multi_spec_transform(
            linkml_test_setup["data_loader"],
            spec_files,
            linkml_test_setup["source_sv"],
            linkml_test_setup["target_sv"],
        )
    )
    # subject.tsv has 110 records
    assert len(results) == 110
    assert results[0]["id"] == "SUBJ001"
    assert results[0]["consent"] == "open"
    assert results[0]["study"] == "STUDY001"


def test_multi_spec_transform_empty_spec_files(linkml_test_setup):
    """Test that empty spec files list yields no results."""
    results = list(
        multi_spec_transform(
            linkml_test_setup["data_loader"],
            [],
            linkml_test_setup["source_sv"],
            linkml_test_setup["target_sv"],
        )
    )
    assert results == []


def test_multi_spec_transform_skips_missing_data_files(linkml_test_setup, temp_dir, caplog):
    """Test that missing data files are skipped with a warning, not an error."""
    # Create a spec that references a nonexistent pht table
    spec_file = Path(temp_dir) / "missing_data_spec.yaml"
    spec_file.write_text(
        "- class_derivations:\n"
        "    Person:\n"
        "      populated_from: nonexistent_table\n"
        "      slot_derivations:\n"
        "        id:\n"
        "          populated_from: subject_id\n"
    )
    with caplog.at_level("WARNING", logger="dm_bip.map_data.map_data"):
        results = list(
            multi_spec_transform(
                linkml_test_setup["data_loader"],
                [spec_file],
                linkml_test_setup["source_sv"],
                linkml_test_setup["target_sv"],
                strict=False,
            )
        )
    assert results == []
    assert any("Skipping class derivation Person" in msg for msg in caplog.messages)
    assert any("nonexistent_table" in msg for msg in caplog.messages)


def test_multi_spec_transform_strict_raises_on_missing_data(linkml_test_setup, temp_dir):
    """Test that strict mode raises FileNotFoundError for missing data files."""
    spec_file = Path(temp_dir) / "missing_data_spec.yaml"
    spec_file.write_text(
        "- class_derivations:\n"
        "    Person:\n"
        "      populated_from: nonexistent_table\n"
        "      slot_derivations:\n"
        "        id:\n"
        "          populated_from: subject_id\n"
    )
    with pytest.raises(FileNotFoundError, match="nonexistent_table"):
        list(
            multi_spec_transform(
                linkml_test_setup["data_loader"],
                [spec_file],
                linkml_test_setup["source_sv"],
                linkml_test_setup["target_sv"],
                strict=True,
            )
        )


def test_multi_spec_transform_skips_value_error_non_strict(linkml_test_setup, temp_dir):
    """Test that ValueError from bad slot references is caught in non-strict mode."""
    spec_file = Path(temp_dir) / "bad_slot_spec.yaml"
    spec_file.write_text(
        "- class_derivations:\n"
        "    Person:\n"
        "      populated_from: demographics\n"
        "      slot_derivations:\n"
        "        id:\n"
        "          populated_from: nonexistent_column\n"
    )
    results = list(
        multi_spec_transform(
            linkml_test_setup["data_loader"],
            [spec_file],
            linkml_test_setup["source_sv"],
            linkml_test_setup["target_sv"],
            strict=False,
        )
    )
    assert results == []


def test_multi_spec_transform_strict_raises_on_value_error(linkml_test_setup, temp_dir):
    """Test that ValueError from bad slot references propagates in strict mode."""
    spec_file = Path(temp_dir) / "bad_slot_spec.yaml"
    spec_file.write_text(
        "- class_derivations:\n"
        "    Person:\n"
        "      populated_from: demographics\n"
        "      slot_derivations:\n"
        "        id:\n"
        "          populated_from: nonexistent_column\n"
    )
    with pytest.raises(ValueError):
        list(
            multi_spec_transform(
                linkml_test_setup["data_loader"],
                [spec_file],
                linkml_test_setup["source_sv"],
                linkml_test_setup["target_sv"],
                strict=True,
            )
        )


def test_multi_spec_transform_unexpected_exception_propagates(linkml_test_setup, temp_dir):
    """Test that unexpected exceptions propagate regardless of strict setting."""
    spec_file = Path(temp_dir) / "bad_structure_spec.yaml"
    # Missing class_derivations key entirely — causes KeyError, not caught
    spec_file.write_text("- wrong_key:\n    Person:\n      populated_from: demographics\n")
    with pytest.raises(KeyError):
        list(
            multi_spec_transform(
                linkml_test_setup["data_loader"],
                [spec_file],
                linkml_test_setup["source_sv"],
                linkml_test_setup["target_sv"],
                strict=False,
            )
        )


# --- process_entities Tests ---


def test_process_entities_creates_output_files(linkml_test_setup, temp_dir):
    """Test that process_entities creates output files for each entity."""
    # Only process Person entity which we have specs for
    entities = ["Person"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="test",
        output_postfix="v1",
        output_type="jsonl",
        chunk_size=10,
    )
    output_file = Path(temp_dir) / "test-Person-v1.jsonl"
    assert output_file.exists()
    # Verify content
    with open(output_file) as f:
        lines = f.readlines()
    assert len(lines) == 110
    first_record = json.loads(lines[0])
    assert first_record["id"] == "SUBJ001"


def test_process_entities_no_prefix_no_postfix(linkml_test_setup, temp_dir):
    """Test that process_entities works with empty prefix and postfix."""
    entities = ["Person"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="",
        output_postfix="",
        output_type="jsonl",
        chunk_size=10,
    )
    output_file = Path(temp_dir) / "Person.jsonl"
    assert output_file.exists()


def test_process_entities_prefix_only(linkml_test_setup, temp_dir):
    """Test that process_entities works with only prefix set."""
    entities = ["Person"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="test",
        output_postfix="",
        output_type="jsonl",
        chunk_size=10,
    )
    output_file = Path(temp_dir) / "test-Person.jsonl"
    assert output_file.exists()


def test_process_entities_postfix_only(linkml_test_setup, temp_dir):
    """Test that process_entities works with only postfix set."""
    entities = ["Person"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="",
        output_postfix="v1",
        output_type="jsonl",
        chunk_size=10,
    )
    output_file = Path(temp_dir) / "Person-v1.jsonl"
    assert output_file.exists()


def test_process_entities_skips_missing_specs(linkml_test_setup, temp_dir):
    """Test that process_entities skips entities without spec files."""
    # NonexistentEntity has no specs
    entities = ["NonexistentEntity"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="test",
        output_postfix="v1",
        output_type="jsonl",
    )
    # No output file should be created
    output_file = Path(temp_dir) / "test-NonexistentEntity-v1.jsonl"
    assert not output_file.exists()


def test_process_entities_multiple_entities(linkml_test_setup, temp_dir):
    """Test processing multiple entities."""
    entities = ["Person", "Participant"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="test",
        output_postfix="v1",
        output_type="jsonl",
    )
    assert (Path(temp_dir) / "test-Person-v1.jsonl").exists()
    assert (Path(temp_dir) / "test-Participant-v1.jsonl").exists()


def test_process_entities_tsv_output(linkml_test_setup, temp_dir):
    """Test process_entities with TSV output format."""
    entities = ["Person"]
    process_entities(
        entities=entities,
        data_loader=linkml_test_setup["data_loader"],
        var_dir=linkml_test_setup["spec_dir"],
        source_schemaview=linkml_test_setup["source_sv"],
        target_schemaview=linkml_test_setup["target_sv"],
        output_dir=temp_dir,
        output_prefix="test",
        output_postfix="v1",
        output_type="tsv",
    )
    output_file = Path(temp_dir) / "test-Person-v1.tsv"
    assert output_file.exists()
    with open(output_file) as f:
        lines = f.readlines()
    # Header + 110 data rows
    assert len(lines) == 111
    assert "id" in lines[0]
    assert "gender" in lines[0]


# --- main function Tests ---


def test_main_creates_output_directory(temp_dir):
    """Test that main creates the output directory if it doesn't exist."""
    output_dir = Path(temp_dir) / "new_output"
    assert not output_dir.exists()

    # main() discovers entities from spec files and processes them
    main(
        source_schema=TOY_DATA / "schemas/source-schema.yaml",
        target_schema=TOY_DATA / "schemas/target-schema.yaml",
        data_dir=TOY_DATA / "raw_data",
        var_dir=TOY_DATA / "specs",
        output_dir=output_dir,
        output_prefix="test",
        output_postfix="v1",
        output_type="jsonl",
    )
    assert output_dir.exists()
