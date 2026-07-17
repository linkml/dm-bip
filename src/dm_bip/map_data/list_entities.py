"""
List class_derivation entity names from a TransformationSpecification dir/files.

Used by `pipeline.Makefile` to discover entities for per-entity `make -j`
parallelism without first materializing composed spec files. Reuses
``linkml_map.utils.spec_merge`` so the merge semantics match exactly what
``linkml-map map-data -T <dir>/`` does at run time.

Upstream candidate: this is a thin wrapper around ``load_and_merge_specs``
and should move into ``linkml-map`` as a ``list-entities`` CLI subcommand.
Once that lands, this file can be deleted and the Makefile shelled out to
``linkml-map list-entities -T <dir>/`` directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

from linkml_map.utils.spec_merge import load_and_merge_specs


def list_entities(paths: list[str | Path]) -> list[str]:
    """
    Return sorted unique class_derivation entity names from spec paths.

    Tolerates empty/missing inputs (returns ``[]``) so this is safe to call at
    Make parse time before the trans-spec directory exists.

    Args:
        paths: One or more spec file or directory paths.

    Returns:
        Sorted list of unique class_derivation names.

    """
    try:
        merged = load_and_merge_specs(tuple(paths))
    except (FileNotFoundError, ValueError):
        return []

    cds = merged.get("class_derivations") or []
    # When a single spec is loaded, ``load_and_merge_specs`` returns its
    # ``class_derivations`` unchanged — which may be a dict ``{ClassName: body}``
    # rather than the list form produced by the multi-spec merge path.
    if isinstance(cds, dict):
        return sorted(cds.keys())

    names: set[str] = set()
    for cd in cds:
        if not isinstance(cd, dict):
            continue
        if "name" in cd:
            names.add(cd["name"])
        else:
            names.update(cd.keys())
    return sorted(names)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: print one entity name per line."""
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print(f"Usage: {sys.argv[0]} <spec-path> [<spec-path>...]", file=sys.stderr)
        return 1
    for name in list_entities(args):
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
