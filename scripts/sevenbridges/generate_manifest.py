#!/usr/bin/env python3
"""Generate a batch task manifest from the Seven Bridges project folder structure."""

# ruff: noqa: B008

import csv
from pathlib import Path

import typer
from sbg_api import SBG_DEFAULT_PROJECT, get_folders

app = typer.Typer(help="Generate a batch task manifest from SBG project folders.")

_DEFAULT_OUTPUT = Path(__file__).parent / "batch_tasks.csv"


@app.command()
def main(
    project: str = typer.Option(SBG_DEFAULT_PROJECT, help="SBG project ID"),
    output: Path = typer.Option(_DEFAULT_OUTPUT, help="Output CSV path"),
):
    """Crawl PilotParentStudies and generate batch_tasks.csv."""
    root_folders = get_folders(project=project)
    pilot_root = next((f for f in root_folders if f["name"] == "PilotParentStudies"), None)
    if not pilot_root:
        typer.echo("Could not find 'PilotParentStudies' folder.", err=True)
        raise typer.Exit(1)

    rows = []
    for cohort in get_folders(parent=pilot_root["id"]):
        schema = cohort["name"]
        typer.echo(f"  {schema}")
        for group in get_folders(parent=cohort["id"]):
            rows.append({"Filename": group["name"], "Schema": schema})

    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Filename", "Schema"])
        writer.writeheader()
        writer.writerows(rows)

    typer.echo(f"\nGenerated {len(rows)} tasks → {output}")


if __name__ == "__main__":
    app()
