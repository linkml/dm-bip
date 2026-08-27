"""
Fill variable library descriptive slots from dbGaP data dictionaries.

Implements the ``MetadataSource`` protocol that ``variable_lib.emit`` defines but nothing has
ever satisfied in production: without one, every entry carries identity (``id``, ``source_id``,
``file_id``, ``associated_study``, ``variable_description``) and eleven nulls.

This is the only layer that knows BDC slot names — ``variable_lib.dbgap`` reads XML and knows
nothing about the target classes, and ``emit`` is unchanged.

**Why this takes a classifier.** ``to_entries`` picks the entry class by calling ``classify``,
then calls ``lookup``, which is not told what it chose. The two single-variable classes are not
interchangeable: only the continuous one has ``minimum_value``, ``maximum_value`` and ``unit``,
and only the categorical one has ``coded_values``. Returning the union and letting ``emit``'s
``model_fields`` filter drop the mismatches would work, but it would warn once per dropped key
per variable — thousands of lines on a real study. Asking the same classifier the same question
returns exactly the right slot set instead.
"""

import logging
from typing import Any

from dm_bip.prepare_study.fetch_digests import CohortDigests, pht_from_filename
from dm_bip.trans_spec_gen.units import UNIT_NORMALIZATION
from dm_bip.variable_lib.classify import Classifier, VariableKind
from dm_bip.variable_lib.datamodel.variable_lib import DataTypeEnum, EnumValue, MissingValue
from dm_bip.variable_lib.dbgap import DbgapTable, DbgapVariable, load_tables

logger = logging.getLogger(__name__)

# var_report's calculated_type is a small closed vocabulary; observed across every ARIC
# report it is exactly integer, decimal, enum_integer, string.
_CALCULATED_DATA_TYPES = {
    "integer": DataTypeEnum.integer,
    "decimal": DataTypeEnum.decimal,
    "float": DataTypeEnum.decimal,
    "double": DataTypeEnum.decimal,
    "enum_integer": DataTypeEnum.enum,
    "enum_string": DataTypeEnum.enum,
    "string": DataTypeEnum.string,
    "boolean": DataTypeEnum.boolean,
}

# The data_dict's declared <type> is free text and spelled inconsistently across studies, so
# it is matched by substring. DataTypeEnum's `numeric` and `code` members exist for exactly
# this case — both are documented in the BDC schema as coming from dbGaP data types.
_REPORTED_NUMERIC = ("integer", "decimal", "numeric", "continuous", "float", "real")
_REPORTED_STRING = ("string", "text", "char")


def _ucum(unit: str | None) -> str | None:
    """
    Normalize a dbGaP unit to UCUM, passing unrecognized units through unchanged.

    Deliberately not ``units.normalize_unit``: its miss path returns the lookup key, which is
    already lowercased and space-stripped, so an unmapped unit comes back mangled (``SI`` ->
    ``si``). Emitting the study's own spelling is more informative than emitting a corruption
    of it, even though the BDC slot asks for UCUM.
    """
    if not unit:
        return None
    normalized = UNIT_NORMALIZATION.get(unit.lower().replace(" ", ""))
    if normalized is None:
        return unit
    return None if normalized == "none" else normalized


def _data_type(variable: DbgapVariable) -> DataTypeEnum | None:
    """Map a dbGaP type onto the BDC data type enum, preferring the calculated one."""
    if variable.calculated_type:
        mapped = _CALCULATED_DATA_TYPES.get(variable.calculated_type.strip().lower())
        if mapped is not None:
            return mapped
        logger.warning("Unrecognized dbGaP calculated_type %r on %s", variable.calculated_type, variable.accession)

    declared = (variable.reported_type or "").strip().lower()
    if not declared:
        return None
    if "encoded" in declared or "enum" in declared:
        return DataTypeEnum.code
    if any(word in declared for word in _REPORTED_NUMERIC):
        return DataTypeEnum.numeric
    if any(word in declared for word in _REPORTED_STRING):
        return DataTypeEnum.string
    return None


def _common_slots(variable: DbgapVariable, table: DbgapTable) -> dict[str, Any]:
    """Slots both single-variable classes accept."""
    return {
        "variable_name": variable.name,
        "source_variable_description": variable.description,
        "file_name": table.table_name,
        "data_type": _data_type(variable),
        "comment": variable.comment,
    }


def _continuous_slots(variable: DbgapVariable) -> dict[str, Any]:
    """
    Slots only ``SingleContinuousVariable`` accepts.

    Coded values on a numeric variable are sentinels — a missingness marker or an
    out-of-band note, not the variable's domain — so they become ``missing_value`` rather
    than being dropped. ``MissingValue`` carries exactly the code and label dbGaP publishes.

    ``resolution`` and ``alert_values`` stay unset: dbGaP states neither, and deriving them
    would be inference rather than a fact read off the dictionary.
    """
    return {
        "minimum_value": variable.stat_min or variable.logical_min,
        "maximum_value": variable.stat_max or variable.logical_max,
        "unit": _ucum(variable.unit),
        "missing_value": [
            MissingValue(indicator_char=value.code, indicator_meaning=value.label) for value in variable.values
        ]
        or None,
    }


def _categorical_slots(variable: DbgapVariable) -> dict[str, Any]:
    """
    Slots only ``SingleCategoricalVariable`` accepts.

    Document order is preserved: dbGaP orders values meaningfully (Yes/No, severity scales),
    and the order of an input file is stable, so sorting would lose information and gain no
    determinism. A bare ``<value>1986</value>`` has no code, and there the element text is
    the value itself, so it becomes the indicator character.
    """
    coded = [
        EnumValue(indicator_char=value.code, indicator_meaning=value.label)
        if value.code is not None
        else EnumValue(indicator_char=value.label)
        for value in variable.values
    ]
    return {"coded_values": coded or None}


class DbgapMetadata:
    """A ``MetadataSource`` backed by an index of dbGaP tables."""

    def __init__(self, tables: dict[str, DbgapTable], classify: Classifier) -> None:
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
        variable = table.variables.get(accession)
        if variable is None:
            logger.debug("%s does not declare %s", table.source_file, accession)
            return {}

        fields = _common_slots(variable, table)
        kind = self._classify(dataset, accession)
        if kind is VariableKind.continuous:
            fields.update(_continuous_slots(variable))
        elif kind is VariableKind.categorical:
            fields.update(_categorical_slots(variable))

        return {key: value for key, value in fields.items() if value is not None}


def metadata_for(digests: CohortDigests, classify: Classifier, *, with_var_report: bool = True) -> DbgapMetadata:
    """
    Build a metadata source from fetched digest files.

    Pairs each data_dict with the var_report for the same ``pht``. Unpaired data_dicts are
    kept — dbGaP publishes some tables without a report, and a declared dictionary alone
    still fills most slots.
    """
    reports = {}
    if with_var_report:
        for path in digests.var_reports:
            pht = pht_from_filename(path.name)
            if pht is not None:
                reports[pht] = path

    pairs = [(path, reports.get(pht_from_filename(path.name) or "")) for path in digests.data_dicts]
    return DbgapMetadata(load_tables(pairs), classify)
