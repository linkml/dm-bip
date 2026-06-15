"""
Generate YAML transformation specs from metadata CSV using Jinja2 templates.

Refactored from DMCYAML_07_GenerateYAML_forPy.py (RTIInternational/NHLBI-BDC-DMC-HV).
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


DEFAULT_LAYOUT = "{cohort}/{quality}/{varname}.yaml"


@dataclass(frozen=True)
class EntitySpec:
    """Binds a BDCHM entity to its template and its row-completeness rule."""

    template: str
    is_good: Callable[[pd.Series], bool]


def _measobs_is_good(row: pd.Series) -> bool:
    """MeasurementObservation rows carry a precomputed row_good flag from prepare_metadata."""
    return row.get("row_good") == 1


_CONDITION_REQUIRED = (
    "pht",
    "participantidphv",
    "onto_id",
    "phv",
    "associatedvisit",
    "value_mappings",
    "condition_provenance",
)


def _condition_is_good(row: pd.Series) -> bool:
    """Return True when a Condition row has every slot the template needs to emit a complete spec."""
    return all(row.get(field) not in (None, "", 0) for field in _CONDITION_REQUIRED)


ENTITY_REGISTRY: dict[str, EntitySpec] = {
    "MeasurementObservation": EntitySpec("yaml_measobs.j2", _measobs_is_good),
    "Condition": EntitySpec("yaml_condition.j2", _condition_is_good),
}


def _safe_output_path(output_dir: Path, rel: str) -> Path:
    """Reject absolute or traversal paths; ensure result stays under output_dir."""
    rel_path = Path(rel)
    if rel_path.is_absolute():
        raise ValueError(f"layout produced absolute path {rel!r}; must be relative to output_dir")
    candidate = (output_dir / rel_path).resolve()
    base = output_dir.resolve()
    if base != candidate and base not in candidate.parents:
        raise ValueError(f"layout {rel!r} resolves outside output_dir {output_dir}")
    return candidate


def generate_yaml(
    input_csv: Path,
    output_dir: Path,
    entity: str,
    cohort: str,
    templates_dir: Path = TEMPLATES_DIR,
    layout: str = DEFAULT_LAYOUT,
) -> list[Path]:
    """
    Generate YAML files from a metadata CSV for a given entity and cohort.

    Args:
        input_csv: Path to the metadata CSV.
        output_dir: Directory to write YAML output files.
        entity: Entity type to filter on (e.g. "MeasurementObservation"). Selects the
            template and completeness rule from ENTITY_REGISTRY.
        cohort: Cohort to filter on (e.g. "aric").
        templates_dir: Directory containing Jinja2 templates.
        layout: Output path template under ``output_dir``. Supports
            ``{cohort}``, ``{quality}``, ``{varname}``. Defaults to
            ``{cohort}/{quality}/{varname}.yaml``.

    Returns:
        List of paths to generated YAML files.

    """
    spec = ENTITY_REGISTRY.get(entity)
    if spec is None:
        raise ValueError(f"No registered entity spec for {entity!r}; known: {sorted(ENTITY_REGISTRY)}")

    df = pd.read_csv(input_csv)
    df = df.fillna(0)

    df_filtered = df[(df["bdchm_entity"] == entity) & (df["cohort"] == cohort)].copy()
    if df_filtered.empty:
        return []

    env = Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True)  # noqa: S701 - generating YAML, not HTML
    template = env.get_template(spec.template)

    good_mask = df_filtered.apply(spec.is_good, axis=1)

    written = []
    for quality in ("good", "bad"):
        subset = df_filtered[good_mask] if quality == "good" else df_filtered[~good_mask]

        for varname, group in subset.groupby("bdchm_varname"):
            safe_name = Path(varname).name
            rel = layout.format(cohort=cohort, quality=quality, varname=safe_name)
            out_path = _safe_output_path(output_dir, rel)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                for _, row in group.iterrows():
                    f.write(template.render(**row.to_dict()))
            written.append(out_path)

    return written
