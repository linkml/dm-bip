"""Command line interface for dm-bip."""

import logging
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


if __name__ == "__main__":
    app()
