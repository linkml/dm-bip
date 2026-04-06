"""
Generate YAML transformation specs from metadata CSV using Jinja2 templates.

Refactored from DMCYAML_07_GenerateYAML_forPy.py (RTIInternational/NHLBI-BDC-DMC-HV).
"""

from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


def generate_yaml(
    input_csv: Path,
    output_dir: Path,
    entity: str,
    cohort: str,
    template_name: str = "yaml_measobs.j2",
    templates_dir: Path = TEMPLATES_DIR,
) -> list[Path]:
    """
    Generate YAML files from a metadata CSV for a given entity and cohort.

    Args:
        input_csv: Path to the metadata CSV.
        output_dir: Directory to write YAML output files.
        entity: Entity type to filter on (e.g. "MeasurementObservation").
        cohort: Cohort to filter on (e.g. "aric").
        template_name: Jinja2 template filename.
        templates_dir: Directory containing Jinja2 templates.

    Returns:
        List of paths to generated YAML files.

    """
    df = pd.read_csv(input_csv)

    df_filtered = df[(df["bdchm_entity"] == entity) & (df["cohort"] == cohort)].copy()
    if df_filtered.empty:
        return []

    env = Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True)  # noqa: S701 - generating YAML, not HTML
    template = env.get_template(template_name)

    written = []
    for quality in ("good", "bad"):
        if quality == "good":
            subset = df_filtered[df_filtered["row_good"] == 1]
        else:
            subset = df_filtered[df_filtered["row_good"] != 1]

        for varname, group in subset.groupby("bdchm_varname"):
            out_path = output_dir / cohort / quality / f"{varname}.yaml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w") as f:
                for _, row in group.iterrows():
                    f.write(template.render(**row.to_dict()))
            written.append(out_path)

    return written
