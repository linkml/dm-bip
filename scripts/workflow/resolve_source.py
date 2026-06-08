#!/usr/bin/env python3
"""
Resolve a raw-data source specification to a local directory path.

The harmonization pipeline always consumes a local directory of raw files.
This helper takes the ``--source`` value handed to the workflow and returns the
local directory the pipeline should read, dispatching on the source scheme:

    <local path>            an existing directory (a plain mounted directory, or
                            a Seven Bridges volume presented as a local path) —
                            returned unchanged
    s3://<bucket>/<prefix>  object-storage source — fetched to a local directory
                            (not yet implemented; Stage 1)
    drs://<id>              GA4GH DRS object(s) — resolved to local files
                            (not yet implemented; Stage 3)

This is the single pluggable acquisition seam: downstream stages never change,
regardless of where the data came from. See
docs/design/automated-harmonization-orchestration.md (§7, §8).

Prints the resolved local directory on stdout. Errors go to stderr;
exits non-zero on failure.
"""

# ruff: noqa: B008

import sys
from pathlib import Path

import typer

app = typer.Typer(help=(__doc__ or "").strip().splitlines()[0], add_completion=False)


def resolve_source(source: str) -> str:
    """
    Resolve a source spec to a local directory path, or raise on failure.

    Args:
        source: The raw-data source: a local directory path, an ``s3://`` URL,
            or a ``drs://`` identifier.

    Returns:
        The local directory path the pipeline should read.

    Raises:
        ValueError: If ``source`` is empty.
        FileNotFoundError: If a local source path is not an existing directory.
        NotImplementedError: If the scheme (``s3://``, ``drs://``) is recognized
            but not yet supported.

    """
    if not source:
        raise ValueError("Source must not be empty")

    if source.startswith("s3://"):
        raise NotImplementedError(
            "s3:// source acquisition is not yet implemented (Stage 1). "
            "Attach the bucket as a Seven Bridges volume and pass its mounted path instead."
        )

    if source.startswith("drs://"):
        raise NotImplementedError("drs:// source resolution is not yet implemented (Stage 3).")

    if not Path(source).is_dir():
        raise FileNotFoundError(f"Source directory does not exist: {source}")

    return source


@app.command()
def main(
    source: str = typer.Option(..., "--source", help="Raw-data source: local dir, s3:// URL, or drs:// id"),
):
    """Resolve the raw-data source to a local directory and print it on stdout."""
    try:
        resolved = resolve_source(source)
    except (ValueError, FileNotFoundError, NotImplementedError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    print(resolved)


if __name__ == "__main__":
    app()
