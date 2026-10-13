"""Tests for the extract-variable-library CLI command's dbGaP wiring."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dm_bip import cli as cli_module
from dm_bip.cli import app
from dm_bip.prepare_study import fetch_digests as fd_mod
from dm_bip.prepare_study.fetch_digests import Cohort

MAPPING_INPUT = Path(__file__).parents[2] / "input" / "mapping_prov"
ARIC_SPECS = MAPPING_INPUT / "ARIC-ingest"

VARIABLE_LIB_INPUT = Path(__file__).parents[2] / "input" / "variable_lib"
DIGESTS = VARIABLE_LIB_INPUT / "dbgap"
COLLIDING = (
    DIGESTS / "phs000007.v35.pht004063.v1.COLLIDING.data_dict.xml",
    DIGESTS / "phs000007.v35.pht004063.v1.p16.COLLIDING.var_report.xml",
)
MATCHING = (
    DIGESTS / "phs000007.v35.pht004063.v1.MATCHING.data_dict.xml",
    DIGESTS / "phs000007.v35.pht004063.v1.p16.MATCHING.var_report.xml",
)

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
            ["extract-variable-library", str(ARIC_SPECS), "--cohort", "phs000101", "--dbgap-cache", str(tmp_path)],
        )
        assert result.exit_code == 2
        assert "Unknown cohort 'phs000101'" in result.stderr

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


class TestPartialDatasetMatch:
    """
    A cohort that resolves is not a cohort that matches.

    A ``pht`` is unique across all of dbGaP, but nothing stops a spec from naming one
    already taken by another study — a fabricated corpus can mint a well-formed accession
    without checking whether it is free. The cohort then resolves, its listing yields a
    digest for that pht, and the dictionary inside describes somebody else's variables.

    The ARIC fixture names three datasets. This cohort publishes exactly one of them.
    """

    @pytest.fixture()
    def serve(self, monkeypatch, tmp_path):
        """Resolve --cohort to a study publishing pht004063, with a dictionary of my choosing."""

        def _serve(digests):
            served = {path.name: path for path in digests}
            monkeypatch.setattr(fd_mod, "NCBI_DELAY_SECONDS", 0)
            monkeypatch.setattr(
                fd_mod,
                "load_cohorts",
                lambda **kwargs: {"fhs": Cohort("fhs", "phs000007", "v35.p16", "Framingham Heart Study (FHS)")},
            )
            monkeypatch.setattr(fd_mod, "list_digest_files", lambda cohort: sorted(served))
            monkeypatch.setattr(fd_mod, "_http_get", lambda url: served[url.rsplit("/", 1)[-1]].read_bytes())

            output = tmp_path / "variable-library.yaml"
            result = runner.invoke(
                app,
                [
                    "extract-variable-library",
                    str(ARIC_SPECS),
                    "--cohort",
                    "fhs",
                    "--dbgap-cache",
                    str(tmp_path / "cache"),
                    "-o",
                    str(output),
                ],
            )
            assert result.exit_code == 0, result.output
            return result, output.read_text()

        return _serve

    @pytest.fixture()
    def collision(self, serve):
        """Run against a dictionary that declares none of the variables the specs name."""
        return serve(COLLIDING)

    def test_names_the_datasets_it_could_not_find(self, collision):
        """The two datasets this cohort does not publish are reported, by accession."""
        result, _ = collision
        assert "2 of 3 datasets have no dbGaP data dictionary: pht012502, pht012811" in result.stderr

    def test_says_nothing_about_the_dataset_it_did_find(self, collision):
        """pht004063 was fetched, so it is absent from the missing list — and that is the trap."""
        result, _ = collision
        missing = [line for line in result.stderr.splitlines() if "no dbGaP data dictionary" in line]
        assert missing and "pht004063" not in missing[0]

    def test_the_digests_really_were_downloaded(self, collision, tmp_path):
        """
        The fetch succeeded; that is what makes the empty result worth a test.

        Without this the next assertion would also pass if nothing had been fetched at all.
        """
        cached = sorted(path.name for path in (tmp_path / "cache").rglob("*.xml"))
        assert cached == [path.name for path in COLLIDING]

    def test_a_colliding_dictionary_contributes_nothing(self, collision):
        """Lookup keys on the phv, so a matched dataset full of foreign variables fills no slots."""
        _, document = collision
        for foreign in ("TNFA", "EXAM_CYCLE", "pg/mL", "Tumor necrosis factor"):
            assert foreign not in document

    def test_nothing_is_typed_but_the_run_does_not_fail(self, collision):
        """With no dictionary describing the specs' variables, every one is held back; the run still succeeds."""
        result, document = collision
        assert "0 entries from 8 source variables" in result.stderr
        assert "phv00204719" not in document

    def test_the_same_pht_declaring_the_right_variable_does_enrich(self, serve):
        """
        The control: change only the dictionary's contents and the slots appear.

        Same cohort, same pht, same fetch — so the empty result above is the collision and
        not a broken pipeline.
        """
        _, document = serve(MATCHING)
        assert "BMI01" in document
        # The observed bounds come through the adapter. The unit does not yet: the dbGaP
        # adapter drops <unit> (linkml/schema-automator#231, item 2), so "kg/m2" cannot be
        # asserted on this path until that lands. TestDdDir covers the unit via a DD TSV.
        assert "minimum_value: '13.1'" in document
        assert "maximum_value: '61.2'" in document


class TestDdDir:
    """
    ``--dd-dir`` reads canonical DD TSVs the pipeline already adapted, and fetches nothing.

    The other options stay accepted so the command's shape can keep evolving, but with a DD
    directory in hand none of them is consulted: no cohort lookup, no network, no cache.
    """

    @pytest.fixture()
    def document(self, monkeypatch, tmp_path):
        """Run against one DD TSV declaring BMI01 for pht004063, with the network cut."""

        def _no_network(url):
            raise AssertionError(f"--dd-dir must not fetch, but requested {url}")

        monkeypatch.setattr(fd_mod, "_http_get", _no_network)

        dd_dir = tmp_path / "dd"
        dd_dir.mkdir()
        columns = "name\ttype\tdescription\tcodes\tunit\tmin\tmax\turi\n"
        row = "BMI01\tdecimal\tBody mass index, exam 1.\t\tkg/m2\t13.1\t61.2\tdbgap:phv00204719.v1\n"
        (dd_dir / "phs000007.v35.pht004063.v1.MATCHING.dd.tsv").write_text(columns + row, encoding="utf-8")

        output = tmp_path / "variable-library.yaml"
        result = runner.invoke(
            app,
            [
                "extract-variable-library",
                str(ARIC_SPECS),
                "--dd-dir",
                str(dd_dir),
                "-o",
                str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        return result, output.read_text()

    def test_enriches_from_the_tsv(self, document):
        """Name, unit and bounds all arrive, the unit included because the TSV carries it."""
        _, text = document
        assert "BMI01" in text
        assert "unit: kg/m2" in text
        assert "minimum_value: '13.1'" in text

    def test_names_the_datasets_with_no_dd(self, document):
        """Coverage is reported against the DD directory, by accession."""
        result, _ = document
        assert "2 of 3 datasets have no canonical DD: pht012502, pht012811" in result.stderr

    def test_file_name_comes_from_the_dd_filename(self, document):
        """The pipeline names each DD after its data_dict, which carries dbGaP's table name."""
        _, text = document
        assert "file_name: MATCHING" in text
