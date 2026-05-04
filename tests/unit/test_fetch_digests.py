"""Unit tests for prepare_study.fetch_digests parsers."""

from pathlib import Path

from dm_bip.prepare_study.fetch_digests import (
    DigestValue,
    parse_data_dict,
    parse_var_report,
)

FIXTURES = Path(__file__).parent.parent / "input" / "dbgap_digests"


def test_parse_data_dict_jhs_subject():
    """Round-trip a real JHS data_dict.xml through parse_data_dict and check key fields."""
    dd = parse_data_dict(FIXTURES / "JHS_Subject.data_dict.xml")

    assert dd.data_table_id == "pht001920.v6"
    assert dd.study_id == "phs000286.v7"
    assert dd.participant_set == "2"

    by_name = {v.name: v for v in dd.variables}
    assert "SUBJECT_ID" in by_name
    assert by_name["SUBJECT_ID"].type == "String"
    assert by_name["SUBJECT_ID"].values == []

    consent = by_name["CONSENT"]
    assert consent.type == "encoded value"
    assert consent.description == "Consent group as determined by DAC"
    assert len(consent.values) >= 5
    assert DigestValue(code="0", label=consent.values[0].label) == consent.values[0]
    assert all(v.code.isdigit() for v in consent.values)


def test_parse_var_report_jhs_subject():
    """Round-trip a real JHS var_report.xml through parse_var_report and check key fields."""
    vr = parse_var_report(FIXTURES / "JHS_Subject.var_report.xml")

    assert vr.name == "JHS_Subject"
    assert vr.dataset_id == "pht001920.v6"
    assert vr.study_id == "phs000286.v7"
    assert vr.study_name and "Jackson Heart Study" in vr.study_name

    subject_id_rows = [v for v in vr.variables if v.var_name == "SUBJECT_ID"]
    assert subject_id_rows, "expected at least one SUBJECT_ID row"

    total_row = next((v for v in subject_id_rows if v.id.endswith(".p2")), None)
    assert total_row is not None
    assert total_row.calculated_type == "string"
    assert total_row.stats is not None
    assert total_row.stats.n == 5885
    assert total_row.stats.nulls == 0
