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


@dataclass(frozen=True)
class EntitySpec:
    """Binds a BDCHM entity to its template and its row-completeness rule."""

    template: str
    is_good: Callable[[dict], bool]


def _measobs_is_good(row: dict) -> bool:
    """MeasurementObservation rows carry a precomputed row_good flag from prepare_metadata."""
    return row.get("row_good") == 1


def _condition_is_good(row: dict) -> bool:
    """Return True when a Condition row has its required slots populated."""
    return all(row.get(field) not in (None, "", 0) for field in ("pht", "participantidphv", "onto_id", "phv"))


ENTITY_REGISTRY: dict[str, EntitySpec] = {
    "MeasurementObservation": EntitySpec("yaml_measobs.j2", _measobs_is_good),
    "Condition": EntitySpec("yaml_condition.j2", _condition_is_good),
}


def generate_yaml(
    input_csv: Path,
    output_dir: Path,
    entity: str,
    cohort: str,
    templates_dir: Path = TEMPLATES_DIR,
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

    good_mask = df_filtered.apply(lambda r: spec.is_good(r.to_dict()), axis=1)

    written = []
    for quality in ("good", "bad"):
        subset = df_filtered[good_mask] if quality == "good" else df_filtered[~good_mask]

        for varname, group in subset.groupby("bdchm_varname"):
            safe_name = Path(varname).name
            out_path = output_dir / cohort / quality / f"{safe_name}.yaml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                for _, row in group.iterrows():
                    f.write(template.render(**row.to_dict()))
            written.append(out_path)

    return written
