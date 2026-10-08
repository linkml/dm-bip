"""
Index source variables from linkml-map transformation specs.

Where mapping-provenance extraction (``dm_bip.mapping_prov.extract``) is organized around
the *derived* thing — each derivation fragment becoming an entity that records what it was
derived from — a variable library is organized around the *source* thing: the entry is the
dbGaP variable, and it should state every target slot that variable feeds. So this module
reuses that module's spec-reading layer wholesale and re-keys what it yields by ``phv``
accession, accumulating uses rather than keeping the first one seen.

Reading the spec, recursing into nested class derivations, and pulling ``{phv...}``
references out of ``expr`` strings all happen in ``mapping_prov.extract``; nothing here
parses YAML. If a third consumer appears, that shared layer is worth lifting into its own
module rather than being imported sideways.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from linkml_runtime.loaders import yaml_loader

from dm_bip.mapping_prov.extract import (
    DMCPROV_PREFIX,
    RESEARCHSTUDY_FILENAME,
    default_base_dir,
    iter_spec_blocks,
    read_study,
    spec_url,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, order=True)
class VariableUsage:
    """
    One place a source variable feeds a target slot.

    ``via_expression`` distinguishes a slot populated directly (``populated_from: phv...``)
    from one that references the variable inside a LinkML expression — an identifier woven
    into a ``uuid5()`` call is a materially weaker claim about the variable's role than a
    value copied straight across, and a library entry should not flatten the two.
    """

    target_class: str
    slot: str
    via_expression: bool
    spec_id: str


@dataclass
class VariableRecord:
    """
    A source variable and every target slot it feeds.

    ``datasets`` is a set rather than a scalar because nothing in the spec format prevents
    the same accession appearing under two ``pht`` values; see :func:`sole_dataset`.
    """

    accession: str
    datasets: set[str] = field(default_factory=set)
    study_id: str | None = None
    usages: list[VariableUsage] = field(default_factory=list)

    def sole_dataset(self) -> str:
        """
        Return the dataset this variable belongs to.

        The variable library's ``file_id`` is single-valued, so a variable seen under
        several datasets has to collapse to one. That collapse is lossy, so it warns and
        picks deterministically rather than silently taking whichever spec was read first.
        """
        datasets = sorted(self.datasets)
        if len(datasets) > 1:
            logger.warning(
                "Variable %s appears under multiple datasets %s; using %s for file_id",
                self.accession,
                datasets,
                datasets[0],
            )
        return datasets[0]


def _study_id(directory: Path) -> str:
    """
    Return the study identifier for a spec directory.

    Falls back to a placeholder named after the directory, matching mapping-provenance
    behavior. Real ``phs`` accessions require a ``researchstudy.yaml``, which the release
    repos do not currently carry, so ``associated_study`` is a placeholder against them.
    """
    study = read_study(directory)
    if study is not None:
        return str(study.id)
    logger.warning(
        "No %s with an accession number in %s; variables will carry a placeholder study id",
        RESEARCHSTUDY_FILENAME,
        directory,
    )
    return f"{DMCPROV_PREFIX}:{directory.name}"


def collect_variables(
    spec_paths: list[Path],
    base_dir: Path | None = None,
    resolve_urls: bool = True,
) -> dict[str, VariableRecord]:
    """
    Index every source variable in the given specs by ``phv`` accession.

    Walks the same derivation blocks as mapping-provenance extraction, but keyed by source
    variable, so each record accumulates all of its uses. Specs are grouped by parent
    directory so each variable can carry the study identity of the directory it came from.

    Returns records sorted by accession, each with its usages sorted, so that repeated runs
    over unchanged specs produce byte-identical output.
    """
    if base_dir is None:
        base_dir = default_base_dir(spec_paths)

    records: dict[str, VariableRecord] = {}
    for directory in sorted({path.parent for path in spec_paths}):
        study_id = _study_id(directory)

        for spec_path in sorted(path for path in spec_paths if path.parent == directory):
            relpath = spec_path.relative_to(base_dir) if spec_path.is_relative_to(base_dir) else Path(spec_path.name)
            url_ref = spec_url(spec_path) if resolve_urls else None
            spec_id = url_ref[0] if url_ref else f"{DMCPROV_PREFIX}:{relpath}"

            for block in iter_spec_blocks(yaml_loader.load_as_dict(str(spec_path))):
                top = block[0]
                for derivation in block:
                    # Nested derivations may omit populated_from and inherit the enclosing
                    # fragment's dataset; mapping_prov.extract relies on the same fallback.
                    dataset = derivation.dataset or top.dataset
                    sources = [(slot, accession, False) for slot, accession in derivation.variables] + [
                        (slot, accession, True) for slot, accession in derivation.expr_variables
                    ]
                    for slot, accession, via_expression in sources:
                        if dataset is None:
                            logger.warning("Variable %s in %s has no enclosing dataset; skipping", accession, relpath)
                            continue
                        record = records.setdefault(accession, VariableRecord(accession=accession))
                        record.datasets.add(dataset)
                        if record.study_id is None:
                            record.study_id = study_id
                        elif record.study_id != study_id:
                            logger.warning(
                                "Variable %s appears under studies %s and %s; keeping %s",
                                accession,
                                record.study_id,
                                study_id,
                                record.study_id,
                            )
                        usage = VariableUsage(str(derivation.target_class), slot, via_expression, spec_id)
                        if usage not in record.usages:
                            record.usages.append(usage)

    for record in records.values():
        record.usages.sort()
    return dict(sorted(records.items()))
