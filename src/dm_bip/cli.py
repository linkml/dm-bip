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


if __name__ == "__main__":
    app()
