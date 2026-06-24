"""Command line interface for dm-bip."""

import logging
from typing import Annotated, Optional

import typer

from dm_bip import __version__

__all__ = [
    "app",
    "main",
]


import functools

# =====================================================================
# PERFORMANCE PATCHES FOR LINKML-MAP 0.5.3-rc1
# These intercept slow, un-cached functions to prevent CPU deadlocks.
# =====================================================================
try:
    import linkml_map.functions.unit_conversion as uc
    import linkml_map.utils.lookup_index as li

    # PATCH 1: Cache the expensive UCUM grammar parsing for units
    uc.normalize_unit = functools.lru_cache(maxsize=1024)(uc.normalize_unit)

    _original_parse_units = uc.pint.UnitRegistry.parse_units

    @functools.lru_cache(maxsize=1024)
    def _cached_parse_units(self, unit_str):
        return _original_parse_units(self, unit_str)

    uc.pint.UnitRegistry.parse_units = _cached_parse_units

    # PATCH 2: Cache the DuckDB cross-table join point-queries
    _original_lookup_row = li.LookupIndex.lookup_row

    @functools.lru_cache(maxsize=50000)
    def _cached_lookup_row(self, table_name, lookup_key, key_val):
        # We must ignore the 'self' argument for caching purposes to avoid 
        # hashing the entire DuckDB connection object on every call.
        return _original_lookup_row(self, table_name, lookup_key, key_val)

    li.LookupIndex.lookup_row = _cached_lookup_row

except ImportError:
    # Fails safely if linkml-map isn't installed in the current environment
    pass
# =====================================================================



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
