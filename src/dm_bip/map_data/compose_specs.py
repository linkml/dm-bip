"""Compose per-variable transformation specs into per-entity TransformationSpecification files."""

import logging
import sys
from collections import defaultdict
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def compose_specs(spec_dir: Path, output_dir: Path) -> list[Path]:
    """
    Read per-variable spec YAMLs, group by entity, write one composite spec per entity.

    Each input file is a YAML list of blocks like::

        - class_derivations:
            EntityName:
              populated_from: ...

    Output files use compact-key list format understood by linkml-map's
    ``_normalize_spec_dict``::

        class_derivations:
          - EntityName:
              populated_from: ...
          - EntityName:
              populated_from: ...

    Returns the list of written output file paths.
    """
    entity_blocks: dict[str, list[dict]] = defaultdict(list)

    yaml_files = sorted([*spec_dir.rglob("*.yaml"), *spec_dir.rglob("*.yml")])
    for yaml_file in yaml_files:
        try:
            specs = yaml.safe_load(yaml_file.read_text())
        except (OSError, yaml.YAMLError) as e:
            logger.warning("Skipping %s: %s", yaml_file, e)
            continue
        if not isinstance(specs, list):
            continue
        for block in specs:
            if not isinstance(block, dict) or "class_derivations" not in block:
                continue
            for class_name in block["class_derivations"]:
                entity_blocks[class_name].append(block["class_derivations"])

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for entity in sorted(entity_blocks):
        out_path = output_dir / f"{entity}.yaml"
        spec = {"class_derivations": [{entity: d[entity]} for d in entity_blocks[entity]]}
        out_path.write_text(yaml.dump(spec, default_flow_style=False, sort_keys=False))
        written.append(out_path)
        logger.info("Wrote %s (%d derivation(s))", out_path.name, len(entity_blocks[entity]))

    return written


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <spec-dir> <output-dir>", file=sys.stderr)
        sys.exit(1)
    compose_specs(Path(sys.argv[1]), Path(sys.argv[2]))
