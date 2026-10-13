"""
Fetch dbGaP variable digest files (data_dict.xml, var_report.xml).

Cohort version pins are sourced from the upstream NHLBI-BDC-DMC-HV
cache-fetcher manifests (``hv_dataqc/cache_fetcher/manifests/_manifest-<key>.yaml``)
— we do not maintain a local copy. That manifest set is the single source of
truth for dbGaP study versions across the upstream tools, so pinning to it keeps
us from drifting away from them.

This module only populates a local cache; it does not read the XML. Two consumers do:
schema-automator's `adapt-dbgap` adapter, which translates a pair into canonical-DD format,
and `dm_bip.variable_lib.dbgap`, which indexes them for variable library entries.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

UPSTREAM_MANIFESTS_API_URL = (
    "https://api.github.com/repos/RTIInternational/NHLBI-BDC-DMC-HV/contents/hv_dataqc/cache_fetcher/manifests"
)
DBGAP_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/dbgap/studies"
NCBI_DELAY_SECONDS = 0.5
DEFAULT_CACHE_DIR = Path(".dbgap-cache")

_DIGEST_FILENAME_RE = re.compile(r'href="([^"/]+\.(?:data_dict|var_report)\.xml)"')
_MANIFEST_FILENAME_RE = re.compile(r"^_manifest-([a-z0-9_]+)\.yaml$")
_FILENAME_PHT_RE = re.compile(r"\.(pht\d+)\.")

DIGEST_KINDS = frozenset({"data_dict", "var_report"})


def pht_from_filename(filename: str) -> str | None:
    """
    Pull the bare ``pht`` accession out of a digest filename.

    Both digest kinds embed it — ``phs000280.v8.pht004027.v3.ABI04.data_dict.xml`` — so a
    caller that knows which datasets it wants can select files without opening any of them.

    >>> pht_from_filename("phs000280.v8.pht004027.v3.ABI04.data_dict.xml")
    'pht004027'
    >>> pht_from_filename("cohorts.yaml") is None
    True
    """
    match = _FILENAME_PHT_RE.search(filename)
    return match.group(1) if match else None


# --- HTTP --------------------------------------------------------------------


def _http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        return resp.read()


# --- Cohort registry ---------------------------------------------------------


@dataclass
class Cohort:
    """A dbGaP cohort entry from an upstream manifest: study identifier and pinned version."""

    key: str
    study_id: str
    data_version: str
    display_name: str


def _fetch_manifests(manifest_dir: Path) -> None:
    """Download every upstream ``_manifest-<key>.yaml`` into the local cache directory."""
    logger.info("Fetching cohort manifests from %s", UPSTREAM_MANIFESTS_API_URL)
    entries = json.loads(_http_get(UPSTREAM_MANIFESTS_API_URL).decode("utf-8"))
    manifest_dir.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        name = entry.get("name", "")
        if not _MANIFEST_FILENAME_RE.fullmatch(name):
            continue
        logger.debug("Fetching %s", name)
        time.sleep(NCBI_DELAY_SECONDS)
        (manifest_dir / name).write_bytes(_http_get(entry["download_url"]))


def _parse_manifest(path: Path) -> Cohort | None:
    """Read one manifest's ``current_version`` block into a Cohort; None if the block is unusable."""
    key = _MANIFEST_FILENAME_RE.fullmatch(path.name).group(1)
    current = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("current_version")
    if not isinstance(current, dict):
        logger.warning("%s has no 'current_version' mapping; skipping", path.name)
        return None
    study_id, data_version = current.get("study_id"), current.get("data_version")
    if not study_id or not data_version:
        logger.warning("%s 'current_version' is missing study_id/data_version; skipping", path.name)
        return None
    return Cohort(
        key=key,
        study_id=study_id,
        data_version=data_version,
        display_name=current.get("study_name", key),
    )


def load_cohorts(cache_dir: Path = DEFAULT_CACHE_DIR, refresh: bool = False) -> dict[str, Cohort]:
    """Load the cohort registry from the upstream cache-fetcher manifests; cached locally."""
    manifest_dir = cache_dir / "manifests"
    cached = sorted(manifest_dir.glob("_manifest-*.yaml"))
    if refresh or not cached:
        _fetch_manifests(manifest_dir)
        cached = sorted(manifest_dir.glob("_manifest-*.yaml"))

    cohorts = {}
    for path in cached:
        cohort = _parse_manifest(path)
        if cohort is not None:
            cohorts[cohort.key] = cohort
    return cohorts


def cohort_for_study(study_id: str, cohorts: dict[str, Cohort]) -> Cohort | None:
    """
    Find the cohort pinned to a study accession, or None.

    Lets a caller that already knows the study — a transformation spec directory carries it
    in ``researchstudy.yaml`` — skip naming the cohort key. The accession is compared bare
    because a study identifier may arrive prefixed (``bdchm:Study/phs000280``) or versioned
    (``phs000280.v8``) while the manifests pin it plain.
    """
    wanted = study_id.rsplit("/", 1)[-1].split(".", 1)[0]
    for _, cohort in sorted(cohorts.items()):
        if cohort.study_id.split(".", 1)[0] == wanted:
            return cohort
    return None


# --- Fetch -------------------------------------------------------------------


@dataclass
class CohortDigests:
    """Result of fetching digest files for a cohort: paths to cached data_dict and var_report XMLs."""

    cohort: Cohort
    cache_root: Path
    data_dicts: list[Path] = field(default_factory=list)
    var_reports: list[Path] = field(default_factory=list)


def _study_url(cohort: Cohort) -> str:
    return f"{DBGAP_FTP_BASE}/{cohort.study_id}/{cohort.study_id}.{cohort.data_version}/pheno_variable_summaries/"


def _study_cache_path(cache_root: Path, cohort: Cohort) -> Path:
    return cache_root / cohort.key / f"{cohort.study_id}.{cohort.data_version}" / "pheno_variable_summaries"


def list_digest_files(cohort: Cohort) -> list[str]:
    """Scrape the dbGaP FTP directory listing for *.data_dict.xml and *.var_report.xml filenames."""
    html = _http_get(_study_url(cohort)).decode("utf-8", errors="replace")
    return sorted(set(_DIGEST_FILENAME_RE.findall(html)))


def _wanted(filename: str, datasets: set[str] | None, kinds: frozenset[str] | None) -> bool:
    """Decide whether a listed digest filename is in scope for this fetch."""
    if kinds is not None and not any(filename.endswith(f".{kind}.xml") for kind in kinds):
        return False
    if datasets is None:
        return True
    pht = pht_from_filename(filename)
    if pht is None:
        logger.warning("No pht accession in %s; excluding it from a filtered fetch", filename)
        return False
    return pht in datasets


def fetch_digests(
    cohort: Cohort,
    cache_root: Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
    *,
    datasets: set[str] | None = None,
    kinds: frozenset[str] | None = None,
) -> CohortDigests:
    """
    Fetch a cohort's digest files into a local cache; skips cached unless refresh=True.

    ``datasets`` limits the fetch to the given bare ``pht`` accessions and ``kinds`` to the
    given digest kinds (``data_dict``, ``var_report``); both default to fetching everything.
    Filtering costs no extra requests because the pht is in the filename — for ARIC, a caller
    that only wants the datasets its transformation specs name pulls 326 files, not 736.
    """
    out_dir = _study_cache_path(cache_root, cohort)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = CohortDigests(cohort=cohort, cache_root=cache_root)

    filenames = list_digest_files(cohort)
    if datasets is not None or kinds is not None:
        filenames = [name for name in filenames if _wanted(name, datasets, kinds)]
    if not filenames:
        logger.warning("No digest files found at %s", _study_url(cohort))
        return result

    base_url = _study_url(cohort)
    for filename in filenames:
        local_path = out_dir / filename
        if local_path.exists() and not refresh:
            logger.debug("Cached: %s", local_path.name)
        else:
            logger.info("Fetching %s", filename)
            time.sleep(NCBI_DELAY_SECONDS)
            local_path.write_bytes(_http_get(base_url + filename))

        if filename.endswith(".data_dict.xml"):
            result.data_dicts.append(local_path)
        elif filename.endswith(".var_report.xml"):
            result.var_reports.append(local_path)

    result.data_dicts.sort()
    result.var_reports.sort()
    return result


def cached_digests(
    cohort: Cohort,
    cache_root: Path = DEFAULT_CACHE_DIR,
    *,
    datasets: set[str] | None = None,
    kinds: frozenset[str] | None = None,
) -> CohortDigests:
    """
    Collect a cohort's already-fetched digest files without touching the network.

    The offline counterpart to ``fetch_digests``, for repeat runs and CI. Applies the same
    filters so a caller gets the same view either way.
    """
    out_dir = _study_cache_path(cache_root, cohort)
    result = CohortDigests(cohort=cohort, cache_root=cache_root)
    if not out_dir.is_dir():
        logger.warning("No cached digests at %s", out_dir)
        return result

    for path in sorted(out_dir.iterdir()):
        if not _wanted(path.name, datasets, kinds):
            continue
        if path.name.endswith(".data_dict.xml"):
            result.data_dicts.append(path)
        elif path.name.endswith(".var_report.xml"):
            result.var_reports.append(path)

    return result


# --- Pair discovery and Makefile-include emission ----------------------------
#
# dbGaP's filename convention puts the participant-set segment (`.p<N>`) into
# var_report filenames but not into data_dict filenames:
#     phs000286.v7.pht001920.v6.JHS_Subject.data_dict.xml
#     phs000286.v7.pht001920.v6.p2.JHS_Subject.var_report.xml
#
# Pure Make pattern rules can't pair these (no shared stem). The fetcher knows
# both filenames at fetch time, so we emit a tiny `digest_pairs.mk` the Makefile
# includes — explicit pair vars keyed by the data_dict basename.


_PARTICIPANT_SET_RE = re.compile(r"^p\d+$")


def _identity_key(filename: str) -> tuple[str, ...]:
    """Identity key for pairing: filename stem minus suffix minus any `.p<N>` segment."""
    stem = filename.rsplit(".data_dict.xml", 1)[0].rsplit(".var_report.xml", 1)[0]
    return tuple(part for part in stem.split(".") if not _PARTICIPANT_SET_RE.fullmatch(part))


def pair_digests(digests: CohortDigests) -> list[tuple[Path, Path]]:
    """Pair each data_dict with its matching var_report by phs.pht.<table> identity."""
    vr_index = {_identity_key(p.name): p for p in digests.var_reports}
    pairs = []
    for dd in digests.data_dicts:
        vr = vr_index.get(_identity_key(dd.name))
        if vr is None:
            logger.warning("No var_report match for %s", dd.name)
            continue
        pairs.append((dd, vr))
    return pairs


def write_pairs_mk(digests: CohortDigests, output_path: Path) -> Path:
    """Emit a Makefile include with explicit data_dict/var_report pair mappings."""
    pairs = pair_digests(digests)
    lines = [
        "# Generated by `dm-bip fetch-digests` - do not edit",
        f"# Cohort: {digests.cohort.key} ({digests.cohort.study_id}.{digests.cohort.data_version})",
        "",
    ]
    keys = [dd.name.removesuffix(".data_dict.xml") for dd, _ in pairs]
    lines.append("DBGAP_DIGEST_KEYS := " + " ".join(keys))
    lines.append("")
    for (dd, vr), key in zip(pairs, keys, strict=True):
        lines.append(f"DBGAP_DD_{key} := {dd}")
        lines.append(f"DBGAP_VR_{key} := {vr}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path
