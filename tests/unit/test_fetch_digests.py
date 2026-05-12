"""Unit tests for prepare_study.fetch_digests fetcher-layer logic."""

from pathlib import Path

import pytest

from dm_bip.prepare_study.fetch_digests import (
    _DIGEST_FILENAME_RE,
    Cohort,
    _study_cache_path,
    _study_url,
    load_cohorts,
)

FIXTURES = Path(__file__).parent.parent / "input" / "dbgap_digests"


@pytest.fixture()
def cohort():
    """Provide a single cohort for path-construction tests."""
    return Cohort(key="jhs", study_id="phs000286", data_version="v7.p2", display_name="Jackson Heart Study")


class TestLoadCohorts:
    """Parse cohorts.yaml into a {key: Cohort} dict."""

    def test_parses_cohort_fields(self, tmp_path):
        """Each entry yields a Cohort with study_id, data_version, display_name."""
        (tmp_path / "cohorts.yaml").write_text(
            "cohorts:\n"
            "  jhs:\n"
            "    study_id: phs000286\n"
            "    data_version: v7.p2\n"
            "    display_name: Jackson Heart Study\n"
            "  aric:\n"
            "    study_id: phs000280\n"
            "    data_version: v8.p2\n"
            "    display_name: ARIC\n",
        )
        cohorts = load_cohorts(cache_dir=tmp_path)
        assert set(cohorts) == {"jhs", "aric"}
        assert cohorts["jhs"].study_id == "phs000286"
        assert cohorts["jhs"].data_version == "v7.p2"
        assert cohorts["jhs"].display_name == "Jackson Heart Study"

    def test_display_name_defaults_to_key(self, tmp_path):
        """When display_name is omitted, the cohort key is used."""
        (tmp_path / "cohorts.yaml").write_text(
            "cohorts:\n  foo:\n    study_id: phs999999\n    data_version: v1.p1\n",
        )
        cohorts = load_cohorts(cache_dir=tmp_path)
        assert cohorts["foo"].display_name == "foo"

    def test_uses_cached_file_without_refresh(self, tmp_path):
        """An existing cohorts.yaml is read; refresh=False does not re-fetch."""
        (tmp_path / "cohorts.yaml").write_text("cohorts:\n  jhs:\n    study_id: phs000286\n    data_version: v7.p2\n")
        # No network call needed because cache is present and refresh=False.
        cohorts = load_cohorts(cache_dir=tmp_path, refresh=False)
        assert "jhs" in cohorts


class TestDigestFilenameRegex:
    """The HTML scrape regex must pick out only the two digest file suffixes."""

    def test_matches_data_dict_and_var_report(self):
        """Both digest suffixes are picked up from typical FTP-listing HTML."""
        html = (
            '<a href="JHS_Subject.data_dict.xml">JHS_Subject.data_dict.xml</a>'
            '<a href="JHS_Subject.var_report.xml">JHS_Subject.var_report.xml</a>'
        )
        assert _DIGEST_FILENAME_RE.findall(html) == [
            "JHS_Subject.data_dict.xml",
            "JHS_Subject.var_report.xml",
        ]

    def test_ignores_other_xml_files(self):
        """Files that aren't .data_dict.xml or .var_report.xml are skipped."""
        html = '<a href="MULTI.MULTI.xml">other</a><a href="JHS.data_dict.xml">dd</a>'
        assert _DIGEST_FILENAME_RE.findall(html) == ["JHS.data_dict.xml"]


class TestPathConstruction:
    """Cache + URL path layout for a cohort."""

    def test_study_url(self, cohort):
        """FTP URL composes cohort study_id and version into the dbGaP layout."""
        assert _study_url(cohort) == (
            "https://ftp.ncbi.nlm.nih.gov/dbgap/studies/phs000286/phs000286.v7.p2/pheno_variable_summaries/"
        )

    def test_study_cache_path(self, cohort, tmp_path):
        """Cache path mirrors the FTP layout with the cohort key on top."""
        assert _study_cache_path(tmp_path, cohort) == (
            tmp_path / "jhs" / "phs000286.v7.p2" / "pheno_variable_summaries"
        )
