"""
Decide whether a source variable is continuous or categorical.

The BDC variable library splits single variables into ``SingleContinuousVariable`` and
``SingleCategoricalVariable``, so an entry cannot be emitted without this determination.
The signal lives in the schema-automator output, not in the transformation specs: that
schema names classes by ``pht`` accession and slots by ``phv`` accession, so the
``(dataset, accession)`` pair from a spec is a direct lookup rather than a name match.

Note that this makes the source schema a *second* input, which the deliverable
(tis-lab/BDC-Add-On-Tracker#93) does not name — it says a transformation spec goes in.
The two single-variable classes are the typed ones, though, and a spec does not say which
a variable is, so the signal has to come from somewhere. Worth confirming.

**Provisional rule.** This module reads the *declared* range only: numeric ranges are
continuous, everything else is categorical. It deliberately does not apply a
``num_distinct_values`` threshold, even though schema-automator annotates every slot with
one, because a threshold is a judgement about what counts as categorical rather than a
fact read off the schema — an integer-ranged participant identifier is the standing
counter-example, numeric by type and a label by meaning. Until that judgement is settled,
a variable classified here is classified by its declared type and nothing else.
"""

import logging
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from linkml_runtime import SchemaView
from linkml_runtime.linkml_model.meta import TypeDefinition

logger = logging.getLogger(__name__)

# Base LinkML types whose values are quantities rather than labels.
CONTINUOUS_BASE_TYPES = frozenset({"integer", "float", "double", "decimal"})


class VariableKind(str, Enum):
    """Which variable library class an entry should take."""

    continuous = "continuous"
    categorical = "categorical"
    unknown = "unknown"


#: Resolves a (dataset, accession) pair to the class its entry should take.
Classifier = Callable[[str, str], VariableKind]


def always_unknown(dataset: str, accession: str) -> VariableKind:
    """Classify nothing. The default when no source schema is available."""
    return VariableKind.unknown


def _base_type(view: SchemaView, range_name: str) -> str:
    """
    Resolve a range to its underlying LinkML base type.

    schema-automator mints named types for recognized identifier patterns (``OMOP
    identifier``, ``MONDO identifier``), each declared ``typeof: string``, so a range name
    has to be followed to its base before it can be judged numeric.
    """
    seen: set[str] = set()
    current = range_name
    while current not in seen:
        seen.add(current)
        definition = view.get_type(current)
        if not isinstance(definition, TypeDefinition) or definition.typeof is None:
            break
        current = str(definition.typeof)
    return current


def classify_from_source_schema(view: SchemaView, dataset: str, accession: str) -> VariableKind:
    """
    Classify a variable from the schema-automator-generated source schema.

    Looks up slot ``accession`` on class ``dataset``. Returns ``unknown`` when the schema
    does not describe that pair — a variable named in a transformation spec but absent from
    the generated schema is a real condition (a spec referencing a column the ingest did not
    produce), and it should surface as unclassified rather than be guessed at.
    """
    # get_class returns None for an absent class, and induced_class would then fail on it.
    if view.get_class(dataset) is None:
        logger.debug("Source schema has no class %s", dataset)
        return VariableKind.unknown

    slot = view.induced_class(dataset).attributes.get(accession)
    if slot is None or slot.range is None:
        logger.debug("Source schema has no slot %s on %s", accession, dataset)
        return VariableKind.unknown

    base = _base_type(view, str(slot.range))
    return VariableKind.continuous if base in CONTINUOUS_BASE_TYPES else VariableKind.categorical


def classifier_for(source_schema: Path | None) -> Classifier:
    """Return a classifier backed by the given source schema, or one that classifies nothing."""
    if source_schema is None:
        logger.warning("No source schema supplied; variables cannot be typed and will be skipped")
        return always_unknown
    view = SchemaView(str(source_schema))
    return lambda dataset, accession: classify_from_source_schema(view, dataset, accession)
