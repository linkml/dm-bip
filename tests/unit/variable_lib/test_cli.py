"""Tests for the extract-variable-library CLI command's dbGaP wiring."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dm_bip import cli as cli_module
from dm_bip.cli import app
from dm_bip.prepare_study import fetch_digests as fd_mod

MAPPING_INPUT = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_SPECS = MAPPING_INPUT / "ARIC-ingest"

runner = CliRunner()


@pytest.fixture()
def no_network(monkeypatch):
    """Fail loudly on any HTTP call, so an offline claim is actually enforced."""

    def fail(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(fd_mod, "_http_get", fail)


class TestCohortResolution:
    """Reaching for the cohort registry is a network call, so it must be earned."""

    def test_specs_without_a_study_accession_never_load_cohorts(self, tmp_path, monkeypatch, no_network):
        """
        Skip the registry when no spec names a study.

        A spec directory with no researchstudy.yaml gets a placeholder id, which can never
        match a cohort — so the registry must not be fetched just to discover that.
        """
        specs = tmp_path / "no-study"
        specs.mkdir()
        (specs / "spec.yaml").write_text(
            "class_derivations:\n"
            "  Obs:\n"
            "    populated_from: pht000001\n"
            "    slot_derivations:\n"
            "      value:\n"
            "        populated_from: phv00000001\n"
        )

        def fail(*args, **kwargs):
            raise AssertionError("load_cohorts should not be called without a study accession")

        monkeypatch.setattr(fd_mod, "load_cohorts", fail)
        result = runner.invoke(app, ["extract-variable-library", str(specs), "--dbgap-cache", str(tmp_path / "c")])
        assert result.exit_code == 0, result.output
        assert "No study accession in these specs" in result.stderr

    def test_unknown_cohort_key_exits_with_a_usage_error(self, tmp_path, monkeypatch):
        """An explicit --cohort that does not exist is the caller's mistake, not a silent skip."""
        monkeypatch.setattr(fd_mod, "load_cohorts", lambda **kwargs: {})
        result = runner.invoke(
            app,
            ["extract-variable-library", str(ARIC_SPECS), "--cohort", "nope", "--dbgap-cache", str(tmp_path)],
        )
        assert result.exit_code == 2
        assert "Unknown cohort 'nope'" in result.stderr

    def test_a_real_accession_is_looked_up(self, tmp_path, monkeypatch, no_network):
        """The ARIC fixture carries phs000280, so the registry is worth consulting."""
        monkeypatch.setattr(fd_mod, "load_cohorts", lambda **kwargs: {})
        result = runner.invoke(app, ["extract-variable-library", str(ARIC_SPECS), "--dbgap-cache", str(tmp_path)])
        assert result.exit_code == 0, result.output
        assert "No dbGaP cohort matches these specs" in result.stderr


class TestPhsPattern:
    """What counts as a study accession worth a registry lookup."""

    @pytest.mark.parametrize(
        ("study_id", "matches"),
        [
            ("bdchm:Study/phs000280", True),
            ("phs000280", True),
            ("dmcprov:example_study_one", False),
            ("bdchm:Study/ARIC-ingest", False),
        ],
    )
    def test_recognizes_only_real_accessions(self, study_id, matches):
        """Placeholder ids built from a directory name carry no phs."""
        assert bool(cli_module._PHS_RE.search(study_id)) is matches
