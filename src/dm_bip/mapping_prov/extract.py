"""
Extract mapping provenance from linkml-map transformation specs.

A transformation spec (as produced for the DMC pipeline) is a YAML document containing a
list of ``class_derivations`` fragments. Each fragment derives a target class from a dbGaP
dataset (a ``pht`` accession, given by a class-level ``populated_from``) and populates its
slots from dbGaP variables (``phv`` accessions, given by slot-level ``populated_from``
values). Fragments are loaded through linkml-map's own datamodel
(``TransformationSpecification``), which normalizes the compact key-as-name YAML syntax the
specs are written in. A file is a *list* of fragments rather than a single specification
because ``class_derivations`` is keyed by class name, and one file may derive the same
class from several datasets.

This module walks those specs and expresses what it finds as study-rooted documents in the
mapping-provenance schema (see ``schema/mapping_prov_schema.yaml``): each spec directory's
``researchstudy.yaml`` identifies the study; datasets nest under the study and variables
nest under their dataset, so study/dataset/variable alignment is carried by structure; and
each derivation fragment becomes an ``Entity`` that is ``derived_from`` its source dataset,
source variables, and the spec itself.
"""

import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linkml_map.datamodel.transformer_model import ClassDerivation
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.loaders import yaml_loader

from dm_bip.mapping_prov.datamodel.prov import Dataset, Entity, Study, TransformationSpec, Variable

logger = logging.getLogger(__name__)

DBGAP_PREFIX = "dbgap"
DMCPROV_PREFIX = "dmcprov"
STUDY_ID_PREFIX = "bdchm:Study/"
RESEARCHSTUDY_FILENAME = "researchstudy.yaml"


@dataclass
class DerivationSources:
    """
    The provenance-relevant parts of a single class derivation.

    Captures the target class, the source dataset (class-level ``populated_from``), and the
    source variables (slot-level ``populated_from`` values) as (slot name, accession) pairs.
    """

    target_class: str
    dataset: str | None
    variables: list[tuple[str, str]] = field(default_factory=list)


def _as_derivation_list(class_derivations: Any) -> list[ClassDerivation]:
    """Return class derivations as a list, whether given as a dict keyed by class name or a list."""
    if isinstance(class_derivations, dict):
        return list(class_derivations.values())
    return list(class_derivations or [])


def _walk_derivations(class_derivations: list[ClassDerivation]) -> Iterator[DerivationSources]:
    """Yield the sources of each class derivation, recursing into derivations nested inside slot derivations."""
    for derivation in class_derivations:
        slot_derivations = (derivation.slot_derivations or {}).values()
        variables = [(sd.name, str(sd.populated_from)) for sd in slot_derivations if sd.populated_from is not None]
        dataset = derivation.populated_from
        yield DerivationSources(
            target_class=str(derivation.name),
            dataset=None if dataset is None else str(dataset),
            variables=variables,
        )
        for sd in slot_derivations:
            if sd.class_derivations:
                yield from _walk_derivations(_as_derivation_list(sd.class_derivations))


def iter_spec_blocks(spec: Any) -> Iterator[list[DerivationSources]]:
    """
    Yield the class derivations of each fragment of a spec document.

    Each fragment is loaded into linkml-map's ``TransformationSpecification`` datamodel. The
    yielded list contains the sources of that fragment's derivations, outermost first, with
    nested derivations (from slot-level ``class_derivations``) following their parent.

    >>> spec = [{"class_derivations": {"Obs": {
    ...     "populated_from": "pht1",
    ...     "slot_derivations": {
    ...         "quantity": {"class_derivations": [{"Quantity": {
    ...             "populated_from": "pht1",
    ...             "slot_derivations": {"value": {"populated_from": "phv2"}},
    ...         }}]},
    ...     },
    ... }}}]
    >>> [[d.target_class for d in block] for block in iter_spec_blocks(spec)]
    [['Obs', 'Quantity']]
    """
    fragments = spec if isinstance(spec, list) else [spec]
    for fragment in fragments:
        if not isinstance(fragment, dict) or "class_derivations" not in fragment:
            continue
        transformer = ObjectTransformer()
        transformer.create_transformer_specification(fragment)
        derivations = list(_walk_derivations(_as_derivation_list(transformer.specification.class_derivations)))
        if derivations:
            yield derivations


def iter_class_derivations(spec: Any) -> Iterator[DerivationSources]:
    """
    Yield the sources of every class derivation in a spec document.

    >>> spec = [{"class_derivations": {"Obs": {
    ...     "populated_from": "pht1",
    ...     "slot_derivations": {"height": {"populated_from": "phv1"}},
    ... }}}]
    >>> [d] = iter_class_derivations(spec)
    >>> d.target_class, d.dataset, d.variables
    ('Obs', 'pht1', [('height', 'phv1')])
    """
    for block in iter_spec_blocks(spec):
        yield from block


def default_base_dir(paths: list[Path]) -> Path:
    """
    Return the deepest common directory of the given spec files or directories.

    Spec identifiers are derived from paths relative to this directory.

    >>> default_base_dir([Path("/a/b/x.yaml"), Path("/a/c/y.yaml")])
    PosixPath('/a')
    """
    candidates = [path if path.is_dir() else path.parent for path in paths]
    return Path(os.path.commonpath([str(c) for c in candidates]))


def read_study(directory: Path) -> Study | None:
    """
    Read study identity from a directory's researchstudy.yaml, if present.

    The file is itself a transformation spec; the study's accession (a dbGaP ``phs``
    number), name, and description are taken from constant-valued slot derivations
    (``accession_number``, ``name``, ``description``). Returns None when the file is absent
    or carries no accession number.
    """
    path = directory / RESEARCHSTUDY_FILENAME
    if not path.is_file():
        return None
    doc = yaml_loader.load_as_dict(str(path))
    fragments = doc if isinstance(doc, list) else [doc]
    for fragment in fragments:
        if not isinstance(fragment, dict):
            continue
        for derivation in (fragment.get("class_derivations") or {}).values():
            slot_derivations = derivation.get("slot_derivations") or {}

            def constant(slot: str, slot_derivations: dict = slot_derivations) -> str | None:
                value = slot_derivations.get(slot) or {}
                return value.get("value") if isinstance(value, dict) else None

            accession = constant("accession_number")
            if accession is not None:
                return Study(
                    id=f"{STUDY_ID_PREFIX}{accession}",
                    name=constant("name"),
                    description=constant("description"),
                )
    return None


def _placeholder_study(directory: Path) -> Study:
    """Return a placeholder study for a spec directory with no usable researchstudy.yaml."""
    logger.warning(
        "No %s with an accession number in %s; using placeholder study id",
        RESEARCHSTUDY_FILENAME,
        directory,
    )
    return Study(id=f"{DMCPROV_PREFIX}:{directory.name}", name=directory.name)


def extract_provenance(spec_paths: list[Path], base_dir: Path | None = None) -> list[Study]:
    """
    Extract mapping provenance from transformation spec files as study documents.

    Spec files are grouped by parent directory; each directory's ``researchstudy.yaml``
    provides the study identity (falling back to a placeholder named after the directory).
    Every dbGaP accession found in a ``populated_from`` contributes a ``Dataset`` or
    ``Variable`` nested under the study, each spec file a ``TransformationSpec``, and each
    derivation fragment a derived ``Entity`` linking them all via ``derived_from``.
    Fragments deriving the same class from the same dataset merge their sources into one
    derived entity. Variables with no enclosing dataset are skipped with a warning.
    """
    if base_dir is None:
        base_dir = default_base_dir(spec_paths)

    studies = []
    for directory in sorted({path.parent for path in spec_paths}):
        study = read_study(directory) or _placeholder_study(directory)
        datasets: dict[str, Dataset] = {}
        specs: dict[str, TransformationSpec] = {}
        derived: dict[str, Entity] = {}

        for spec_path in sorted(path for path in spec_paths if path.parent == directory):
            relpath = spec_path.relative_to(base_dir) if spec_path.is_relative_to(base_dir) else Path(spec_path.name)
            spec_id = f"{DMCPROV_PREFIX}:{relpath}"
            specs.setdefault(spec_id, TransformationSpec(id=spec_id, name=str(relpath)))
            spec = yaml_loader.load_as_dict(str(spec_path))

            for block in iter_spec_blocks(spec):
                top = block[0]
                derived_from: list[str] = []

                for derivation in block:
                    if derivation.dataset is not None:
                        dataset_id = f"{DBGAP_PREFIX}:{derivation.dataset}"
                        datasets.setdefault(dataset_id, Dataset(id=dataset_id, name=derivation.dataset, variables=[]))
                        if dataset_id not in derived_from:
                            derived_from.append(dataset_id)
                    dataset_acc = derivation.dataset or top.dataset
                    for slot_name, accession in derivation.variables:
                        if dataset_acc is None:
                            logger.warning("Variable %s in %s has no enclosing dataset; skipping", accession, relpath)
                            continue
                        variable_id = f"{DBGAP_PREFIX}:{accession}"
                        dataset = datasets[f"{DBGAP_PREFIX}:{dataset_acc}"]
                        if all(v.id != variable_id for v in dataset.variables):
                            dataset.variables.append(
                                Variable(
                                    id=variable_id,
                                    name=accession,
                                    description=f"Source for {derivation.target_class}.{slot_name}",
                                )
                            )
                        if variable_id not in derived_from:
                            derived_from.append(variable_id)

                derived_from.append(spec_id)
                entity_id = f"{DMCPROV_PREFIX}:{relpath.with_suffix('')}/{top.target_class}/{top.dataset}"
                if entity_id in derived:
                    existing = derived[entity_id].derived_from
                    existing.extend(ref for ref in derived_from if ref not in existing)
                else:
                    derived[entity_id] = Entity(
                        id=entity_id,
                        name=f"{top.target_class} derived from {top.dataset} ({relpath})",
                        derived_from=derived_from,
                    )

        for dataset in datasets.values():
            dataset.variables.sort(key=lambda v: str(v.id))
        study.datasets = sorted(datasets.values(), key=lambda d: str(d.id))
        study.transformation_specs = sorted(specs.values(), key=lambda s: str(s.id))
        study.derived_entities = sorted(derived.values(), key=lambda e: str(e.id))
        studies.append(study)

    return studies


def to_yaml(studies: list[Study]) -> str:
    """Serialize study documents as a YAML list."""
    return yaml_dumper.dumps([study.model_dump() for study in studies])
