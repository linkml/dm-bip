"""Tests for Condition trans-spec generation via the entity registry."""

from pathlib import Path

import yaml

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
        assert good_files == ["angina", "copd"]

    def test_incomplete_row_routes_to_bad(self, tmp_path):
        """A row missing a required slot (onto_id) lands in bad/."""
        _run(tmp_path)
        bad_files = sorted(p.stem for p in (tmp_path / "chs" / "bad").glob("*.yaml"))
        assert bad_files == ["incomplete"]

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

    def test_concept_provenance_and_evidence(self, tmp_path):
        """condition_concept, provenance, relationship, and evidence render from the row."""
        _run(tmp_path)
        slots = self._slots(tmp_path)["slot_derivations"]
        assert slots["condition_concept"]["value"] == "MONDO:0005002"
        assert slots["condition_provenance"]["value"] == "PATIENT_SELF-REPORTED_CONDITION"
        assert slots["relationship_to_participant"]["value"] == "ONESELF"
        assert slots["associated_evidence"]["value"] == "self-report questionnaire"
