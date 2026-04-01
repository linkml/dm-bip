#!/usr/bin/env python3
"""Submit batch harmonization tasks to Seven Bridges from a CSV manifest."""

# ruff: noqa: B008

import csv
import time
import urllib.parse
from pathlib import Path

import typer
from sbg_api import SBG_DEFAULT_APP, SBG_DEFAULT_PROJECT, get_folders, sbg_request

app = typer.Typer(help="Submit batch harmonization tasks to Seven Bridges.")

_DEFAULT_MANIFEST = Path(__file__).parent / "batch_tasks.csv"


@app.command()
def main(
    project: str = typer.Option(SBG_DEFAULT_PROJECT, help="SBG project ID"),
    app_id: str = typer.Option(SBG_DEFAULT_APP, "--app", help="SBG app (CWL workflow) ID"),
    root_folder: str = typer.Option("PilotParentStudies_NoDRS", "--study-root", help="Root folder containing cohorts"),
    manifest: Path = typer.Option(_DEFAULT_MANIFEST, help="Task manifest CSV"),
    throttle: int = typer.Option(60, help="Seconds between task submissions"),
):
    """Read batch_tasks.csv and launch harmonization tasks."""
    if not manifest.exists():
        typer.echo(f"Manifest not found: {manifest}. Run generate_manifest.py first.", err=True)
        raise typer.Exit(1)

    # Pre-fetch cohort folder IDs
    root_folders = get_folders(project=project)
    pilot_root = next((f for f in root_folders if f["name"] == root_folder), None)
    if not pilot_root:
        typer.echo(f"Could not find '{root_folder}' folder.", err=True)
        raise typer.Exit(1)

    cohort_lookup = {f["name"]: f["id"] for f in get_folders(parent=pilot_root["id"])}
    typer.echo(f"Found {len(cohort_lookup)} cohorts")

    with open(manifest) as f:
        tasks = list(csv.DictReader(f))
    typer.echo(f"Loaded {len(tasks)} tasks from {manifest}\n")

    for i, row in enumerate(tasks):
        name, schema = row["Filename"], row["Schema"]
        typer.echo(f"  {name} ({schema})...", nl=False)

        parent_id = cohort_lookup.get(schema)
        if not parent_id:
            typer.echo(f" [ERROR: schema '{schema}' not found]")
            continue

        # Resolve consent-group folder inside its cohort
        encoded = urllib.parse.quote(name, safe="")
        resp = sbg_request(f"files?parent={parent_id}&name={encoded}")
        folder = next((f for f in resp.get("items", []) if f["type"] == "folder" and f["name"] == name), None)
        if not folder:
            typer.echo(f" [ERROR: folder not found in {schema}]")
            continue

        # Create and run the task
        consent_suffix = name.rsplit("-", 1)[-1]
        task_body = {
            "project": project,
            "app": app_id,
            "name": f"Harmonization_{schema}_{consent_suffix}",
            "inputs": {
                "Schema": schema,
                "RawSource": {"class": "Directory", "path": folder["id"]},
            },
        }
        try:
            created = sbg_request("tasks", method="POST", body=task_body)
            sbg_request(f"tasks/{created['id']}/actions/run", method="POST")
            typer.echo(f" [RUNNING: {created['id']}]")
        except Exception as e:
            typer.echo(f" [FAILED: {e}]")

        if i < len(tasks) - 1:
            typer.echo(f"  Waiting {throttle}s...")
            time.sleep(throttle)

    typer.echo("\nBatch complete.")


if __name__ == "__main__":
    app()
