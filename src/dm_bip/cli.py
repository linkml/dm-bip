"""Command line interface for dm-bip."""

import logging
from pathlib import Path
from typing import Annotated, Optional

import typer

from dm_bip import __version__

__all__ = [
    "app",
    "main",
]

logger = logging.getLogger(__name__)

app = typer.Typer(help="CLI for dm-bip.")


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"dm-bip {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[int, typer.Option("-v", "--verbose", count=True, help="Increase verbosity")] = 0,
    quiet: Annotated[Optional[bool], typer.Option("-q", "--quiet", help="Suppress output")] = None,
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True, help="Show version")
    ] = None,
):
    """CLI for dm-bip."""
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


@app.command()
def run():
    """Display usage information for the dm-bip pipeline."""
    typer.echo("The dm-bip pipeline is run using make.")
    typer.echo("Run 'make help' to see available targets and usage information.")


@app.command()
def generate_trans_specs(
    input_csv: Annotated[Path, typer.Option("--input", "-i", help="Path to the metadata CSV")],
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Directory for YAML output files")],
    cohort: Annotated[str, typer.Option("--cohort", "-c", help="Cohort to filter on (e.g. aric, jhs, whi)")],
    entity: Annotated[str, typer.Option("--entity", "-e", help="Entity type to filter on")] = "MeasurementObservation",
    template: Annotated[str, typer.Option("--template", "-t", help="Jinja2 template filename")] = "yaml_measobs.j2",
):
    """Generate trans-spec YAML files from a metadata CSV."""
    from dm_bip.trans_spec_gen.generate_trans_specs import generate_yaml

    results = generate_yaml(
        input_csv=input_csv,
        output_dir=output_dir,
        entity=entity,
        cohort=cohort,
        template_name=template,
    )
    if results:
        typer.echo(f"Generated {len(results)} YAML files in {output_dir}")
        for path in results:
            typer.echo(f"  {path}")
    else:
        typer.echo(f"No matching rows for entity={entity}, cohort={cohort}")
        raise typer.Exit(code=1)


@app.command()
def prepare_metadata(
    raw_files: Annotated[list[Path], typer.Option("--raw", "-r", help="Raw metadata Excel file(s)")],
    bdchv_defs: Annotated[Path, typer.Option("--bdchv-defs", help="Path to bdchv_defs.csv")],
    contextual_vars: Annotated[Path, typer.Option("--contextual-vars", help="Path to contextual_variables_key.csv")],
    unit_key: Annotated[Path, typer.Option("--unit-key", help="Path to unit_key.xlsx")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output CSV path")],
    fixes: Annotated[Optional[Path], typer.Option("--fixes", "-f", help="Curator fixes CSV")] = None,
):
    """Prepare metadata for trans-spec generation from raw dbGaP exports."""
    from dm_bip.trans_spec_gen.prepare_metadata import prepare_metadata as _prepare

    result = _prepare(
        raw_files=raw_files,
        bdchv_defs_path=bdchv_defs,
        contextual_vars_path=contextual_vars,
        unit_key_path=unit_key,
        output_path=output,
        fixes_file=fixes,
    )
    if result is None:
        typer.echo("No data loaded from raw files")
        raise typer.Exit(code=1)
    typer.echo(f"Output written to {result}")


@app.command()
def fetch_digests(
    cohort_key: Annotated[
        Optional[str],
        typer.Argument(help="Cohort key (e.g. jhs, aric). Omit with --list to list cohorts."),
    ] = None,
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="Local cache directory")] = Path(".dbgap-cache"),
    refresh: Annotated[bool, typer.Option("--refresh", help="Force re-fetch of cached files")] = False,
    list_cohorts: Annotated[bool, typer.Option("--list", help="List available cohorts and exit")] = False,
):
    """Fetch dbGaP variable digest files (data_dict.xml, var_report.xml) for a cohort."""
    from dm_bip.prepare_study.fetch_digests import fetch_digests as _fetch
    from dm_bip.prepare_study.fetch_digests import load_cohorts

    cohorts = load_cohorts(cache_dir=cache_dir, refresh=refresh)

    if list_cohorts:
        for key, cohort in sorted(cohorts.items()):
            typer.echo(f"  {key:<12} {cohort.study_id}.{cohort.data_version}  {cohort.display_name}")
        return

    if cohort_key is None:
        typer.echo("Error: cohort_key is required (use --list to see options)")
        raise typer.Exit(code=2)

    if cohort_key not in cohorts:
        typer.echo(f"Unknown cohort '{cohort_key}'. Available: {', '.join(sorted(cohorts))}")
        raise typer.Exit(code=2)

    result = _fetch(cohorts[cohort_key], cache_root=cache_dir, refresh=refresh)
    typer.echo(
        f"Cached {len(result.data_dicts)} data_dict.xml + {len(result.var_reports)} var_report.xml "
        f"under {result.cache_root}"
    )


@app.command()
def parse_digests(
    cohort_key: Annotated[str, typer.Argument(help="Cohort key (e.g. jhs, aric)")],
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="dbGaP digest cache (input)")] = Path(".dbgap-cache"),
    output_dir: Annotated[Path, typer.Option("--output-dir", "-o", help="Output root directory")] = Path("output"),
    refresh_cohorts: Annotated[bool, typer.Option("--refresh-cohorts", help="Re-fetch cohorts.yaml")] = False,
):
    """Convert cached dbGaP digests for a cohort into schema-automator canonical-DD TSVs."""
    from dm_bip.prepare_study.fetch_digests import load_cohorts, parse_cached_digests

    cohorts = load_cohorts(cache_dir=cache_dir, refresh=refresh_cohorts)
    if cohort_key not in cohorts:
        typer.echo(f"Unknown cohort '{cohort_key}'. Available: {', '.join(sorted(cohorts))}")
        raise typer.Exit(code=2)

    written = parse_cached_digests(cohorts[cohort_key], cache_root=cache_dir, output_root=output_dir)
    typer.echo(f"Wrote {len(written)} data dictionaries under {output_dir / cohort_key / 'dd'}")


if __name__ == "__main__":
    app()
