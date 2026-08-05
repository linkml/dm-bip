"""Tests for Condition trans-spec generation via the entity registry."""

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from dm_bip.cli import app
from dm_bip.trans_spec_gen.generate_trans_specs import generate_yaml

SAMPLE_CSV = Path(__file__).parents[1] / "input" / "make_yaml" / "condition_sample.csv"


def _run(tmp_path, cohort="chs"):
    return generate_yaml(input_csv=SAMPLE_CSV, output_dir=tmp_path, entity="Condition", cohort=cohort)


def _read_yaml(tmp_path, cohort, quality, varname):
    return yaml.safe_load((tmp_path / cohort / quality / f"{varname}.yaml").read_text())


class TestFileOutput:
    """File creation, organization, and completeness routing."""

    def test_complete_rows_route_to_good(self, tmp_path):
        """Rows with all required slots populated land in good/."""
        _run(tmp_path)
        good_files = sorted(p.stem for p in (tmp_path / "chs" / "good").glob("*.yaml"))
        assert good_files == ["angina", "copd", "fam_stroke", "quoted"]

    def test_incomplete_row_routes_to_bad(self, tmp_path):
        """Rows missing a required slot (onto_id, or value_mappings) land in bad/."""
        _run(tmp_path)
        bad_files = sorted(p.stem for p in (tmp_path / "chs" / "bad").glob("*.yaml"))
        assert bad_files == ["incomplete", "novmap"]

    def test_missing_value_mappings_renders_without_crash(self, tmp_path):
        """A row lacking value_mappings still renders valid YAML, omitting the value_mappings block."""
        _run(tmp_path)
        parsed = _read_yaml(tmp_path, "chs", "bad", "novmap")
        status = parsed[0]["class_derivations"]["Condition"]["slot_derivations"]["condition_status"]
        assert "value_mappings" not in status
        assert status["populated_from"] == "phv00104001"

    def test_output_is_valid_yaml(self, tmp_path):
        """All generated Condition files parse as valid YAML."""
        for path in _run(tmp_path):
            yaml.safe_load(path.read_text())


class TestConditionSlots:
    """The Condition slot shape matches the NHLBI-BDC-DMC-HV -ingest reference."""

    def _slots(self, tmp_path):
        parsed = _read_yaml(tmp_path, "chs", "good", "copd")
        return parsed[0]["class_derivations"]["Condition"]

    def test_populated_from_uses_pht(self, tmp_path):
        """Top-level populated_from is the row's pht."""
        _run(tmp_path)
        assert self._slots(tmp_path)["populated_from"] == "pht001452"

    def test_participant_and_visit_use_uuid5(self, tmp_path):
        """associated_participant and associated_visit render uuid5 expressions."""
        _run(tmp_path)
        slots = self._slots(tmp_path)["slot_derivations"]
        assert slots["associated_participant"]["expr"] == (
            'uuid5("https://w3id.org/bdchm/Participant", str({phv00100285}) + ":CHS")'
        )
        assert slots["associated_visit"]["expr"] == (
            'uuid5("https://w3id.org/bdchm/Visit", str({phv00100285}) + ":CHS BASELINE BOTH")'
        )

    def test_condition_status_value_mappings(self, tmp_path):
        """value_mappings expands the code=ENUM column into a mapping."""
        _run(tmp_path)
        status = self._slots(tmp_path)["slot_derivations"]["condition_status"]
        assert status["populated_from"] == "phv00100497"
        assert status["value_mappings"] == {"0": "ABSENT", "1": "PRESENT"}

    def test_value_mapping_code_with_apostrophe(self, tmp_path):
        """A mapping code with a single quote escapes, and a trailing empty pair is skipped."""
        _run(tmp_path)
        parsed = _read_yaml(tmp_path, "chs", "good", "quoted")
        status = parsed[0]["class_derivations"]["Condition"]["slot_derivations"]["condition_status"]
        assert status["value_mappings"] == {"No": "ABSENT", "Don't know": "UNKNOWN", "Yes": "PRESENT"}

    def test_value_field_with_apostrophe_escapes(self, tmp_path):
        """An apostrophe in a single-quoted value field (associated_evidence) escapes to valid YAML."""
        _run(tmp_path)
        parsed = _read_yaml(tmp_path, "chs", "good", "quoted")
        slots = parsed[0]["class_derivations"]["Condition"]["slot_derivations"]
        assert slots["associated_evidence"]["value"] == "physician's note"

    def test_concept_provenance_and_evidence(self, tmp_path):
        """condition_concept, provenance, relationship, and evidence render from the row."""
        _run(tmp_path)
        slots = self._slots(tmp_path)["slot_derivations"]
        assert slots["condition_concept"]["value"] == "MONDO:0005002"
        assert slots["condition_provenance"]["value"] == "PATIENT_SELF-REPORTED_CONDITION"
        assert slots["relationship_to_participant"]["value"] == "ONESELF"
        assert slots["associated_evidence"]["value"] == "self-report questionnaire"

    def test_relationship_defaults_to_oneself_when_blank(self, tmp_path):
        """A blank relationship_to_participant column falls back to ONESELF."""
        _run(tmp_path)
        slots = self._slots(tmp_path)["slot_derivations"]
        assert slots["relationship_to_participant"]["value"] == "ONESELF"

    def test_relationship_uses_explicit_value(self, tmp_path):
        """A family-history row renders its explicit relationship (e.g. an OMOP relative code)."""
        _run(tmp_path)
        parsed = _read_yaml(tmp_path, "chs", "good", "fam_stroke")
        slots = parsed[0]["class_derivations"]["Condition"]["slot_derivations"]
        assert slots["relationship_to_participant"]["value"] == "OMOP:4053608"


class TestUnknownEntity:
    """An unregistered entity fails loudly, with a clean CLI error."""

    def test_generate_yaml_raises_for_unknown_entity(self, tmp_path):
        """generate_yaml raises ValueError when no EntitySpec is registered for the entity."""
        with pytest.raises(ValueError, match="No registered entity spec"):
            generate_yaml(input_csv=SAMPLE_CSV, output_dir=tmp_path, entity="Nonexistent", cohort="chs")

    def test_cli_unknown_entity_exits_cleanly(self, tmp_path):
        """The CLI reports an unknown entity as a parameter error, not a traceback."""
        result = CliRunner().invoke(
            app,
            ["generate-trans-specs", "-i", str(SAMPLE_CSV), "-o", str(tmp_path), "-c", "chs", "-e", "Nonexistent"],
        )
        assert result.exit_code != 0
        assert "not a registered entity" in result.output
