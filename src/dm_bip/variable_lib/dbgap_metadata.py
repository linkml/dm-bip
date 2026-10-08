"""
Fill variable library descriptive slots from canonical data dictionaries.

Implements the ``MetadataSource`` protocol that ``variable_lib.emit`` defines: without one,
every entry carries identity (``id``, ``source_id``, ``file_id``, ``associated_study``,
``variable_description``) and eleven nulls.

The input is the canonical data dictionary (DD) that ``schemauto adapt-dbgap`` produces,
one per dbGaP pheno table: either the TSV the pipeline's ``adapt-digests`` target writes
under ``output/<cohort>/dd/`` (``load_tables``), or the same adapter's output kept in memory
for digests that were just fetched (``tables_from_digests``). Deciding what a dbGaP
variable *is* (its type, bounds, unit, codes) is schema-automator's job; this module only
maps DD columns onto BDC slot names. It is therefore the only layer that knows those names,
and nothing here parses XML itself.

**Columns.** The adapter emits ``name``, ``type``, ``description``, ``codes``, ``unit``,
``min``, ``max`` and ``uri``, and those are required. ``comment`` and ``missing_values``
are read when present and left unset otherwise: they are the columns proposed upstream to
carry dbGaP's ``<comment>`` and the sentinel codes of numeric variables, and a DD written
before they land still fills every other slot.

**Why this takes a classifier.** ``to_entries`` picks the entry class by calling ``classify``,
then calls ``lookup``, which is not told what it chose. The two single-variable classes are
not interchangeable: only the continuous one has ``minimum_value``, ``maximum_value`` and
``unit``, and only the categorical one has ``coded_values``. Asking the same classifier the
same question returns exactly the right slot set, instead of a union that ``emit`` would
have to warn about once per dropped key per variable.
"""

import csv
import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from schema_automator.adapters.codes import parse_codes

from dm_bip.prepare_study.fetch_digests import pht_from_filename
from dm_bip.trans_spec_gen.units import UNIT_NORMALIZATION
from dm_bip.variable_lib.classify import Classifier, VariableKind
from dm_bip.variable_lib.datamodel.variable_lib import DataTypeEnum, EnumValue, MissingValue

logger = logging.getLogger(__name__)

#: The columns ``schemauto adapt-dbgap --tsv`` always writes.
REQUIRED_COLUMNS = frozenset({"name", "type", "description", "codes", "unit", "min", "max", "uri"})
COMMENT_COLUMN = "comment"
MISSING_VALUES_COLUMN = "missing_values"

# The DD spec's explicit "no unit" / "unbounded" token, as distinct from an empty cell.
_DD_NONE = "none"

# The canonical DD type vocabulary onto the BDC data type enum. Temporal and identifier
# types have no BDC counterpart beyond string; `numeric` and `code` exist in the enum for
# dbGaP's free-text declared types, which the adapter has already resolved by this point.
_DD_DATA_TYPES = {
    "integer": DataTypeEnum.integer,
    "decimal": DataTypeEnum.decimal,
    "permissible_values": DataTypeEnum.enum,
    "string": DataTypeEnum.string,
    "boolean": DataTypeEnum.boolean,
    "date": DataTypeEnum.string,
    "datetime": DataTypeEnum.string,
    "time": DataTypeEnum.string,
    "uri": DataTypeEnum.string,
    "curie": DataTypeEnum.string,
}

# `dbgap:phv00000001.v1` -> phv00000001. The adapter writes the versioned id as a CURIE;
# transformation specs name variables unversioned, so the join needs the bare stem.
_URI_ACCESSION_RE = re.compile(r"(?:^|:)(phv\d+)")
# `phs000280.v8.pht000001.v1.DEMO.dd.tsv` -> DEMO. The pipeline names each DD after the
# data_dict it came from, which carries dbGaP's table name after the pht version, so the
# same pattern reads the name off a data_dict adapted in memory.
_TABLE_NAME_RE = re.compile(r"pht\d+\.v\d+\.(?P<name>.+?)\.(?:dd\.tsv|data_dict\.xml)$")


@dataclass(frozen=True)
class Code:
    """One permissible value or sentinel: the literal code and, when the DD gives one, its label."""

    code: str
    label: str | None = None


@dataclass
class DdEntry:
    """One DD row, with the codes columns parsed and the empty-cell / ``none`` distinction kept."""

    accession: str
    name: str | None = None
    data_type: str | None = None
    description: str | None = None
    codes: list[Code] = field(default_factory=list)
    unit: str | None = None
    min: str | None = None
    max: str | None = None
    comment: str | None = None
    missing_values: list[Code] = field(default_factory=list)


@dataclass
class DdTable:
    """One pheno table's DD rows, keyed by bare ``phv`` accession."""

    dataset: str
    source_file: str = ""
    table_name: str | None = None
    entries: dict[str, DdEntry] = field(default_factory=dict)


def _cell(row: dict[str, str], column: str) -> str | None:
    """Return a stripped cell, or None when the column is absent or the cell is empty."""
    value = row.get(column)
    if value is None:
        return None
    return value.strip() or None


def _codes(cell: str | None, accession: str, column: str) -> list[Code]:
    """Parse a codes-grammar cell (``code, label | code | ...``), keeping document order."""
    if cell is None:
        return []
    try:
        parsed = parse_codes(cell)
    except ValueError as exc:
        logger.warning("Unparsable %s on %s (%s); ignoring the column", column, accession, exc)
        return []
    return [Code(code=item["code"], label=item.get("label")) for item in parsed]


def _accession(uri: str | None) -> str | None:
    """Return the bare ``phv`` accession named by a DD ``uri`` cell, or None."""
    if uri is None:
        return None
    match = _URI_ACCESSION_RE.search(uri)
    return match.group(1) if match else None


def table_name_from_filename(filename: str) -> str | None:
    """
    Return dbGaP's table name from a pipeline-named DD file or a dbGaP data_dict, or None.

    >>> table_name_from_filename("phs000280.v8.pht000001.v1.DEMO.dd.tsv")
    'DEMO'
    >>> table_name_from_filename("phs000280.v8.pht000001.v1.DEMO.data_dict.xml")
    'DEMO'
    >>> table_name_from_filename("phs000280.pht000001.dd.tsv") is None
    True
    """
    match = _TABLE_NAME_RE.search(filename)
    return match.group("name") if match else None


def read_dd(path: Path) -> DdTable:
    """
    Read one canonical DD TSV into a table keyed by bare ``phv`` accession.

    The dataset comes from the filename, since DD rows carry a variable URI but no table
    identity. Raises ``ValueError`` when the header lacks a column the adapter always
    writes, so a file that is not a canonical DD fails loudly rather than filling nothing.
    """
    dataset = pht_from_filename(path.name) or ""
    table = DdTable(dataset=dataset, source_file=path.name, table_name=table_name_from_filename(path.name))

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        columns = set(reader.fieldnames or [])
        if missing := REQUIRED_COLUMNS - columns:
            raise ValueError(f"{path.name} is not a canonical DD: missing column(s) {', '.join(sorted(missing))}")

        for row in reader:
            accession = _accession(_cell(row, "uri"))
            if accession is None:
                logger.warning("%s row %r has no dbgap:phv uri; skipping", path.name, _cell(row, "name"))
                continue
            table.entries[accession] = DdEntry(
                accession=accession,
                name=_cell(row, "name"),
                data_type=_cell(row, "type"),
                description=_cell(row, "description"),
                codes=_codes(_cell(row, "codes"), accession, "codes"),
                unit=_cell(row, "unit"),
                min=_cell(row, "min"),
                max=_cell(row, "max"),
                comment=_cell(row, COMMENT_COLUMN),
                missing_values=_codes(_cell(row, MISSING_VALUES_COLUMN), accession, MISSING_VALUES_COLUMN),
            )

    return table


def load_tables(paths: Iterable[Path]) -> dict[str, DdTable]:
    """
    Read DD files into an index keyed by bare ``pht`` accession.

    Files whose names carry no ``pht`` are skipped with a warning, as is a second file for
    a dataset already read: the pipeline writes one DD per pheno table, so a duplicate is a
    stray rather than a choice.
    """
    tables: dict[str, DdTable] = {}
    for path in sorted(paths):
        dataset = pht_from_filename(path.name)
        if dataset is None:
            logger.warning("%s names no pht accession; skipping", path.name)
            continue
        if dataset in tables:
            logger.warning("%s is a second DD for %s; keeping %s", path.name, dataset, tables[dataset].source_file)
            continue
        tables[dataset] = read_dd(path)
    return tables


def _adapter_codes(cell: Any, accession: str, column: str) -> list[Code]:
    """
    Turn the adapter's in-memory codes list into ``Code`` records.

    A value dbGaP publishes with no code attribute (``<value>1986</value>``) arrives as a
    record with only a label. The DD grammar reads such a bareword as the value itself, so
    it is kept as the code with no label, exactly as ``read_dd`` would see it.
    """
    if not cell:
        return []
    if not isinstance(cell, list):
        logger.warning("Unexpected %s on %s (%r); ignoring the column", column, accession, cell)
        return []
    codes = []
    for item in cell:
        code, label = item.get("code"), item.get("label")
        if code in (None, ""):
            code, label = label, None
        if code in (None, ""):
            continue
        codes.append(Code(code=str(code), label=None if label in (None, "") else str(label)))
    return codes


def _adapter_cell(record: dict[str, Any], key: str) -> str | None:
    """Return a scalar from the adapter's record as a stripped string, or None when unset."""
    value = record.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def tables_from_digests(pairs: Iterable[tuple[Path, Path | None]]) -> dict[str, DdTable]:
    """
    Adapt dbGaP digest pairs in memory into an index keyed by bare ``pht`` accession.

    The offline-TSV path (``load_tables``) reads what ``schemauto adapt-dbgap --tsv`` wrote.
    This path calls the same adapter but keeps its canonical DD in memory, so a caller that
    has just fetched digests need not round-trip through files. It also sidesteps the
    adapter's TSV serializer, which currently rejects a bareword value; see
    ``_adapter_codes``. A ``var_report`` of None adapts the data_dict alone.
    """
    from schema_automator.adapters.dbgap import dbgap_to_dd

    tables: dict[str, DdTable] = {}
    for data_dict, var_report in pairs:
        dataset = pht_from_filename(data_dict.name)
        if dataset is None:
            logger.warning("%s names no pht accession; skipping", data_dict.name)
            continue
        if dataset in tables:
            logger.warning(
                "%s is a second data_dict for %s; keeping %s", data_dict.name, dataset, tables[dataset].source_file
            )
            continue
        table = DdTable(
            dataset=dataset, source_file=data_dict.name, table_name=table_name_from_filename(data_dict.name)
        )
        canonical = dbgap_to_dd(str(data_dict), str(var_report) if var_report is not None else None)
        for record in canonical.get("entries", []):
            accession = _accession(_adapter_cell(record, "uri"))
            if accession is None:
                logger.warning("%s entry %r has no dbgap:phv uri; skipping", data_dict.name, record.get("name"))
                continue
            table.entries[accession] = DdEntry(
                accession=accession,
                name=_adapter_cell(record, "name"),
                data_type=_adapter_cell(record, "type"),
                description=_adapter_cell(record, "description"),
                codes=_adapter_codes(record.get("codes"), accession, "codes"),
                unit=_adapter_cell(record, "unit"),
                min=_adapter_cell(record, "min"),
                max=_adapter_cell(record, "max"),
                comment=_adapter_cell(record, COMMENT_COLUMN),
                missing_values=_adapter_codes(record.get(MISSING_VALUES_COLUMN), accession, MISSING_VALUES_COLUMN),
            )
        tables[dataset] = table
    return tables


def _ucum(unit: str | None) -> str | None:
    """
    Normalize a unit to UCUM, passing unrecognized units through unchanged.

    The DD's explicit ``none`` token means a unitless quantity and yields no unit.
    Deliberately not ``units.normalize_unit``: its miss path returns the lookup key, which is
    already lowercased and space-stripped, so an unmapped unit comes back mangled (``SI`` ->
    ``si``). Emitting the study's own spelling is more informative than emitting a corruption
    of it, even though the BDC slot asks for UCUM.
    """
    if not unit or unit.lower() == _DD_NONE:
        return None
    normalized = UNIT_NORMALIZATION.get(unit.lower().replace(" ", ""))
    if normalized is None:
        return unit
    return None if normalized == _DD_NONE else normalized


def _data_type(entry: DdEntry) -> DataTypeEnum | None:
    """Map the DD's canonical type onto the BDC data type enum."""
    if entry.data_type is None:
        return None
    mapped = _DD_DATA_TYPES.get(entry.data_type.strip().lower())
    if mapped is None:
        logger.warning("Unrecognized DD type %r on %s", entry.data_type, entry.accession)
    return mapped


def _bound(value: str | None, entry: DdEntry, slot: str) -> str | None:
    """
    Keep a bound only if it is a decimal, which is all the schema can hold.

    The DD's ``none`` token declares a bound as genuinely absent and is not an error. dbGaP
    top-codes to protect identity, publishing ``max=">89"`` on age variables rather than
    the real maximum; the adapter drops those, but a DD edited by hand may not, and
    ``minimum_value``/``maximum_value`` are ``range: decimal`` upstream. Passing a censored
    bound through fails validation and kills the whole run, and rewriting ">89" as 89 would
    assert a maximum the data does not have. Dropping it loses only the bound, and the
    warning keeps the censoring visible in the run output.
    """
    if value is None or value.lower() == _DD_NONE:
        return None
    try:
        Decimal(value)
    except (InvalidOperation, ValueError):
        logger.warning("Non-decimal %s %r on %s; dropping it", slot, value, entry.accession)
        return None
    return value


def _common_slots(entry: DdEntry, table: DdTable) -> dict[str, Any]:
    """Slots both single-variable classes accept."""
    return {
        "variable_name": entry.name,
        "source_variable_description": entry.description,
        "file_name": table.table_name,
        "data_type": _data_type(entry),
        "comment": entry.comment,
    }


def _continuous_slots(entry: DdEntry) -> dict[str, Any]:
    """
    Slots only ``SingleContinuousVariable`` accepts.

    Codes on a numeric variable are sentinels — a missingness marker or an out-of-band
    note, not the variable's domain — so they become ``missing_value`` rather than being
    dropped. They come from the DD's ``missing_values`` column when it has one. Until the
    adapter writes that column, a numeric variable carrying codes is typed
    ``permissible_values`` upstream with the sentinels in ``codes``, so ``codes`` is the
    fallback: a variable the classifier calls continuous has no other use for them.

    ``resolution`` and ``alert_values`` stay unset: the DD states neither, and deriving them
    would be inference rather than a fact read off the dictionary.
    """
    sentinels = entry.missing_values or entry.codes
    return {
        "minimum_value": _bound(entry.min, entry, "minimum"),
        "maximum_value": _bound(entry.max, entry, "maximum"),
        "unit": _ucum(entry.unit),
        "missing_value": [MissingValue(indicator_char=c.code, indicator_meaning=c.label) for c in sentinels] or None,
    }


def _categorical_slots(entry: DdEntry) -> dict[str, Any]:
    """
    Slots only ``SingleCategoricalVariable`` accepts.

    Document order is preserved: dbGaP orders values meaningfully (Yes/No, severity scales),
    the adapter keeps that order, and the order of an input file is stable, so sorting would
    lose information and gain no determinism. A bareword code (the DD's spelling of dbGaP's
    bare ``<value>1986</value>``) is the value itself and has no label.
    """
    coded = [EnumValue(indicator_char=c.code, indicator_meaning=c.label) for c in entry.codes]
    return {"coded_values": coded or None}


class DbgapMetadata:
    """A ``MetadataSource`` backed by an index of canonical DD tables."""

    def __init__(self, tables: dict[str, DdTable], classify: Classifier) -> None:
        """Index tables by bare ``pht``, and keep the classifier used to route slots."""
        self._tables = tables
        self._classify = classify

    def lookup(self, dataset: str, accession: str) -> dict[str, Any]:
        """
        Return variable library slot values for a variable, or an empty mapping.

        ``associated_study`` is never returned. ``emit`` merges this over the identity fields,
        so returning it would let a table contributed by another study overwrite the study the
        transformation spec actually belongs to.
        """
        table = self._tables.get(dataset)
        if table is None:
            logger.debug("No dbGaP data dictionary for dataset %s", dataset)
            return {}
        entry = table.entries.get(accession)
        if entry is None:
            logger.debug("%s does not declare %s", table.source_file, accession)
            return {}

        fields = _common_slots(entry, table)
        kind = self._classify(dataset, accession)
        if kind is VariableKind.continuous:
            fields.update(_continuous_slots(entry))
        elif kind is VariableKind.categorical:
            fields.update(_categorical_slots(entry))

        return {key: value for key, value in fields.items() if value is not None}


def metadata_for(dd_paths: Iterable[Path], classify: Classifier) -> DbgapMetadata:
    """Build a metadata source from canonical DD files, typically ``output/<cohort>/dd/*.dd.tsv``."""
    return DbgapMetadata(load_tables(dd_paths), classify)


def metadata_from_digests(pairs: Iterable[tuple[Path, Path | None]], classify: Classifier) -> DbgapMetadata:
    """Build a metadata source straight from fetched digest pairs, adapting them in memory."""
    return DbgapMetadata(tables_from_digests(pairs), classify)
