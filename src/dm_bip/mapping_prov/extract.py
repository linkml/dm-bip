"""
Extract mapping provenance from linkml-map transformation specs.

A transformation spec (as produced for the DMC pipeline) is a YAML document containing a
list of ``class_derivations`` fragments. Each fragment derives a target class from a dbGaP
dataset (a ``pht`` accession, given by a class-level ``populated_from``) and populates its
slots from dbGaP variables (``phv`` accessions, given by slot-level ``populated_from``
values or referenced as ``{phv...}`` inside ``expr`` strings). Fragments are loaded
through linkml-map's own datamodel
(``TransformationSpecification``), which normalizes the compact key-as-name YAML syntax the
specs are written in. A file is a *list* of fragments rather than a single specification
because ``class_derivations`` is keyed by class name, and one file may derive the same
class from several datasets.

This module walks those specs and expresses what it finds as study-rooted documents in the
mapping-provenance schema (see ``schema/mapping_prov_schema.yaml``). Following
prov-schema#10, everything is a generic ``Entity`` typed by a controlled vocabulary
(``entity_type``): each spec directory's ``researchstudy.yaml`` identifies the study;
datasets sit in the study's ``has_part`` and variables in their dataset's, so
study/dataset/variable alignment is carried by structure; and each derivation fragment
becomes an ``Entity`` that is ``derived_from`` its source dataset, source variables, and
the spec itself.
"""

import ast
import logging
import os
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import git
from linkml_map.datamodel.transformer_model import ClassDerivation
from linkml_map.transformer.object_transformer import ObjectTransformer
from linkml_map.utils.expression_locations import iter_expressions
from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.loaders import yaml_loader

from dm_bip.mapping_prov.datamodel.prov import Activity, Agent, Entity, EntityTypeEnum, TransformationSpec
from dm_bip.provenance import _get_package_versions, get_build_info

logger = logging.getLogger(__name__)

DBGAP_PREFIX = "dbgap"
DMCPROV_PREFIX = "dmcprov"
STUDY_ID_PREFIX = "bdchm:Study/"
RESEARCHSTUDY_FILENAME = "researchstudy.yaml"

_PHV_PATTERN = re.compile(r"phv\d+")


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
    expr_variables: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class _RepoInfo:
    """A spec directory's git context: the repository, its GitHub base URL, and HEAD commit."""

    repo: git.Repo
    url_base: str
    commit: str


_repo_info_cache: dict[Path, "_RepoInfo | None"] = {}


def _github_base(remote: str) -> str | None:
    """Return the https://github.com/owner/repo base for a git remote URL, or None."""
    match = re.fullmatch(r"(?:git@github\.com:|https://github\.com/)([^/]+/[^/]+?)(?:\.git)?/?", remote)
    return f"https://github.com/{match.group(1)}" if match else None


def _repo_info(directory: Path) -> _RepoInfo | None:
    """Return (and cache) the git context for a spec directory, or None if unavailable."""
    if directory not in _repo_info_cache:
        try:
            repo = git.Repo(directory, search_parent_directories=True)
            remote_url = next((remote.url for remote in repo.remotes if remote.name == "origin"), None)
            url_base = _github_base(remote_url) if remote_url else None
            info = _RepoInfo(repo=repo, url_base=url_base, commit=repo.head.commit.hexsha) if url_base else None
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
            info = None
        if info is None:
            logger.info("No usable git context for %s; spec ids fall back to local paths", directory)
        _repo_info_cache[directory] = info
    return _repo_info_cache[directory]


def spec_url(spec_path: Path) -> tuple[str, str] | None:
    """
    Return a commit-pinned GitHub URL identifying a spec file, with its repo-relative path.

    The URL is built from the enclosing checkout's origin remote, HEAD commit, and the
    file's path within the repository — an immutable permalink naming the spec exactly as
    it was read. Returns None (caller falls back to a local path id) when the file is not
    in a git repository with a GitHub remote, or when it is untracked or locally modified —
    a commit URL would misrepresent the content actually extracted.
    """
    info = _repo_info(spec_path.parent)
    if info is None or info.repo.working_tree_dir is None:
        return None
    relpath = spec_path.resolve().relative_to(Path(info.repo.working_tree_dir).resolve())
    if info.repo.is_dirty(path=str(relpath), untracked_files=True):
        logger.warning("%s is untracked or locally modified; using local path id instead of a commit URL", spec_path)
        return None
    return f"{info.url_base}/blob/{info.commit}/{relpath}", str(relpath)


def _braced_names(expression: str) -> list[str]:
    """
    Return the bare names referenced as ``{name}`` in a LinkML expression.

    linkml-map parses a braced reference as a single-element set display (see
    ``eval_utils._eval_set``); its ``extract_braced_reference_roots`` helper covers only
    the dotted ``{Table.col}`` form, so the bare ``{col}`` form the DMC specs use is
    collected here with the same parse. Unparsable expressions are skipped with a
    warning, since specs are external input.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        logger.warning("Could not parse expression %r; skipping its references", expression)
        return []
    return sorted(
        {
            node.elts[0].id
            for node in ast.walk(tree)
            if isinstance(node, ast.Set) and len(node.elts) == 1 and isinstance(node.elts[0], ast.Name)
        }
    )


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
        expr_variables = [
            (sd.name, name)
            for sd in slot_derivations
            for expression in iter_expressions(sd)
            for name in _braced_names(expression)
            if _PHV_PATTERN.fullmatch(name)
        ]
        dataset = derivation.populated_from
        yield DerivationSources(
            target_class=str(derivation.name),
            dataset=None if dataset is None else str(dataset),
            variables=variables,
            expr_variables=expr_variables,
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


def collect_spec_paths(paths: list[Path]) -> list[Path]:
    """Expand any directories in ``paths`` into the transformation spec files they contain."""
    spec_paths = []
    for path in paths:
        if path.is_dir():
            spec_paths.extend(sorted(path.rglob("*.yaml")))
        else:
            spec_paths.append(path)
    return spec_paths


def default_base_dir(paths: list[Path]) -> Path:
    """
    Return the deepest common directory of the given spec files or directories.

    Spec identifiers are derived from paths relative to this directory.

    >>> default_base_dir([Path("/a/b/x.yaml"), Path("/a/c/y.yaml")])
    PosixPath('/a')
    """
    candidates = [path if path.is_dir() else path.parent for path in paths]
    return Path(os.path.commonpath([str(c) for c in candidates]))


def read_study(directory: Path) -> Entity | None:
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
                return Entity(
                    id=f"{STUDY_ID_PREFIX}{accession}",
                    entity_type=EntityTypeEnum.study,
                    name=constant("name"),
                    description=constant("description"),
                )
    return None


def _placeholder_study(directory: Path) -> Entity:
    """Return a placeholder study for a spec directory with no usable researchstudy.yaml."""
    logger.warning(
        "No %s with an accession number in %s; using placeholder study id",
        RESEARCHSTUDY_FILENAME,
        directory,
    )
    return Entity(id=f"{DMCPROV_PREFIX}:{directory.name}", entity_type=EntityTypeEnum.study, name=directory.name)


def extract_provenance(spec_paths: list[Path], base_dir: Path | None = None, resolve_urls: bool = True) -> list[Entity]:
    """
    Extract mapping provenance from transformation spec files as study documents.

    Specs are identified by commit-pinned GitHub URLs derived from their enclosing git
    checkout (see :func:`spec_url`), falling back to ``dmcprov:`` local-path ids; pass
    ``resolve_urls=False`` to skip URL derivation and always use path ids.

    Spec files are grouped by parent directory; each directory's ``researchstudy.yaml``
    provides the study identity (falling back to a placeholder named after the directory).
    Following prov-schema#10, everything is a generic ``Entity`` typed by the
    ``entity_type`` vocabulary, with containment expressed by ``has_part``: each study
    contains its datasets (every dbGaP accession found in a ``populated_from`` or
    referenced as ``{phv...}`` in an expression), each dataset its variables, and the
    study also contains its transformation specs and derived entities. Each derivation
    fragment becomes a derived ``Entity`` linking dataset, variables, and spec via
    ``derived_from``. Fragments deriving the same class from the same dataset merge
    their sources into one derived entity. Variables with no enclosing dataset are
    skipped with a warning.
    """
    if base_dir is None:
        base_dir = default_base_dir(spec_paths)

    studies = []
    for directory in sorted({path.parent for path in spec_paths}):
        study = read_study(directory) or _placeholder_study(directory)
        datasets: dict[str, Entity] = {}
        specs: dict[str, TransformationSpec] = {}
        derived: dict[str, Entity] = {}

        for spec_path in sorted(path for path in spec_paths if path.parent == directory):
            relpath = spec_path.relative_to(base_dir) if spec_path.is_relative_to(base_dir) else Path(spec_path.name)
            url_ref = spec_url(spec_path) if resolve_urls else None
            spec_id, spec_name = url_ref if url_ref else (f"{DMCPROV_PREFIX}:{relpath}", str(relpath))
            specs.setdefault(
                spec_id,
                TransformationSpec(id=spec_id, name=spec_name, entity_type=EntityTypeEnum.transformation_spec),
            )
            spec = yaml_loader.load_as_dict(str(spec_path))

            for block in iter_spec_blocks(spec):
                top = block[0]
                derived_from: list[str] = []

                for derivation in block:
                    if derivation.dataset is not None:
                        dataset_id = f"{DBGAP_PREFIX}:{derivation.dataset}"
                        datasets.setdefault(
                            dataset_id,
                            Entity(
                                id=dataset_id,
                                entity_type=EntityTypeEnum.dataset,
                                name=derivation.dataset,
                                has_part=[],
                            ),
                        )
                        if dataset_id not in derived_from:
                            derived_from.append(dataset_id)
                    dataset_acc = derivation.dataset or top.dataset
                    sources = [(slot, accession, "") for slot, accession in derivation.variables] + [
                        (slot, accession, " (via expression)") for slot, accession in derivation.expr_variables
                    ]
                    for slot_name, accession, via in sources:
                        if dataset_acc is None:
                            logger.warning("Variable %s in %s has no enclosing dataset; skipping", accession, relpath)
                            continue
                        variable_id = f"{DBGAP_PREFIX}:{accession}"
                        dataset = datasets[f"{DBGAP_PREFIX}:{dataset_acc}"]
                        if all(v.id != variable_id for v in dataset.has_part):
                            dataset.has_part.append(
                                Entity(
                                    id=variable_id,
                                    entity_type=EntityTypeEnum.variable,
                                    name=accession,
                                    description=f"Source for {derivation.target_class}.{slot_name}{via}",
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
            dataset.has_part.sort(key=lambda v: str(v.id))
        study.has_part = (
            sorted(datasets.values(), key=lambda d: str(d.id))
            + sorted(specs.values(), key=lambda s: str(s.id))
            + sorted(derived.values(), key=lambda e: str(e.id))
        )
        studies.append(study)

    return studies


def run_activity(studies: list[Entity], started_at: datetime, ended_at: datetime) -> Activity:
    """
    Return an Activity documenting this extraction run.

    The execution-provenance layer: when extraction ran, the agent that performed it
    (dm-bip and the versions of its key dependencies, via the same machinery as
    ``dm_bip.provenance``), and which transformation specs it read (``has_input``,
    referencing the spec entities described within the study documents).
    """
    spec_ids = sorted(
        str(part.id)
        for study in studies
        for part in study.has_part or []
        if part.entity_type == EntityTypeEnum.transformation_spec
    )
    build = get_build_info()
    versions = ", ".join(f"{name} {version}" for name, version in _get_package_versions().items())
    return Activity(
        id=f"{DMCPROV_PREFIX}:run/{uuid.uuid4()}",
        name="dm-bip extract-mapping-provenance",
        started_at_time=started_at,
        ended_at_time=ended_at,
        associated_with=Agent(
            id="https://github.com/linkml/dm-bip",
            name=f"dm-bip {build['version']}",
            description=versions,
        ),
        has_input=spec_ids,
    )


def to_yaml(records: list[Activity | Entity]) -> str:
    """Serialize provenance records (a run activity and/or study documents) as a YAML list."""
    return yaml_dumper.dumps([record.model_dump(mode="json") for record in records])
