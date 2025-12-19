"""Command line interface for dm-bip."""

import logging

import click

from dm_bip import __version__

__all__ = [
    "main",
]

logger = logging.getLogger(__name__)


@click.group()
@click.option("-v", "--verbose", count=True)
@click.option("-q", "--quiet")
@click.version_option(__version__)
def main(verbose: int, quiet: bool):
    """CLI for dm-bip."""
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


@main.command()
def run():
    """Display usage information for the dm-bip pipeline."""
    click.echo("The dm-bip pipeline is run using make.")
    click.echo("Run 'make help' to see available targets and usage information.")


if __name__ == "__main__":
    main()
