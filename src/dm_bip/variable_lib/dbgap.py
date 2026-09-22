"""
Read dbGaP variable digest XML into an index keyed by accession.

dbGaP publishes two files per pheno table, and a variable library entry needs both:

- ``*.data_dict.xml`` — what the study *declares*. One ``<variable>`` per column carrying
  ``<name>``, ``<description>``, ``<type>``, ``<unit>``, ``<logical_min>``/``<logical_max>``,
  ``<comment>``, and ``<value code="X">label</value>`` children for encoded values.
- ``*.var_report.xml`` — what the data *contains*. Adds ``calculated_type`` and a ``<stat>``
  element with the observed ``min``/``max``, which is the only place those numbers exist:
  across the ARIC variables our transformation specs reference, ``<logical_min>`` is present
  on none of them and ``<stat min>`` on every numeric one.

Why not ``schema_automator.adapters.dbgap.parse_dbgap_digest``: it is schema-driven by a
metamodel whose ``Variable`` class declares exactly eight attributes — id, name, description,
reported_type, calculated_type, values, min, max — so ``<unit>``, ``<logical_min>``,
``<logical_max>`` and ``<comment>`` have nowhere to land and are silently dropped. Four of
the eleven slots this module exists to fill are unreachable through that API.

This module only reads XML. Mapping any of it onto variable library slots is
``dbgap_metadata``'s job.
"""

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

# A var_report variable id is `<phv>.v<N>.p<M>` for the total set and `<phv>.v<N>.p<M>.c<K>`
# per consent group. Only the total-set row contributes; the consent-group rows restate it.
_TOTAL_SET_RE = re.compile(r"\.p\d+$")


def _parse(path: Path) -> etree._Element:
    """
    Parse a digest file with entity resolution, DTD loading, and network access disabled.

    These files come off an FTP listing rather than from us, so the parser is hardened
    against the XML defaults even though NCBI is the publisher.
    """
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, remove_comments=True)
    return etree.parse(str(path), parser).getroot()


def _bare(accession: str) -> str:
    """
    Strip version and participant-set suffixes from an accession.

    Transformation specs name variables unversioned (``phv00202843``) while dbGaP versions
    everything (``phv00202843.v2``, ``pht004027.v3``), so joining the two needs the stem.

    >>> _bare("phv00202843.v2.p2.c1")
    'phv00202843'
    >>> _bare("pht004027.v3")
    'pht004027'
    """
    return accession.split(".", 1)[0]


def _text(element: "etree._Element | None") -> str | None:
    """Return an element's stripped text, or None when absent or empty."""
    if element is None:
        return None
    return (element.text or "").strip() or None


@dataclass(frozen=True)
class CodedValue:
    """
    One ``<value>`` element: an encoded value and what it means.

    ``code`` is None for a bare ``<value>1986</value>`` — dbGaP emits those, and there the
    element text is the value itself rather than a label for one.
    """

    code: str | None
    label: str | None


@dataclass
class DbgapVariable:
    """One ``<variable>``, merged across the data_dict and var_report views of it."""

    accession: str
    versioned_id: str
    name: str | None = None
    description: str | None = None
    reported_type: str | None = None
    unit: str | None = None
    logical_min: str | None = None
    logical_max: str | None = None
    comment: str | None = None
    values: list[CodedValue] = field(default_factory=list)
    calculated_type: str | None = None
    stat_min: str | None = None
    stat_max: str | None = None


@dataclass
class DbgapTable:
    """One pheno table's variables, keyed by bare ``phv`` accession."""

    dataset: str
    versioned_id: str
    study_id: str | None = None
    table_name: str | None = None
    source_file: str = ""
    variables: dict[str, DbgapVariable] = field(default_factory=dict)


def read_data_dict(path: Path) -> DbgapTable:
    """Read a ``*.data_dict.xml`` into a table indexed by bare phv accession."""
    root = _parse(path)
    versioned = root.get("id") or ""
    table = DbgapTable(
        dataset=_bare(versioned),
        versioned_id=versioned,
        study_id=root.get("study_id"),
        source_file=path.name,
    )

    for element in root.findall("variable"):
        variable_id = element.get("id") or ""
        accession = _bare(variable_id)
        if not accession:
            logger.warning("%s has a <variable> with no id; skipping", path.name)
            continue
        table.variables[accession] = DbgapVariable(
            accession=accession,
            versioned_id=variable_id,
            name=_text(element.find("name")),
            description=_text(element.find("description")),
            reported_type=_text(element.find("type")),
            unit=_text(element.find("unit")),
            logical_min=_text(element.find("logical_min")),
            logical_max=_text(element.find("logical_max")),
            comment=_text(element.find("comment")),
            values=[CodedValue(code=value.get("code"), label=_text(value)) for value in element.findall("value")],
        )

    return table


def merge_var_report(table: DbgapTable, path: Path) -> None:
    """
    Fold a ``*.var_report.xml`` into an already-read table, in place.

    Only the total-set row of each variable is read; the per-consent-group rows (``.c<N>``)
    restate the same variable over a subset. Variables the data_dict did not declare are
    ignored — the declared dictionary is the authority on which columns exist.
    """
    root = _parse(path)
    table.table_name = root.get("name") or table.table_name

    for element in root.findall("variable"):
        variable_id = element.get("id") or ""
        if not _TOTAL_SET_RE.search(variable_id):
            continue
        variable = table.variables.get(_bare(variable_id))
        if variable is None:
            logger.debug("%s reports %s, absent from the data dictionary", path.name, variable_id)
            continue

        variable.calculated_type = element.get("calculated_type")
        stat = element.find("total/stats/stat")
        if stat is not None:
            variable.stat_min = stat.get("min")
            variable.stat_max = stat.get("max")


def load_tables(pairs: Iterable[tuple[Path, Path | None]]) -> dict[str, DbgapTable]:
    """
    Read data_dict/var_report pairs into an index keyed by bare ``pht`` accession.

    Keyed on the ``pht`` the XML declares rather than the one in the filename: a cohort's
    listing includes tables contributed by other studies, whose filenames carry a different
    ``phs`` prefix, and those are legitimate content a spec may reference.
    """
    tables: dict[str, DbgapTable] = {}

    # Sort on the data_dict alone: the var_report is None in data_dict-only mode, and a
    # tuple sort would compare Path against None.
    for data_dict_path, var_report_path in sorted(pairs, key=lambda pair: pair[0]):
        table = read_data_dict(data_dict_path)
        if not table.dataset:
            logger.warning("%s has no data_table id; skipping", data_dict_path.name)
            continue
        if table.dataset in tables:
            logger.warning(
                "%s declares %s, already read from %s; keeping the first",
                data_dict_path.name,
                table.dataset,
                tables[table.dataset].source_file,
            )
            continue
        if var_report_path is not None:
            merge_var_report(table, var_report_path)
        tables[table.dataset] = table

    return tables
