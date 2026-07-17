#!/usr/bin/env python3
"""
Resolve the trans-spec directory inside a cloned trans-spec repo.

Given a repo directory and a schema name, return the absolute path to the
directory that holds the schema's transformation specs. Two repo layouts are
supported:

    NHLBI-BDC-DMC-HV layout:
        <repo>/priority_variables_transform/<SCHEMA>-ingest/

    bdc-harmonized-variables layout (versioned):
        <repo>/trans_specs/<SCHEMA>/<latest-version>/

If --explicit-path is provided, it overrides auto-detection.

Prints the resolved absolute path on stdout. Errors go to stderr;
exits non-zero on failure.
"""

# ruff: noqa: B008

import re
import sys
from pathlib import Path

import typer

app = typer.Typer(help=(__doc__ or "").strip().splitlines()[0], add_completion=False)


def _version_sort_key(name: str) -> tuple:
    """Natural-sort key that orders '1.10' after '1.2', and stays deterministic on mixed names like '1.0' vs 'v1.0'."""
    chunks = []
    for c in re.split(r"(\d+)", name):
        if not c:
            continue
        chunks.append((0, int(c)) if c.isdigit() else (1, c))
    return tuple(chunks)


def resolve_trans_spec_dir(repo_dir: Path, schema_name: str, explicit_path: str = "") -> Path:
    """Resolve the trans-spec directory for a schema; returns an absolute Path or raises on failure."""
    if not repo_dir.is_dir():
        raise ValueError(f"Repo directory does not exist: {repo_dir}")
    repo_dir = repo_dir.resolve()

    if explicit_path:
        if explicit_path.startswith("/") or ".." in explicit_path:
            raise ValueError(f"Explicit trans-spec path must be relative and not contain '..': {explicit_path}")
        resolved = repo_dir / explicit_path
        if not resolved.is_dir():
            raise FileNotFoundError(f"Explicit trans-spec path not found: {resolved}")
        return resolved

    pvt = repo_dir / "priority_variables_transform"
    trans_specs = repo_dir / "trans_specs"

    if pvt.is_dir():
        resolved = pvt / f"{schema_name}-ingest"
        if not resolved.is_dir():
            raise FileNotFoundError(f"Auto-detected trans-spec directory not found: {resolved}")
        return resolved

    if trans_specs.is_dir():
        base = trans_specs / schema_name
        if not base.is_dir():
            raise FileNotFoundError(f"No trans-spec directory for schema '{schema_name}' under {trans_specs}")
        versions = sorted(
            (p for p in base.iterdir() if p.is_dir()),
            key=lambda p: _version_sort_key(p.name),
        )
        if not versions:
            raise FileNotFoundError(f"No trans-spec version directory found under {base}")
        return versions[-1]

    raise ValueError(
        f"Cannot auto-detect trans-spec layout in {repo_dir}\n"
        "       Use OWNER/REPO@REF:PATH to specify the path explicitly"
    )


@app.command()
def main(
    repo_dir: Path = typer.Option(..., "--repo-dir", help="Path to the cloned trans-spec repo"),
    schema_name: str = typer.Option(..., "--schema-name", help="Schema name (e.g., FHS)"),
    explicit_path: str = typer.Option(
        "", "--explicit-path", help="Optional relative path within the repo (overrides auto-detect)"
    ),
):
    """Resolve the trans-spec directory and print it on stdout."""
    try:
        resolved = resolve_trans_spec_dir(repo_dir, schema_name, explicit_path)
    except (ValueError, FileNotFoundError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    print(resolved)


if __name__ == "__main__":
    app()
