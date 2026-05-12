"""
Fetch dbGaP variable digest files (data_dict.xml, var_report.xml).

Cohort version pins (cohorts.yaml) are sourced from upstream
NHLBI-BDC-DMC-HV/hv-lint/cohorts.yaml — we do not maintain a local copy.

Parsing and translation of digest XML into canonical-DD format is handled by
schema-automator's `adapt-dbgap` adapter; this module is only responsible for
populating a local cache the adapter can read from.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

UPSTREAM_COHORTS_YAML_URL = (
    "https://raw.githubusercontent.com/RTIInternational/NHLBI-BDC-DMC-HV/main/hv-lint/cohorts.yaml"
)
DBGAP_FTP_BASE = "https://ftp.ncbi.nlm.nih.gov/dbgap/studies"
NCBI_DELAY_SECONDS = 0.5
DEFAULT_CACHE_DIR = Path(".dbgap-cache")

_DIGEST_FILENAME_RE = re.compile(r'href="([^"]+\.(?:data_dict|var_report)\.xml)"')


# --- Cohort registry ---------------------------------------------------------


@dataclass
class Cohort:
    """A dbGaP cohort entry from cohorts.yaml: study identifier and pinned version."""

    key: str
    study_id: str
    data_version: str
    display_name: str


def load_cohorts(cache_dir: Path = DEFAULT_CACHE_DIR, refresh: bool = False) -> dict[str, Cohort]:
    """Load the cohort registry from upstream NHLBI-BDC-DMC-HV/hv-lint/cohorts.yaml; cached locally."""
    cache_path = cache_dir / "cohorts.yaml"
    if refresh or not cache_path.exists():
        logger.info("Fetching cohorts.yaml from %s", UPSTREAM_COHORTS_YAML_URL)
        with urllib.request.urlopen(UPSTREAM_COHORTS_YAML_URL, timeout=30) as resp:  # noqa: S310
            raw = resp.read()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(raw)
    else:
        raw = cache_path.read_bytes()

    parsed = yaml.safe_load(raw) or {}
    return {
        key: Cohort(
            key=key,
            study_id=entry["study_id"],
            data_version=entry["data_version"],
            display_name=entry.get("display_name", key),
        )
        for key, entry in (parsed.get("cohorts") or {}).items()
    }


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


def _http_get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        return resp.read()


def list_digest_files(cohort: Cohort) -> list[str]:
    """Scrape the dbGaP FTP directory listing for *.data_dict.xml and *.var_report.xml filenames."""
    html = _http_get(_study_url(cohort)).decode("utf-8", errors="replace")
    return sorted(set(_DIGEST_FILENAME_RE.findall(html)))


def fetch_digests(
    cohort: Cohort,
    cache_root: Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
) -> CohortDigests:
    """Fetch all digest files for a cohort into a local cache; skips cached unless refresh=True."""
    out_dir = _study_cache_path(cache_root, cohort)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = CohortDigests(cohort=cohort, cache_root=cache_root)

    filenames = list_digest_files(cohort)
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
