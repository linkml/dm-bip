"""
Index source variables from linkml-map transformation specs.

Where mapping-provenance extraction (``dm_bip.mapping_prov.extract``) is organized around
the *derived* thing — each derivation fragment becoming an entity that records what it was
derived from — a variable library is organized around the *source* thing: the entry is the
dbGaP variable, and it should state every target slot that variable feeds. So this module
reuses that module's spec-reading layer wholesale and re-keys what it yields by ``phv``
accession, accumulating uses rather than keeping the first one seen. The records it builds
are ``bdc_varlib``'s intermediate representation, so that package's emit step consumes them
directly.

Reading the spec, recursing into nested class derivations, and pulling ``{phv...}``
references out of ``expr`` strings all happen in ``mapping_prov.extract``; nothing here
parses YAML. If a third consumer appears, that shared layer is worth lifting into its own
module rather than being imported sideways.
"""

import logging
from pathlib import Path

from bdc_varlib.pipeline.records import VariableRecord, VariableUsage
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
