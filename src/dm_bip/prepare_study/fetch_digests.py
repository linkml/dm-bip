"""
Fetch and parse dbGaP variable digest files (data_dict.xml, var_report.xml).

Brings minimal structure over from NHLBI-BDC-DMC-HV/hv-lint/ ahead of the full
hv-lint migration tracked in #312. Cohort version pins (cohorts.yaml) are sourced
from upstream — we do not maintain a local copy.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import defusedxml.ElementTree as DET
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


# --- Parsed-form models ------------------------------------------------------


@dataclass
class DigestValue:
    """One entry in a data dictionary's encoded value list."""

    code: str
    label: str


@dataclass
class DigestVariable:
    """A variable as described in a dbGaP data_dict.xml file."""

    id: str
    name: str
    description: str | None = None
    type: str | None = None
    values: list[DigestValue] = field(default_factory=list)


@dataclass
class DataDictionary:
    """Parsed contents of a dbGaP data_dict.xml file (one phenotype data table)."""

    data_table_id: str
    study_id: str
    participant_set: str | None
    date_created: str | None
    description: str | None
    variables: list[DigestVariable] = field(default_factory=list)


@dataclass
class ReportStat:
    """Summary statistics for a variable from a var_report.xml entry."""

    n: int | None
    nulls: int | None


@dataclass
class ReportVariable:
    """A variable record from a var_report.xml file (one row per total/consent group)."""

    id: str
    var_name: str
    calculated_type: str | None = None
    reported_type: str | None = None
    description: str | None = None
    stats: ReportStat | None = None


@dataclass
class VarReport:
    """Parsed contents of a dbGaP var_report.xml file."""

    name: str
    dataset_id: str
    study_id: str
    study_name: str | None
    participant_set: str | None
    date_created: str | None
    description: str | None
    variables: list[ReportVariable] = field(default_factory=list)


# --- XML parsers -------------------------------------------------------------


def _text(elem: ET.Element | None) -> str | None:
    if elem is None:
        return None
    return (elem.text or "").strip() or None


def parse_data_dict(path: Path) -> DataDictionary:
    """Parse a dbGaP data_dict.xml file into a DataDictionary."""
    root = DET.parse(path).getroot()
    if root.tag != "data_table":
        raise ValueError(f"{path}: expected <data_table> root, got <{root.tag}>")

    variables = []
    for v_elem in root.findall("variable"):
        values = [
            DigestValue(code=val.get("code", ""), label=(val.text or "").strip())
            for val in v_elem.findall("value")
        ]
        variables.append(
            DigestVariable(
                id=v_elem.get("id", ""),
                name=_text(v_elem.find("name")) or "",
                description=_text(v_elem.find("description")),
                type=_text(v_elem.find("type")),
                values=values,
            )
        )

    return DataDictionary(
        data_table_id=root.get("id", ""),
        study_id=root.get("study_id", ""),
        participant_set=root.get("participant_set"),
        date_created=root.get("date_created"),
        description=_text(root.find("description")),
        variables=variables,
    )


def _parse_stats(v_elem: ET.Element) -> ReportStat | None:
    stat = v_elem.find("./total/stats/stat")
    if stat is None:
        return None
    n = stat.get("n")
    nulls = stat.get("nulls")
    return ReportStat(
        n=int(n) if n and n.isdigit() else None,
        nulls=int(nulls) if nulls and nulls.isdigit() else None,
    )


def parse_var_report(path: Path) -> VarReport:
    """Parse a dbGaP var_report.xml file into a VarReport."""
    root = DET.parse(path).getroot()
    if root.tag != "data_table":
        raise ValueError(f"{path}: expected <data_table> root, got <{root.tag}>")

    variables = [
        ReportVariable(
            id=v_elem.get("id", ""),
            var_name=v_elem.get("var_name", ""),
            calculated_type=v_elem.get("calculated_type"),
            reported_type=v_elem.get("reported_type"),
            description=_text(v_elem.find("description")),
            stats=_parse_stats(v_elem),
        )
        for v_elem in root.findall("variable")
    ]

    return VarReport(
        name=root.get("name", ""),
        dataset_id=root.get("dataset_id", ""),
        study_id=root.get("study_id", ""),
        study_name=root.get("study_name"),
        participant_set=root.get("participant_set"),
        date_created=root.get("date_created"),
        description=_text(root.find("description")),
        variables=variables,
    )


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


# --- Canonical data-dictionary TSV output ------------------------------------

DD_TSV_COLUMNS = ("name", "type", "description", "codes", "unit", "min", "max", "uri")

_DBGAP_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "decimal": "decimal",
    "encoded value": "permissible_values",
    "date": "date",
    "datetime": "datetime",
    "time": "time",
    "boolean": "boolean",
}


def _translate_type(dbgap_type: str | None) -> str:
    """Translate a dbGaP <type> value to the schema-automator canonical type vocabulary."""
    if not dbgap_type:
        return "string"
    canonical = _DBGAP_TYPE_MAP.get(dbgap_type.strip().lower())
    if canonical is None:
        logger.debug("Unknown dbGaP type %r; defaulting to 'string'", dbgap_type)
        return "string"
    return canonical


def _sanitize_label(label: str) -> str:
    """Replace characters that conflict with the codes-encoding separators."""
    return label.replace("\t", " ").replace("|", "/").replace(",", ";")


def _encode_codes(values: list[DigestValue]) -> str:
    """Render encoded values as REDCap-style 'code, label | code, label | ...' string."""
    return " | ".join(f"{v.code}, {_sanitize_label(v.label)}" for v in values)


def _dd_row(variable: DigestVariable) -> dict[str, str]:
    """Build one canonical-DD row from a parsed dbGaP variable."""
    return {
        "name": variable.name,
        "type": _translate_type(variable.type),
        "description": variable.description or "",
        "codes": _encode_codes(variable.values),
        "unit": "",
        "min": "",
        "max": "",
        "uri": f"dbgap:{variable.id}" if variable.id else "",
    }


def write_canonical_dd(dd: DataDictionary, output_path: Path) -> Path:
    """Write a parsed DataDictionary to a TSV file in the schema-automator canonical format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write("\t".join(DD_TSV_COLUMNS) + "\n")
        for var in dd.variables:
            row = _dd_row(var)
            f.write("\t".join(row[col] for col in DD_TSV_COLUMNS) + "\n")
    logger.info("Wrote %s (%d variables)", output_path, len(dd.variables))
    return output_path


def _dd_output_filename(dd: DataDictionary) -> str:
    """Build a stable output filename: <phs>.<pht>.dd.tsv."""
    phs = dd.study_id.split(".")[0] if dd.study_id else "unknown_phs"
    pht = dd.data_table_id.split(".")[0] if dd.data_table_id else "unknown_pht"
    return f"{phs}.{pht}.dd.tsv"


def parse_cached_digests(
    cohort: Cohort,
    cache_root: Path = DEFAULT_CACHE_DIR,
    output_root: Path = Path("output"),
) -> list[Path]:
    """Convert all cached data_dict.xml files for a cohort into canonical-DD TSVs (offline)."""
    cache_dir = _study_cache_path(cache_root, cohort)
    if not cache_dir.exists():
        raise FileNotFoundError(f"No cached digests at {cache_dir} (run fetch-digests first)")

    out_dir = output_root / cohort.key / "dd"
    written = []
    for dd_path in sorted(cache_dir.glob("*.data_dict.xml")):
        dd = parse_data_dict(dd_path)
        out_path = out_dir / _dd_output_filename(dd)
        write_canonical_dd(dd, out_path)
        written.append(out_path)
    return written
