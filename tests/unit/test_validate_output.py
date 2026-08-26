"""Unit tests for the mapped-output validation helper."""

import json

import pytest

from dm_bip.map_data.validate_output import (
    EntityReport,
    Issue,
    entity_output_path,
    load_records,
    main,
    normalize_slot_path,
    read_entity_list,
    render_report,
)

SCHEMA = """
id: https://example.org/target
name: target
prefixes:
  linkml: https://w3id.org/linkml/
default_range: string
imports:
  - linkml:types
classes:
  Participant:
    attributes:
      id:
        identifier: true
      age:
        range: integer
"""


def test_load_records_unwraps_container_key(tmp_path):
    """linkml-map wraps records in a pluralized container key that is stripped."""
    path = tmp_path / "out.yaml"
    path.write_text("participants:\n- id: '1'\n- id: '2'\n")
    assert load_records(path) == [{"id": "1"}, {"id": "2"}]


def test_load_records_multi_document_stream(tmp_path):
    """Current linkml-map emits one YAML document per record, separated by '---'."""
    path = tmp_path / "out.yaml"
    path.write_text("id: '1'\nage: 3\n---\nid: '2'\nage: 4\n")
    assert load_records(path) == [{"id": "1", "age": 3}, {"id": "2", "age": 4}]


def test_load_records_accepts_bare_list(tmp_path):
    """A top-level list is treated as the record collection."""
    path = tmp_path / "out.yaml"
    path.write_text("- id: '1'\n- id: '2'\n")
    assert load_records(path) == [{"id": "1"}, {"id": "2"}]


def test_load_records_treats_multi_key_doc_as_single_record(tmp_path):
    """A dict with several keys is a record, not a container."""
    path = tmp_path / "out.yaml"
    path.write_text("id: '1'\nage: 3\n")
    assert load_records(path) == [{"id": "1", "age": 3}]


def test_load_records_empty_file(tmp_path):
    """An empty document yields no records rather than raising."""
    path = tmp_path / "out.yaml"
    path.write_text("")
    assert load_records(path) == []


def test_load_records_jsonl(tmp_path):
    """JSONL input is read line by line, ignoring blank lines."""
    path = tmp_path / "out.jsonl"
    path.write_text('{"id": "1"}\n\n{"id": "2"}\n')
    assert load_records(path) == [{"id": "1"}, {"id": "2"}]


def test_load_records_json_container(tmp_path):
    """JSON input is unwrapped the same way as YAML."""
    path = tmp_path / "out.json"
    path.write_text(json.dumps({"participants": [{"id": "1"}]}))
    assert load_records(path) == [{"id": "1"}]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$.observations[0].value", "$.observations[*].value"),
        ("$.observations[12].a[3].b", "$.observations[*].a[*].b"),
        ("$.id", "$.id"),
    ],
)
def test_normalize_slot_path_collapses_indices(raw, expected):
    """Array indices collapse so one systematic problem is one finding."""
    assert normalize_slot_path(raw) == expected


def test_entity_output_path_omits_empty_parts(tmp_path):
    """Path building mirrors the Makefile's _map_base, skipping empty prefix/postfix."""
    assert entity_output_path(tmp_path, "Participant") == tmp_path / "Participant.yaml"
    assert entity_output_path(tmp_path, "Participant", "TOY", "-data") == tmp_path / "TOY-Participant--data.yaml"
    assert entity_output_path(tmp_path, "P", fmt="jsonl") == tmp_path / "P.jsonl"


def test_read_entity_list_missing_file(tmp_path):
    """A missing entity list yields no entities rather than raising."""
    assert read_entity_list(tmp_path / "nope") == []


def test_read_entity_list_skips_blank_lines(tmp_path):
    """Blank lines in the entity list are ignored."""
    path = tmp_path / "entities"
    path.write_text("Participant\n\n  Demography  \n")
    assert read_entity_list(path) == ["Participant", "Demography"]


def test_render_report_flags_invalid_records(tmp_path):
    """The report summarizes counts and lists aggregated findings."""
    report = EntityReport(entity="Participant", path=tmp_path / "p.yaml", total_records=2, checked_records=2)
    report.invalid_records = 2
    report.issues[("$.id", "type", "string")] = Issue(
        slot_path="$.id", constraint="type", expected="string", count=2, examples=["1001 is not of type 'string'"]
    )
    body = render_report([report], tmp_path / "schema.yaml", 0)
    assert "2 invalid (100.0%)" in body
    assert "$.id" in body
    assert "2x" in body
    assert "advisory" in body


def test_render_report_clean_run(tmp_path):
    """A clean run says so explicitly."""
    report = EntityReport(entity="Participant", path=tmp_path / "p.yaml", total_records=1, checked_records=1)
    body = render_report([report], tmp_path / "schema.yaml", 0)
    assert "No conformance issues found." in body
    assert "[ok]" in body


def test_empty_output_is_not_reported_as_clean(tmp_path):
    """Zero records means the map step emitted nothing — never a pass."""
    report = EntityReport(entity="Participant", path=tmp_path / "p.yaml")
    assert not report.is_clean


def test_main_flags_empty_entity_file(tmp_path):
    """An empty mapped file is surfaced as a problem, not silently reported ok."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1"}])
    (mapped / "Participant.yaml").write_text("")
    code, report = _run(tmp_path, schema, mapped, entity_list)
    assert code == 0
    body = report.read_text()
    assert "no records in output" in body
    assert "[ok]" not in body


def _write_inputs(tmp_path, records):
    schema = tmp_path / "schema.yaml"
    schema.write_text(SCHEMA)
    mapped = tmp_path / "mapped"
    mapped.mkdir()
    (mapped / "Participant.yaml").write_text(json.dumps({"participants": records}))
    entity_list = tmp_path / "entities"
    entity_list.write_text("Participant\n")
    return schema, mapped, entity_list


def _run(tmp_path, schema, mapped, entity_list, extra=None):
    report = tmp_path / "report.txt"
    argv = [
        "--target-schema",
        str(schema),
        "--mapped-dir",
        str(mapped),
        "--entity-list",
        str(entity_list),
        "--report",
        str(report),
        *(extra or []),
    ]
    return main(argv), report


def test_main_reports_nonconforming_output(tmp_path):
    """An integer in a string slot is reported, and the run still exits 0."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": 1001, "age": 3}])
    code, report = _run(tmp_path, schema, mapped, entity_list)
    assert code == 0
    body = report.read_text()
    assert "1 invalid" in body
    assert "$.id" in body


def test_main_exits_zero_on_conforming_output(tmp_path):
    """Conforming output produces a clean report and exit 0."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1001", "age": 3}])
    code, report = _run(tmp_path, schema, mapped, entity_list)
    assert code == 0
    assert "No conformance issues found." in report.read_text()


def test_main_limit_caps_records_checked(tmp_path):
    """--limit bounds how many records are validated per entity."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": n} for n in range(10)])
    code, report = _run(tmp_path, schema, mapped, entity_list, ["--limit", "3"])
    assert code == 0
    body = report.read_text()
    assert "3 checked" in body
    assert "Record limit:  3" in body


def test_main_writes_report_when_schema_missing(tmp_path):
    """A missing target schema is recorded in the report, not a crash."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1"}])
    code, report = _run(tmp_path, tmp_path / "absent.yaml", mapped, entity_list)
    assert code == 0
    assert "Skipped" in report.read_text()


def test_main_writes_report_when_no_entities(tmp_path):
    """An empty entity list still produces a report so Make sees the target built."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1"}])
    entity_list.write_text("")
    code, report = _run(tmp_path, schema, mapped, entity_list)
    assert code == 0
    assert "Skipped" in report.read_text()


def test_main_skips_unsupported_format(tmp_path):
    """TSV output is skipped with a reason: flattening makes validation unreliable."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1"}])
    (mapped / "Participant.tsv").write_text("id\n1\n")
    code, report = _run(tmp_path, schema, mapped, entity_list, ["--format", "tsv"])
    assert code == 0
    assert "unsupported format" in report.read_text()


def test_main_reports_missing_entity_file(tmp_path):
    """A listed entity with no output file is skipped with a reason, not a crash."""
    schema, mapped, entity_list = _write_inputs(tmp_path, [{"id": "1"}])
    entity_list.write_text("Participant\nAbsent\n")
    code, report = _run(tmp_path, schema, mapped, entity_list)
    assert code == 0
    assert "file not found" in report.read_text()
