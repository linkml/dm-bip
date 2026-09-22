"""Unit tests for prepare_study.fetch_digests fetcher-layer logic."""

import json
import logging
from pathlib import Path

import pytest

from dm_bip.prepare_study import fetch_digests as fd_mod
from dm_bip.prepare_study.fetch_digests import (
    _DIGEST_FILENAME_RE,
    _MANIFEST_FILENAME_RE,
    Cohort,
    CohortDigests,
    _study_cache_path,
    _study_url,
    _wanted,
    cohort_for_study,
    fetch_digests,
    list_digest_files,
    load_cohorts,
    pair_digests,
    pht_from_filename,
    write_pairs_mk,
)

FIXTURES = Path(__file__).parent.parent / "input" / "dbgap_digests"


@pytest.fixture()
def cohort():
    """Provide a single cohort for path-construction tests."""
    return Cohort(key="jhs", study_id="phs000286", data_version="v7.p2", display_name="Jackson Heart Study")


def _write_manifest(manifest_dir, key, body):
    """Write a `_manifest-<key>.yaml` into a cache's manifests/ dir."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"_manifest-{key}.yaml").write_text(body)


class TestManifestFilenameRegex:
    """Only well-formed `_manifest-<key>.yaml` names are accepted as manifests."""

    def test_captures_cohort_key(self):
        """The cohort key is the filename segment between the prefix and the suffix."""
        assert _MANIFEST_FILENAME_RE.fullmatch("_manifest-hchs_sol.yaml").group(1) == "hchs_sol"

    def test_rejects_other_names(self):
        """README and non-manifest YAML in the same directory are ignored."""
        assert _MANIFEST_FILENAME_RE.fullmatch("README.md") is None
        assert _MANIFEST_FILENAME_RE.fullmatch("cohorts.yaml") is None

    def test_rejects_path_separators(self):
        """A name containing `/` is not matched — guards against path traversal on write."""
        assert _MANIFEST_FILENAME_RE.fullmatch("../_manifest-evil.yaml") is None


class TestLoadCohorts:
    """Parse the upstream cache-fetcher manifests into a {key: Cohort} dict."""

    def test_parses_current_version_fields(self, tmp_path):
        """Each manifest's current_version block yields a Cohort keyed by its filename."""
        manifests = tmp_path / "manifests"
        _write_manifest(
            manifests,
            "jhs",
            'current_version:\n  study_id: "phs000286"\n  study_name: "Jackson Heart Study"\n  data_version: "v7.p2"\n',
        )
        _write_manifest(
            manifests,
            "aric",
            'current_version:\n  study_id: "phs000280"\n  study_name: "ARIC"\n  data_version: "v8.p2"\n',
        )
        cohorts = load_cohorts(cache_dir=tmp_path)
        assert set(cohorts) == {"jhs", "aric"}
        assert cohorts["jhs"].study_id == "phs000286"
        assert cohorts["jhs"].data_version == "v7.p2"
        assert cohorts["jhs"].display_name == "Jackson Heart Study"

    def test_ignores_unrelated_keys_in_manifest(self, tmp_path):
        """Manifests carry much more than current_version; the rest is not read."""
        _write_manifest(
            tmp_path / "manifests",
            "jhs",
            "current_version:\n"
            '  study_id: "phs000286"\n'
            '  data_version: "v7.p2"\n'
            "  dbgap_references:\n"
            '    study_homepage:\n      url: "https://example.invalid"\n'
            "prior_versions:\n"
            '  - data_version: "v6.p1"\n',
        )
        assert load_cohorts(cache_dir=tmp_path)["jhs"].data_version == "v7.p2"

    def test_display_name_defaults_to_key(self, tmp_path):
        """When study_name is omitted, the cohort key is used."""
        _write_manifest(
            tmp_path / "manifests",
            "foo",
            'current_version:\n  study_id: "phs999999"\n  data_version: "v1.p1"\n',
        )
        assert load_cohorts(cache_dir=tmp_path)["foo"].display_name == "foo"

    def test_skips_manifest_without_current_version(self, tmp_path):
        """A manifest missing the current_version block is dropped, not fatal."""
        manifests = tmp_path / "manifests"
        _write_manifest(manifests, "broken", "prior_versions:\n  - data_version: v1.p1\n")
        _write_manifest(
            manifests,
            "jhs",
            'current_version:\n  study_id: "phs000286"\n  data_version: "v7.p2"\n',
        )
        assert set(load_cohorts(cache_dir=tmp_path)) == {"jhs"}

    def test_skips_manifest_missing_version_pin(self, tmp_path):
        """current_version without study_id/data_version cannot pin a URL, so it is dropped."""
        _write_manifest(
            tmp_path / "manifests",
            "jhs",
            'current_version:\n  study_name: "Jackson Heart Study"\n',
        )
        assert load_cohorts(cache_dir=tmp_path) == {}

    def test_uses_cached_manifests_without_refresh(self, tmp_path, monkeypatch):
        """Existing manifests are read; refresh=False does not re-fetch."""

        def fail(*args, **kwargs):
            raise AssertionError("should not fetch when cache is populated")

        monkeypatch.setattr(fd_mod, "_http_get", fail)
        _write_manifest(
            tmp_path / "manifests",
            "jhs",
            'current_version:\n  study_id: "phs000286"\n  data_version: "v7.p2"\n',
        )
        assert "jhs" in load_cohorts(cache_dir=tmp_path, refresh=False)

    def test_fetches_when_cache_is_empty(self, tmp_path, monkeypatch):
        """With no cached manifests, the listing is fetched and each manifest downloaded."""
        monkeypatch.setattr(fd_mod, "NCBI_DELAY_SECONDS", 0)
        listing = json.dumps(
            [
                {"name": "_manifest-jhs.yaml", "download_url": "https://example.invalid/jhs"},
                {"name": "README.md", "download_url": "https://example.invalid/readme"},
            ]
        ).encode()
        manifest = b'current_version:\n  study_id: "phs000286"\n  data_version: "v7.p2"\n'
        requested = []

        def fake_get(url):
            requested.append(url)
            return listing if url == fd_mod.UPSTREAM_MANIFESTS_API_URL else manifest

        monkeypatch.setattr(fd_mod, "_http_get", fake_get)
        cohorts = load_cohorts(cache_dir=tmp_path)
        assert set(cohorts) == {"jhs"}
        assert requested == [fd_mod.UPSTREAM_MANIFESTS_API_URL, "https://example.invalid/jhs"]
        assert (tmp_path / "manifests" / "_manifest-jhs.yaml").exists()
        assert not (tmp_path / "manifests" / "README.md").exists()

    def test_refresh_overwrites_cached_manifests(self, tmp_path, monkeypatch):
        """refresh=True re-fetches even when the cache is populated."""
        monkeypatch.setattr(fd_mod, "NCBI_DELAY_SECONDS", 0)
        _write_manifest(
            tmp_path / "manifests",
            "jhs",
            'current_version:\n  study_id: "phs000286"\n  data_version: "v6.p1"\n',
        )
        listing = json.dumps([{"name": "_manifest-jhs.yaml", "download_url": "https://example.invalid/jhs"}]).encode()
        fresh = b'current_version:\n  study_id: "phs000286"\n  data_version: "v7.p2"\n'
        monkeypatch.setattr(
            fd_mod,
            "_http_get",
            lambda url: listing if url == fd_mod.UPSTREAM_MANIFESTS_API_URL else fresh,
        )
        assert load_cohorts(cache_dir=tmp_path, refresh=True)["jhs"].data_version == "v7.p2"


class TestPhtFromFilename:
    """Both digest kinds embed the pht, so scope can be decided without opening a file."""

    @pytest.mark.parametrize(
        "filename",
        [
            "phs000280.v8.pht004027.v3.ABI04.data_dict.xml",
            "phs000280.v8.pht004027.v3.p2.ABI04.var_report.xml",
        ],
    )
    def test_reads_the_accession_from_either_kind(self, filename):
        """The var_report's extra .p<N> segment does not move the pht."""
        assert pht_from_filename(filename) == "pht004027"

    def test_returns_none_without_one(self):
        """A file that is not a digest has no pht to find."""
        assert pht_from_filename("cohorts.yaml") is None


class TestWanted:
    """The fetch filter selects on dataset and kind, both optional."""

    def test_keeps_requested_datasets_across_both_kinds(self):
        """A wanted pht brings its data_dict and its var_report."""
        assert _wanted("phs000280.v8.pht004027.v3.ABI04.data_dict.xml", {"pht004027"}, None)
        assert _wanted("phs000280.v8.pht004027.v3.p2.ABI04.var_report.xml", {"pht004027"}, None)

    def test_drops_unrequested_datasets(self):
        """A pht no spec names is not fetched."""
        assert not _wanted("phs000280.v8.pht009999.v3.OTHER.data_dict.xml", {"pht004027"}, None)

    def test_kind_filter_selects_data_dicts(self):
        """data_dict-only mode halves the download."""
        assert _wanted("phs000280.v8.pht004027.v3.ABI04.data_dict.xml", None, frozenset({"data_dict"}))
        assert not _wanted("phs000280.v8.pht004027.v3.p2.ABI04.var_report.xml", None, frozenset({"data_dict"}))

    def test_filters_compose(self):
        """Dataset and kind both have to pass."""
        wanted = {"pht004027"}
        kinds = frozenset({"data_dict"})
        assert _wanted("phs000280.v8.pht004027.v3.ABI04.data_dict.xml", wanted, kinds)
        assert not _wanted("phs000280.v8.pht004027.v3.p2.ABI04.var_report.xml", wanted, kinds)
        assert not _wanted("phs000280.v8.pht009999.v3.OTHER.data_dict.xml", wanted, kinds)

    def test_excludes_and_warns_on_a_filename_with_no_pht(self, caplog):
        """Excluding is right, but silently is not — a filtered fetch must say what it dropped."""
        with caplog.at_level(logging.WARNING):
            assert not _wanted("weird.data_dict.xml", {"pht004027"}, None)
        assert "No pht accession" in caplog.text


class TestDigestFilter:
    """fetch_digests applies the filter between listing and download."""

    @pytest.fixture()
    def no_sleep(self, monkeypatch):
        """Disable the inter-request delay during tests."""
        monkeypatch.setattr(fd_mod, "NCBI_DELAY_SECONDS", 0)

    @pytest.fixture()
    def listing(self, monkeypatch):
        """Stand in for the FTP listing with two datasets, both kinds."""
        names = [
            "phs000280.v8.pht000001.v1.KEEP.data_dict.xml",
            "phs000280.v8.pht000001.v1.p2.KEEP.var_report.xml",
            "phs000280.v8.pht000002.v1.DROP.data_dict.xml",
            "phs000280.v8.pht000002.v1.p2.DROP.var_report.xml",
        ]
        monkeypatch.setattr(fd_mod, "list_digest_files", lambda c: names)
        monkeypatch.setattr(fd_mod, "_http_get", lambda url: b"<xml/>")
        return names

    def test_no_filter_fetches_everything(self, cohort, tmp_path, listing, no_sleep):
        """The default is unchanged behavior — this guards every pre-existing caller."""
        result = fetch_digests(cohort, cache_root=tmp_path)
        assert len(result.data_dicts) == 2
        assert len(result.var_reports) == 2

    def test_dataset_filter_limits_the_fetch(self, cohort, tmp_path, listing, no_sleep):
        """Only the requested pht is downloaded, and nothing else reaches disk."""
        result = fetch_digests(cohort, cache_root=tmp_path, datasets={"pht000001"})
        assert [p.name for p in result.data_dicts] == ["phs000280.v8.pht000001.v1.KEEP.data_dict.xml"]
        assert [p.name for p in result.var_reports] == ["phs000280.v8.pht000001.v1.p2.KEEP.var_report.xml"]
        assert not list(tmp_path.rglob("*DROP*"))

    def test_kind_filter_skips_var_reports(self, cohort, tmp_path, listing, no_sleep):
        """data_dict-only mode leaves var_reports unfetched."""
        result = fetch_digests(cohort, cache_root=tmp_path, kinds=frozenset({"data_dict"}))
        assert len(result.data_dicts) == 2
        assert result.var_reports == []

    def test_filtering_everything_out_returns_empty(self, monkeypatch, cohort, tmp_path, listing, no_sleep):
        """An empty scope is not an error, and must not reach the network."""

        def fail(url):
            raise AssertionError("should not fetch when the filter keeps nothing")

        monkeypatch.setattr(fd_mod, "_http_get", fail)
        result = fetch_digests(cohort, cache_root=tmp_path, datasets={"pht999999"})
        assert result.data_dicts == []
        assert result.var_reports == []


class TestCohortForStudy:
    """A study accession picks its cohort, so callers need not name the key."""

    @pytest.fixture()
    def cohorts(self):
        """Provide a two-cohort registry."""
        return {
            "aric": Cohort(key="aric", study_id="phs000280", data_version="v8.p2", display_name="ARIC"),
            "jhs": Cohort(key="jhs", study_id="phs000286", data_version="v7.p2", display_name="JHS"),
        }

    @pytest.mark.parametrize(
        "study_id",
        ["phs000280", "phs000280.v8", "bdchm:Study/phs000280", "bdchm:Study/phs000280.v8.p2"],
    )
    def test_matches_however_the_accession_arrives(self, study_id, cohorts):
        """Prefixed and versioned forms both reduce to the bare accession the manifests pin."""
        assert cohort_for_study(study_id, cohorts).key == "aric"

    def test_returns_none_for_an_unpinned_study(self, cohorts):
        """A study with no manifest is a real condition; the caller falls back."""
        assert cohort_for_study("phs999999", cohorts) is None


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
        html = '<a href="b.data_dict.xml">b</a><a href="a.var_report.xml">a</a><a href="b.data_dict.xml">b again</a>'
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
