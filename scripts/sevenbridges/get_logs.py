#!/usr/bin/env python3
"""Fetch execution logs from completed or failed Seven Bridges tasks."""

# ruff: noqa: B008 S310

import json
import urllib.request
from pathlib import Path

import typer
from sbg_api import SBG_DEFAULT_PROJECT, get_token, sbg_request

app = typer.Typer(help="Fetch logs from completed/failed Seven Bridges tasks.")

PIPELINE_LOGS = {"stdout_dm_bip.log", "stderr_dm_bip.log"}


@app.command()
def main(
    task_id: str = typer.Argument(None, help="Specific task ID (omit to list recent tasks)"),
    project: str = typer.Option(SBG_DEFAULT_PROJECT, help="SBG project ID"),
    output_dir: Path = typer.Option(Path("task_logs"), help="Directory to save log files"),
    status: str = typer.Option("COMPLETED,FAILED", help="Task statuses to query (comma-separated)"),
    limit: int = typer.Option(10, help="Max tasks to list when no task_id given"),
    stdout: bool = typer.Option(False, help="Download stdout log"),
    stderr: bool = typer.Option(False, help="Download stderr log"),
    all_logs: bool = typer.Option(False, "--all", help="Download all log files"),
):
    """
    Fetch pipeline logs from a task.

    Without a task ID, lists recent completed/failed tasks.
    Use --stdout, --stderr, or --all to select which logs to download.
    If none specified, defaults to --stderr.
    """
    if not task_id:
        _list_tasks(project, status, limit)
        return

    task = sbg_request(f"tasks/{task_id}")
    task_name = task.get("name", task_id)
    typer.echo(f"Task: {task_name} ({task.get('status', 'unknown')})")

    details = sbg_request(f"tasks/{task_id}/execution_details")
    jobs = details.get("jobs", [])
    if not jobs:
        typer.echo(f"No jobs found (status: {details.get('status')})")
        return

    task_dir = output_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)

    for job in jobs:
        job_name = job.get("name", "unknown")
        typer.echo(f"\n  Job: {job_name} ({job.get('status', 'unknown')})")

        # Default to stderr if no flags specified
        if not (stdout or stderr or all_logs):
            stderr = True

        wanted = set()
        if all_logs:
            wanted = None  # download everything
        else:
            if stdout:
                wanted.add("stdout_dm_bip.log")
            if stderr:
                wanted.add("stderr_dm_bip.log")

        logs = job.get("logs", {})
        for log_name, download_info_url in logs.items():
            if not download_info_url:
                continue
            if wanted is not None and log_name not in wanted:
                continue
            try:
                content = _download_log(download_info_url)
                log_path = task_dir / f"{job_name}.{log_name}"
                log_path.write_text(content)
                typer.echo(f"    {log_name} ({len(content):,} bytes) → {log_path}")
            except Exception as e:
                typer.echo(f"    {log_name}: failed ({e})")

    typer.echo(f"\nLogs saved to {task_dir}")


def _list_tasks(project: str, status: str, limit: int):
    """List recent tasks matching the given statuses."""
    for s in status.split(","):
        resp = sbg_request(f"tasks?project={project}&status={s.strip()}&limit={limit}")
        tasks = resp.get("items", [])
        if tasks:
            typer.echo(f"\n{s.strip()} tasks:")
            for t in tasks:
                typer.echo(f"  {t['id']}  {t['name']}")


def _download_log(download_info_url: str) -> str:
    """Fetch a log file via its SBG download_info endpoint (two-step: signed URL then content)."""
    headers = {"X-SBG-Auth-Token": get_token(), "Content-Type": "application/json"}

    req = urllib.request.Request(download_info_url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        info = json.loads(resp.read())

    req2 = urllib.request.Request(info["url"])
    with urllib.request.urlopen(req2, timeout=60) as resp:
        return resp.read().decode()


if __name__ == "__main__":
    app()
