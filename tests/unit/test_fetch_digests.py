"""Unit tests for prepare_study.fetch_digests fetcher-layer logic."""

from pathlib import Path

import pytest

from dm_bip.prepare_study import fetch_digests as fd_mod
from dm_bip.prepare_study.fetch_digests import (
    _DIGEST_FILENAME_RE,
    Cohort,
    CohortDigests,
    _study_cache_path,
    _study_url,
    fetch_digests,
    list_digest_files,
    load_cohorts,
    pair_digests,
    write_pairs_mk,
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

    def test_rejects_path_separators(self):
        """A href containing `/` is not captured — guards against path traversal."""
        html = '<a href="../escape.data_dict.xml">bad</a><a href="ok.data_dict.xml">good</a>'
        assert _DIGEST_FILENAME_RE.findall(html) == ["ok.data_dict.xml"]


class TestListDigestFiles:
    """list_digest_files fetches HTML and extracts digest filenames."""

    def test_returns_sorted_unique_filenames(self, monkeypatch, cohort):
        """Duplicates collapse and results sort alphabetically."""
        html = (
            '<a href="b.data_dict.xml">b</a>'
            '<a href="a.var_report.xml">a</a>'
            '<a href="b.data_dict.xml">b again</a>'
        )
        monkeypatch.setattr(fd_mod, "_http_get", lambda url: html.encode("utf-8"))
        assert list_digest_files(cohort) == ["a.var_report.xml", "b.data_dict.xml"]

    def test_passes_study_url_to_http_get(self, monkeypatch, cohort):
        """The URL we GET is the study URL for the cohort."""
        captured = {}

        def fake_get(url):
            captured["url"] = url
            return b""

        monkeypatch.setattr(fd_mod, "_http_get", fake_get)
        list_digest_files(cohort)
        assert captured["url"] == _study_url(cohort)


class TestFetchDigests:
    """fetch_digests populates the cache, respects refresh, and separates dd/vr."""

    @pytest.fixture()
    def no_sleep(self, monkeypatch):
        """Disable the inter-request delay during tests."""
        monkeypatch.setattr(fd_mod, "NCBI_DELAY_SECONDS", 0)

    def test_separates_data_dicts_and_var_reports(self, monkeypatch, cohort, tmp_path, no_sleep):
        """Each filename lands in the right bucket based on its suffix."""
        filenames = ["a.data_dict.xml", "a.p2.var_report.xml", "b.data_dict.xml"]
        monkeypatch.setattr(fd_mod, "list_digest_files", lambda c: filenames)
        monkeypatch.setattr(fd_mod, "_http_get", lambda url: b"<xml/>")

        result = fetch_digests(cohort, cache_root=tmp_path)
        assert [p.name for p in result.data_dicts] == ["a.data_dict.xml", "b.data_dict.xml"]
        assert [p.name for p in result.var_reports] == ["a.p2.var_report.xml"]

    def test_skips_cached_when_refresh_false(self, monkeypatch, cohort, tmp_path, no_sleep):
        """If a file already exists in the cache, refresh=False does not re-download it."""
        out_dir = _study_cache_path(tmp_path, cohort)
        out_dir.mkdir(parents=True)
        (out_dir / "a.data_dict.xml").write_bytes(b"cached")

        monkeypatch.setattr(fd_mod, "list_digest_files", lambda c: ["a.data_dict.xml"])
        called = {"count": 0}

        def fake_get(url):
            called["count"] += 1
            return b"fresh"

        monkeypatch.setattr(fd_mod, "_http_get", fake_get)
        fetch_digests(cohort, cache_root=tmp_path, refresh=False)
        # _http_get only called for list_digest_files emulation? It's replaced too — so 0 calls expected.
        assert called["count"] == 0
        assert (out_dir / "a.data_dict.xml").read_bytes() == b"cached"

    def test_refresh_true_overwrites_cache(self, monkeypatch, cohort, tmp_path, no_sleep):
        """refresh=True re-downloads even when the file is already cached."""
        out_dir = _study_cache_path(tmp_path, cohort)
        out_dir.mkdir(parents=True)
        (out_dir / "a.data_dict.xml").write_bytes(b"old")

        monkeypatch.setattr(fd_mod, "list_digest_files", lambda c: ["a.data_dict.xml"])
        monkeypatch.setattr(fd_mod, "_http_get", lambda url: b"new")

        fetch_digests(cohort, cache_root=tmp_path, refresh=True)
        assert (out_dir / "a.data_dict.xml").read_bytes() == b"new"


class TestPairDigests:
    """pair_digests matches data_dicts with var_reports by phs.pht.<table> identity."""

    def _make_result(self, tmp_path, cohort, dd_names, vr_names):
        out_dir = _study_cache_path(tmp_path, cohort)
        out_dir.mkdir(parents=True)
        result = CohortDigests(cohort=cohort, cache_root=tmp_path)
        for name in dd_names:
            p = out_dir / name
            p.write_bytes(b"")
            result.data_dicts.append(p)
        for name in vr_names:
            p = out_dir / name
            p.write_bytes(b"")
            result.var_reports.append(p)
        return result

    def test_pairs_when_var_report_has_participant_set_segment(self, cohort, tmp_path):
        """data_dict 'X.data_dict.xml' pairs with var_report 'X.p2.var_report.xml'."""
        result = self._make_result(
            tmp_path,
            cohort,
            dd_names=["phs000286.v7.pht001920.v6.JHS_Subject.data_dict.xml"],
            vr_names=["phs000286.v7.pht001920.v6.p2.JHS_Subject.var_report.xml"],
        )
        pairs = pair_digests(result)
        assert len(pairs) == 1
        dd, vr = pairs[0]
        assert dd.name == "phs000286.v7.pht001920.v6.JHS_Subject.data_dict.xml"
        assert vr.name == "phs000286.v7.pht001920.v6.p2.JHS_Subject.var_report.xml"

    def test_pairs_when_no_participant_set(self, cohort, tmp_path):
        """data_dict and var_report with identical stems also pair correctly."""
        result = self._make_result(
            tmp_path,
            cohort,
            dd_names=["a.data_dict.xml"],
            vr_names=["a.var_report.xml"],
        )
        pairs = pair_digests(result)
        assert len(pairs) == 1

    def test_skips_data_dict_with_no_var_report_match(self, cohort, tmp_path, caplog):
        """Unmatched data_dict logs a warning and is omitted from the pair list."""
        result = self._make_result(
            tmp_path,
            cohort,
            dd_names=["lonely.data_dict.xml", "matched.data_dict.xml"],
            vr_names=["matched.p2.var_report.xml"],
        )
        with caplog.at_level("WARNING"):
            pairs = pair_digests(result)
        assert len(pairs) == 1
        assert pairs[0][0].name == "matched.data_dict.xml"
        assert any("lonely.data_dict.xml" in rec.message for rec in caplog.records)


class TestWritePairsMk:
    """write_pairs_mk emits a Makefile include with explicit DBGAP_DD_ / DBGAP_VR_ vars."""

    def test_writes_keys_and_pair_vars(self, cohort, tmp_path):
        """Output contains DBGAP_DIGEST_KEYS and one DBGAP_DD_/DBGAP_VR_ pair per match."""
        out_dir = _study_cache_path(tmp_path, cohort)
        out_dir.mkdir(parents=True)
        dd = out_dir / "phs000286.v7.pht001920.v6.JHS_Subject.data_dict.xml"
        vr = out_dir / "phs000286.v7.pht001920.v6.p2.JHS_Subject.var_report.xml"
        dd.write_bytes(b"")
        vr.write_bytes(b"")
        result = CohortDigests(cohort=cohort, cache_root=tmp_path, data_dicts=[dd], var_reports=[vr])

        out = write_pairs_mk(result, tmp_path / "digest_pairs.mk")
        text = out.read_text(encoding="utf-8")
        key = "phs000286.v7.pht001920.v6.JHS_Subject"
        assert f"DBGAP_DIGEST_KEYS := {key}" in text
        assert f"DBGAP_DD_{key} := {dd}" in text
        assert f"DBGAP_VR_{key} := {vr}" in text


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
