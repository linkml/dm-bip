#!/usr/bin/env python3
"""Display a status dashboard for running Seven Bridges tasks."""

import math
from datetime import datetime, timezone

import typer
from sbg_api import SBG_DEFAULT_PROJECT, sbg_request

app = typer.Typer(help="Check status of running Seven Bridges tasks.")


@app.command()
def main(
    project: str = typer.Option(SBG_DEFAULT_PROJECT, help="SBG project ID"),
):
    """Show a dashboard of running tasks with health status and duration."""
    resp = sbg_request(f"tasks?project={project}&status=RUNNING&limit=100")
    tasks = resp.get("items", [])
    now = datetime.now(timezone.utc)

    if not tasks:
        typer.echo("No active tasks.")
        return

    rows = []
    for t in tasks:
        full = sbg_request(f"tasks/{t['id']}")

        duration = "00h 00m"
        submitted = "N/A"
        if full.get("created_time"):
            created = datetime.fromisoformat(full["created_time"].replace("Z", "+00:00"))
            elapsed = now - created
            hours = math.floor(elapsed.total_seconds() / 3600)
            mins = math.floor((elapsed.total_seconds() % 3600) / 60)
            duration = f"{hours:02d}h {mins:02d}m"
            submitted = created.astimezone().strftime("%m/%d %H:%M")

        health = "Healthy"
        instance = "Pending..."
        try:
            details = sbg_request(f"tasks/{t['id']}/execution_details")
            jobs = details.get("jobs", [])
            if not jobs:
                health = "!! ZOMBIE !!"
            else:
                instance = jobs[0].get("instance_type", "Running...")
        except Exception:
            health = "API Delay"

        rows.append(
            {
                "name": full.get("name", "")[:30],
                "health": health,
                "submitted": submitted,
                "duration": duration,
                "sort_key": elapsed.total_seconds() if full.get("created_time") else 0,
                "instance": instance,
                "id": full["id"],
            }
        )

    rows.sort(key=lambda r: r["sort_key"], reverse=True)

    # Render table
    fmt = "{:<32} {:<14} {:<14} {:<10} {:<20} {}"
    typer.echo("\n" + fmt.format("Task", "Status", "Submitted", "Duration", "Instance", "ID"))
    typer.echo("-" * 110)
    for r in rows:
        typer.echo(fmt.format(r["name"], r["health"], r["submitted"], r["duration"], r["instance"], r["id"]))


if __name__ == "__main__":
    app()
