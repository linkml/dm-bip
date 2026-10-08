"""
Decide whether a source variable is continuous or categorical.

The BDC variable library splits single variables into ``SingleContinuousVariable`` and
``SingleCategoricalVariable``, so an entry cannot be emitted without this determination,
and a transformation spec never says which a variable is.

The signal is the canonical data dictionary's ``type``. schema-automator's ``adapt-dbgap``
resolves it from dbGaP's own declared and calculated types, and ``schema-create`` reads the
same DD, so the decision about what a variable *is* is made once, upstream. This module only
maps that vocabulary onto the two classes: ``integer`` and ``decimal`` are continuous;
``permissible_values``, ``boolean``, ``string`` and the temporal and identifier types are
categorical. A variable the dictionary does not describe is ``unknown``, and ``emit`` holds
it back rather than defaulting it.

One known limit comes from upstream. The adapter currently types any variable carrying
codes as ``permissible_values``, so a numeric variable with sentinel codes (an age with
``-9`` for missing) is categorical here until linkml/schema-automator#231 teaches the adapter
to check ``calculated_type`` first. That fix reaches here with no change to this module.
"""

import logging
from collections.abc import Callable, Mapping
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # dbgap_metadata imports this module, so only the type checker follows the edge
    from dm_bip.variable_lib.dbgap_metadata import DdTable

logger = logging.getLogger(__name__)

#: Canonical DD types whose values are quantities. Everything else the adapter writes,
#: ``permissible_values``, ``boolean``, ``string``, ``date``, ``datetime``, ``time``,
#: ``uri`` and ``curie``, is a label.
DD_CONTINUOUS_TYPES = frozenset({"integer", "decimal"})


class VariableKind(str, Enum):
    """Which variable library class an entry should take."""

    continuous = "continuous"
    categorical = "categorical"
    unknown = "unknown"


#: Resolves a (dataset, accession) pair to the class its entry should take.
Classifier = Callable[[str, str], VariableKind]


def always_unknown(dataset: str, accession: str) -> VariableKind:
    """Classify nothing. The default when no data dictionary is available."""
    return VariableKind.unknown


def classify_from_dd(tables: "Mapping[str, DdTable]", dataset: str, accession: str) -> VariableKind:
    """
    Classify a variable from its canonical data dictionary entry.

    The DD ``type`` is the adapter's decision about what the variable is, so this only maps
    that vocabulary onto the two classes. Returns ``unknown`` when the dictionary does not
    describe the pair, or describes it without a type.
    """
    table = tables.get(dataset)
    entry = table.entries.get(accession) if table is not None else None
    if entry is None or entry.data_type is None:
        logger.debug("Data dictionary does not type %s on %s", accession, dataset)
        return VariableKind.unknown
    kind = entry.data_type.strip().lower()
    return VariableKind.continuous if kind in DD_CONTINUOUS_TYPES else VariableKind.categorical


def classifier_for(tables: "Mapping[str, DdTable] | None") -> Classifier:
    """Return a classifier over the given data dictionaries, or one that classifies nothing and says so."""
    if not tables:
        logger.warning("No data dictionary supplied; variables cannot be typed and will be skipped")
        return always_unknown
    return lambda dataset, accession: classify_from_dd(tables, dataset, accession)
