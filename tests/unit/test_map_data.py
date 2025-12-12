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
    get_schema,
    get_spec_files,
    json_stream,
    jsonl_stream,
    main,
    multi_spec_transform,
    process_entities,
    rewrite_header_and_pad,
    tsv_stream,
    yaml_stream,
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
        f.write("class_derivations:\n")
        f.write("    Participant:\n")
        f.write("      populated_from: test_data\n")

    # Another YAML file with search string
    yaml_match2 = os.path.join(temp_dir, "another_spec.yaml")
    with open(yaml_match2, "w") as f:
        f.write("class_derivations:\n")
        f.write("    Participant:\n")
        f.write("      populated_from: other_data\n")

    # YAML file without the search string
    yaml_no_match = os.path.join(temp_dir, "no_match.yaml")
    with open(yaml_no_match, "w") as f:
        f.write("class_derivations:\n")
        f.write("    Person:\n")
        f.write("      populated_from: person_data\n")

    # Non-YAML file with search string (should be ignored)
    txt_match = os.path.join(temp_dir, "match.txt")
    with open(txt_match, "w") as f:
        f.write("    Participant:\n")

    return temp_dir


@pytest.fixture(autouse=True)
def reset_tsv_stream_headers():
    """Reset tsv_stream.headers before and after each test."""
    if hasattr(tsv_stream, "headers"):
        del tsv_stream.headers
    yield
    if hasattr(tsv_stream, "headers"):
        del tsv_stream.headers


# --- DataLoader Tests ---


def test_dataloader_init_stores_base_path(data_loader_dir):
    """Test that __init__ stores the base path correctly."""
    loader = DataLoader(data_loader_dir)
    assert loader.base_path == data_loader_dir


def test_dataloader_contains_returns_true_for_existing_file(data_loader_dir):
    """Test __contains__ returns True when file exists."""
    loader = DataLoader(data_loader_dir)
    assert "test_data" in loader


def test_dataloader_contains_returns_false_for_missing_file(data_loader_dir):
    """Test __contains__ returns False when file does not exist."""
    loader = DataLoader(data_loader_dir)
    assert "nonexistent" not in loader


def test_dataloader_getitem_returns_iterator_for_existing_file(data_loader_dir):
    """Test __getitem__ returns an iterator of instances from TSV."""
    loader = DataLoader(data_loader_dir)
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
    loader = DataLoader(data_loader_dir)
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


# --- json_stream Tests ---


def test_json_stream_single_chunk():
    """Test JSON output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]]
    result = list(json_stream(chunks, "persons"))
    assert len(result) == 1
    parsed = json.loads(result[0])
    assert parsed["persons"] == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


def test_json_stream_multiple_chunks():
    """Test JSON output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    result = list(json_stream(chunks, "items"))
    assert len(result) == 2
    assert '"items"' in result[0]


def test_json_stream_empty():
    """Test JSON output with no chunks."""
    result = list(json_stream([], "items"))
    assert result == []


# --- jsonl_stream Tests ---


def test_jsonl_stream_single_chunk():
    """Test JSONL output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]]
    result = list(jsonl_stream(chunks))
    assert len(result) == 1
    lines = result[0].strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": 1, "name": "Alice"}
    assert json.loads(lines[1]) == {"id": 2, "name": "Bob"}


def test_jsonl_stream_multiple_chunks():
    """Test JSONL output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    result = list(jsonl_stream(chunks))
    assert len(result) == 2
    assert json.loads(result[0].strip()) == {"id": 1}
    assert json.loads(result[1].strip()) == {"id": 2}


def test_jsonl_stream_each_object_on_own_line():
    """Test that each object is on its own line."""
    chunks = [[{"a": 1}, {"b": 2}, {"c": 3}]]
    result = list(jsonl_stream(chunks))
    lines = result[0].strip().split("\n")
    assert len(lines) == 3


# --- yaml_stream Tests ---


def test_yaml_stream_single_chunk():
    """Test YAML output with a single chunk."""
    chunks = [[{"id": 1, "name": "Alice"}]]
    result = list(yaml_stream(chunks, "persons"))
    assert len(result) == 1
    parsed = yaml.safe_load(result[0])
    assert parsed["persons"] == [{"id": 1, "name": "Alice"}]


def test_yaml_stream_multiple_chunks():
    """Test YAML output with multiple chunks."""
    chunks = [[{"id": 1}], [{"id": 2}]]
    result = list(yaml_stream(chunks, "items"))
    assert len(result) == 2
    assert "items:" in result[0]


# --- tsv_stream Tests ---


def test_tsv_stream_basic_output():
    """Test basic TSV output with flat objects."""
    chunks = [[{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]]
    result = list(tsv_stream(chunks))
    lines = "".join(result).strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    headers = lines[0].split("\t")
    assert "id" in headers
    assert "name" in headers


def test_tsv_stream_nested_objects_flattened():
    """Test that nested objects are flattened with separator."""
    chunks = [[{"id": "1", "person": {"name": "Alice", "age": 30}}]]
    result = list(tsv_stream(chunks))
    lines = "".join(result).strip().split("\n")
    headers = lines[0].split("\t")
    assert "person__name" in headers
    assert "person__age" in headers


def test_tsv_stream_custom_separator():
    """Test custom column separator."""
    chunks = [[{"id": "1", "name": "Alice"}]]
    result = list(tsv_stream(chunks, sep=","))
    lines = "".join(result).strip().split("\n")
    assert "," in lines[0]


def test_tsv_stream_missing_values_empty_string():
    """Test that missing values become empty strings when key is in headers."""
    # First object establishes headers, second object is missing a key
    chunks = [[{"id": "1", "name": "Alice"}, {"id": "2"}]]
    result = list(tsv_stream(chunks))
    # Parse without strip() to preserve empty trailing columns
    lines = "".join(result).rstrip("\n").split("\n")
    headers = lines[0].split("\t")
    # Headers include both id and name from first object
    assert "name" in headers
    # Second data row should have empty value for name
    row2_values = lines[2].split("\t")
    name_idx = headers.index("name")
    assert row2_values[name_idx] == ""


def test_tsv_stream_headers_attribute_set_when_headers_change():
    """Test that tsv_stream.headers is set when new columns appear after first row."""
    chunks = [[{"id": "1"}], [{"id": "2", "new_col": "value"}]]
    list(tsv_stream(chunks))
    # Headers attribute should be set because new columns appeared
    assert hasattr(tsv_stream, "headers")
    assert "new_col" in tsv_stream.headers


def test_tsv_stream_headers_attribute_not_set_when_consistent():
    """Test that headers attribute is not set when columns are consistent."""
    chunks = [[{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]]
    list(tsv_stream(chunks))
    assert not hasattr(tsv_stream, "headers")


# --- rewrite_header_and_pad Tests ---


def test_rewrite_header_and_pad_rewrites_header():
    """Test that the header is rewritten with final columns."""
    original_lines = ["a\tb\n", "1\t2\n", "3\t4\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(rewrite_header_and_pad(chunks, final_header))
    combined = "".join(result)
    lines = combined.strip().split("\n")
    assert lines[0] == "a\tb\tc"


def test_rewrite_header_and_pad_pads_short_rows():
    """Test that rows with fewer columns are padded."""
    # Original file has 2 columns, final header has 3
    original_lines = ["a\tb\n", "1\t2\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(rewrite_header_and_pad(chunks, final_header))
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
    result = list(rewrite_header_and_pad(chunks, final_header))
    combined = "".join(result)
    lines = combined.strip().split("\n")
    assert len(lines) == 3  # header + 2 data rows


def test_rewrite_header_and_pad_custom_separator():
    """Test with a custom separator."""
    original_lines = ["a,b\n", "1,2\n"]
    chunks = iter([original_lines])
    final_header = ["a", "b", "c"]
    result = list(rewrite_header_and_pad(chunks, final_header, sep=","))
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
    spec_files = get_spec_files(linkml_test_setup["spec_dir"], "    Person:")
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
    spec_files = get_spec_files(linkml_test_setup["spec_dir"], "    Participant:")
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
        stream_func=jsonl_stream,
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
        stream_func=jsonl_stream,
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
        stream_func=jsonl_stream,
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
        stream_func=tsv_stream,
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

    # main() will try to process the hardcoded entity list, most won't have specs
    # but it should still create the directory
    main(
        source_schema=str(TOY_DATA / "schemas/source-schema.yaml"),
        target_schema=str(TOY_DATA / "schemas/target-schema.yaml"),
        data_dir=str(TOY_DATA / "raw_data"),
        var_dir=str(TOY_DATA / "specs"),
        output_dir=str(output_dir),
        output_prefix="test",
        output_postfix="v1",
        output_type="jsonl",
    )
    assert output_dir.exists()
