"""
Express indexed source variables as BDC variable library instances.

Kept separate from :mod:`dm_bip.variable_lib.extract` because emitting depends on the
schema-automator output that types a variable, while extraction depends only on the
transformation specs. Splitting them keeps the spec-reading half testable on its own.

The deliverable (tis-lab/BDC-Add-On-Tracker#93) takes a transformation spec as its input,
so what an entry carries is what a spec can say: the identity triple that linkml/dm-bip#352
asks to preserve — ``source_id`` (phv), ``file_id`` (pht), ``associated_study`` (phs) — plus
a description of what each variable feeds. Every descriptive slot the BDC classes define
(``variable_name``, ``source_variable_description``, ``minimum_value``, ``maximum_value``,
``resolution``, ``unit``, ``comment``, ``missing_value``, ``coded_values``) corresponds to a
dbGaP data dictionary field, which is a different input and therefore out of scope here.
:class:`MetadataSource` is the seam for supplying them if that scope ever widens.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

import yaml

from dm_bip.variable_lib.classify import Classifier, VariableKind
from dm_bip.variable_lib.datamodel.variable_lib import SingleCategoricalVariable, SingleContinuousVariable
from dm_bip.variable_lib.extract import VariableRecord, VariableUsage

logger = logging.getLogger(__name__)

DBGAP_PREFIX = "dbgap"

_ENTRY_CLASSES = {
    VariableKind.continuous: SingleContinuousVariable,
    VariableKind.categorical: SingleCategoricalVariable,
}


class MetadataSource(Protocol):
    """
    Supplies data-dictionary slots for a variable.

    The seam between emitting identity only and emitting fully-populated entries: adding
    dbGaP data dictionaries later means writing one implementation of this, not
    restructuring the module. Implementations return ``{}`` for variables they do not know.
    """

    def lookup(self, dataset: str, accession: str) -> dict[str, Any]:
        """Return variable library slot values for a variable, or an empty mapping."""
        ...


@dataclass
class VariableEntries:
    """
    The result of an emit pass, grouped by the class each entry took.

    Grouping is what makes the output self-describing: in a first pass the descriptive
    slots are empty, so a continuous and a categorical entry are otherwise identical on
    the page and a flat list would not say which class it meant.
    """

    continuous: list[SingleContinuousVariable] = field(default_factory=list)
    categorical: list[SingleCategoricalVariable] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)

    def __len__(self) -> int:
        """Return the number of emitted entries, not counting unclassified variables."""
        return len(self.continuous) + len(self.categorical)


def describe(usages: list[VariableUsage]) -> str:
    """
    Render a human-readable account of every target slot a variable feeds.

    >>> describe([VariableUsage("Demography", "sex", False, "spec"),
    ...           VariableUsage("Demography", "id", True, "spec")])
    'Source for Demography.sex; Demography.id (via expression)'
    """
    parts = [f"{u.target_class}.{u.slot}{' (via expression)' if u.via_expression else ''}" for u in usages]
    return f"Source for {'; '.join(parts)}"


def _entry_fields(record: VariableRecord, metadata: MetadataSource | None) -> dict[str, Any]:
    """Assemble the slot values for one entry, identity first, then any supplied metadata."""
    dataset = record.sole_dataset()
    fields: dict[str, Any] = {
        "id": f"{DBGAP_PREFIX}:{record.accession}",
        "source_id": record.accession,
        "file_id": dataset,
        "associated_study": record.study_id,
        "variable_description": describe(record.usages),
    }
    if metadata is not None:
        fields.update(metadata.lookup(dataset, record.accession))
    return fields


def to_entries(
    records: dict[str, VariableRecord],
    classify: Classifier,
    metadata: MetadataSource | None = None,
) -> VariableEntries:
    """
    Express variable records as BDC variable library instances.

    Variables the classifier cannot type are collected in ``unclassified`` rather than
    emitted: the two single-variable classes are where ``source_id`` and ``file_id`` are
    defined, so there is no correctly-typed place to put an unclassified variable's
    identity, and defaulting to either class would assert something unproven about the
    data. Their accessions are returned so callers can report the count.
    """
    entries = VariableEntries()
    for accession, record in sorted(records.items()):
        kind = classify(record.sole_dataset(), accession)
        entry_class = _ENTRY_CLASSES.get(kind)
        if entry_class is None:
            entries.unclassified.append(accession)
            continue
        fields = _entry_fields(record, metadata)
        known = {name: value for name, value in fields.items() if name in entry_class.model_fields}
        for name in sorted(set(fields) - set(known)):
            logger.warning("%s has no slot %s on %s; dropping it", accession, name, entry_class.__name__)
        entry = entry_class(**known)
        if kind is VariableKind.continuous:
            entries.continuous.append(entry)
        else:
            entries.categorical.append(entry)

    if entries.unclassified:
        logger.warning(
            "%d of %d variables could not be typed and were not emitted", len(entries.unclassified), len(records)
        )
    return entries


def to_yaml(entries: VariableEntries) -> str:
    """
    Serialize entries as a mapping of class name to instance list.

    Unset slots are omitted rather than written as nulls, and both groups are always
    present even when empty — an absent key would read as "this run found none" only if
    you already knew the key was meant to be there.
    """
    return yaml.safe_dump(
        {
            "single_continuous_variables": [e.model_dump(mode="json", exclude_none=True) for e in entries.continuous],
            "single_categorical_variables": [e.model_dump(mode="json", exclude_none=True) for e in entries.categorical],
        },
        sort_keys=False,
    )
