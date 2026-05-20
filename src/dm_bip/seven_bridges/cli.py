"""Typer subapp for the seven-bridges verb-group: manifest, submit, status, logs."""

from __future__ import annotations

import csv
import enum
import logging
import math
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer

from dm_bip.seven_bridges.client import (
    Client,
    SevenBridgesError,
    TokenMissingError,
    load_config,
)

logger = logging.getLogger("dm_bip.seven_bridges")

DEFAULT_STUDY_ROOT = "PilotParentStudies_NoDRS"
DEFAULT_MANIFEST_PATH = Path("batch_tasks.csv")
DEFAULT_THROTTLE_SECONDS = 60
DEFAULT_LOG_DIR = Path("task_logs")
PIPELINE_LOG_FILES = frozenset({"stdout_dm_bip.log", "stderr_dm_bip.log"})


class LogLevel(str, enum.Enum):
    """Verbosity controls for the seven-bridges subapp."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    silent = "silent"


_LOG_LEVEL_MAP = {
    LogLevel.debug: logging.DEBUG,
    LogLevel.info: logging.INFO,
    LogLevel.warning: logging.WARNING,
    LogLevel.error: logging.ERROR,
    LogLevel.silent: logging.CRITICAL + 10,
}


app = typer.Typer(help="Seven Bridges (BioData Catalyst) task lifecycle: manifest, submit, status, logs.")


@app.callback()
def _configure(
    log_level: Annotated[
        LogLevel,
        typer.Option("--log-level", help="Set verbosity for this command."),
    ] = LogLevel.info,
) -> None:
    """Configure logging for the seven-bridges subapp."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.handlers = [handler]
    logger.setLevel(_LOG_LEVEL_MAP[log_level])
    logger.propagate = False


def _handle_error(exc: SevenBridgesError) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=1) from exc


def _make_client() -> Client:
    return Client(load_config())


# --- manifest ---------------------------------------------------------------


@app.command()
def manifest(
    project: Annotated[
        Optional[str], typer.Option("--project", help="SBG project ID (defaults to SBG_DEFAULT_PROJECT).")
    ] = None,
    study_root: Annotated[
        str, typer.Option("--study-root", help="Root folder containing cohorts.")
    ] = DEFAULT_STUDY_ROOT,
    output: Annotated[Path, typer.Option("--output", "-o", help="Output CSV path.")] = DEFAULT_MANIFEST_PATH,
) -> None:
    """Crawl the project's study-root for cohorts and consent-groups; emit a task manifest CSV."""
    client = _make_client()
    project_id = project or client.config.project

    try:
        root_folders = client.get_folders(project=project_id)
        pilot_root = next((f for f in root_folders if f["name"] == study_root), None)
        if not pilot_root:
            typer.echo(f"Could not find '{study_root}' folder in {project_id}.", err=True)
            raise typer.Exit(code=1)

        rows = []
        for cohort in client.get_folders(parent=pilot_root["id"]):
            schema = cohort["name"]
            typer.echo(f"  {schema}")
            for group in client.get_folders(parent=cohort["id"]):
                rows.append({"Filename": group["name"], "Schema": schema})
    except TokenMissingError as exc:
        _handle_error(exc)
    except SevenBridgesError as exc:
        _handle_error(exc)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Filename", "Schema"])
        writer.writeheader()
        writer.writerows(rows)

    typer.echo(f"\nGenerated {len(rows)} tasks → {output}")


# --- submit -----------------------------------------------------------------


@app.command()
def submit(
    project: Annotated[
        Optional[str], typer.Option("--project", help="SBG project ID (defaults to SBG_DEFAULT_PROJECT).")
    ] = None,
    sbg_app: Annotated[
        Optional[str], typer.Option("--app", help="SBG app (CWL workflow) ID (defaults to SBG_DEFAULT_APP).")
    ] = None,
    study_root: Annotated[
        str, typer.Option("--study-root", help="Root folder containing cohorts.")
    ] = DEFAULT_STUDY_ROOT,
    manifest_path: Annotated[
        Path, typer.Option("--manifest", help="Task manifest CSV (from `manifest` verb).")
    ] = DEFAULT_MANIFEST_PATH,
    trans_spec: Annotated[str, typer.Option("--trans-spec", help="Alternate trans-spec (OWNER/REPO@REF:PATH).")] = "",
    throttle: Annotated[
        int, typer.Option("--throttle", min=0, help="Seconds between task submissions.")
    ] = DEFAULT_THROTTLE_SECONDS,
) -> None:
    """Read the manifest CSV and launch one harmonization task per row, throttled."""
    if not manifest_path.exists():
        typer.echo(f"Manifest not found: {manifest_path}. Run `seven-bridges manifest` first.", err=True)
        raise typer.Exit(code=2)

    client = _make_client()
    project_id = project or client.config.project
    app_id = sbg_app or client.config.app

    try:
        root_folders = client.get_folders(project=project_id)
        pilot_root = next((f for f in root_folders if f["name"] == study_root), None)
        if not pilot_root:
            typer.echo(f"Could not find '{study_root}' folder in {project_id}.", err=True)
            raise typer.Exit(code=1)

        cohort_lookup = {f["name"]: f["id"] for f in client.get_folders(parent=pilot_root["id"])}
    except SevenBridgesError as exc:
        _handle_error(exc)

    typer.echo(f"Found {len(cohort_lookup)} cohorts")

    with manifest_path.open() as f:
        tasks = list(csv.DictReader(f))
    typer.echo(f"Loaded {len(tasks)} tasks from {manifest_path}\n")

    for i, row in enumerate(tasks):
        name, schema = row["Filename"], row["Schema"]
        typer.echo(f"  {name} ({schema})...", nl=False)

        parent_id = cohort_lookup.get(schema)
        if not parent_id:
            typer.echo(f" [ERROR: schema '{schema}' not found]")
            continue

        encoded = urllib.parse.quote(name, safe="")
        try:
            resp = client.request(f"files?parent={parent_id}&name={encoded}")
        except SevenBridgesError as exc:
            typer.echo(f" [FAILED: {exc}]")
            continue
        folder = next((f for f in resp.get("items", []) if f["type"] == "folder" and f["name"] == name), None)
        if not folder:
            typer.echo(f" [ERROR: folder not found in {schema}]")
            continue

        consent_suffix = name.rsplit("-", 1)[-1]
        task_body = {
            "project": project_id,
            "app": app_id,
            "name": f"Harmonization_{schema}_{consent_suffix}",
            "inputs": {
                "Schema": schema,
                "RawSource": {"class": "Directory", "path": folder["id"]},
                **({"TransSpec": trans_spec} if trans_spec else {}),
            },
        }
        try:
            created = client.request("tasks", method="POST", body=task_body)
            client.request(f"tasks/{created['id']}/actions/run", method="POST")
            typer.echo(f" [RUNNING: {created['id']}]")
        except SevenBridgesError as exc:
            typer.echo(f" [FAILED: {exc}]")

        if i < len(tasks) - 1 and throttle > 0:
            typer.echo(f"  Waiting {throttle}s...")
            time.sleep(throttle)

    typer.echo("\nBatch complete.")


# --- status -----------------------------------------------------------------


@app.command()
def status(
    project: Annotated[
        Optional[str], typer.Option("--project", help="SBG project ID (defaults to SBG_DEFAULT_PROJECT).")
    ] = None,
) -> None:
    """Show a dashboard of running tasks with health, duration, and instance type."""
    client = _make_client()
    project_id = project or client.config.project

    try:
        resp = client.request(f"tasks?project={project_id}&status=RUNNING&limit=100")
    except SevenBridgesError as exc:
        _handle_error(exc)

    tasks = resp.get("items", [])
    if not tasks:
        typer.echo("No active tasks.")
        return

    now = datetime.now(timezone.utc)
    rows = []
    for t in tasks:
        try:
            full = client.request(f"tasks/{t['id']}")
        except SevenBridgesError as exc:
            logger.warning("Skipping task %s (%s)", t["id"], exc)
            continue

        duration = "00h 00m"
        submitted = "N/A"
        elapsed_secs = 0.0
        if full.get("created_time"):
            created = datetime.fromisoformat(full["created_time"].replace("Z", "+00:00"))
            elapsed = now - created
            elapsed_secs = elapsed.total_seconds()
            hours = math.floor(elapsed_secs / 3600)
            mins = math.floor((elapsed_secs % 3600) / 60)
            duration = f"{hours:02d}h {mins:02d}m"
            submitted = created.astimezone().strftime("%m/%d %H:%M")

        health = "Healthy"
        instance = "Pending..."
        try:
            details = client.request(f"tasks/{t['id']}/execution_details")
            jobs = details.get("jobs", [])
            if not jobs:
                health = "!! ZOMBIE !!"
            else:
                instance = jobs[0].get("instance_type", "Running...")
        except SevenBridgesError:
            health = "API Delay"

        rows.append(
            {
                "name": full.get("name", "")[:30],
                "health": health,
                "submitted": submitted,
                "duration": duration,
                "sort_key": elapsed_secs,
                "instance": instance,
                "id": full["id"],
            }
        )

    rows.sort(key=lambda r: r["sort_key"], reverse=True)

    fmt = "{:<32} {:<14} {:<14} {:<10} {:<20} {}"
    typer.echo("\n" + fmt.format("Task", "Status", "Submitted", "Duration", "Instance", "ID"))
    typer.echo("-" * 110)
    for r in rows:
        typer.echo(fmt.format(r["name"], r["health"], r["submitted"], r["duration"], r["instance"], r["id"]))


# --- logs -------------------------------------------------------------------


@app.command()
def logs(
    task_id: Annotated[Optional[str], typer.Argument(help="Specific task ID (omit to list recent tasks).")] = None,
    project: Annotated[
        Optional[str], typer.Option("--project", help="SBG project ID (defaults to SBG_DEFAULT_PROJECT).")
    ] = None,
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Directory to save log files.")] = DEFAULT_LOG_DIR,
    statuses: Annotated[
        str, typer.Option("--status", help="Task statuses to list (comma-separated).")
    ] = "COMPLETED,FAILED",
    limit: Annotated[int, typer.Option("--limit", min=1, help="Max tasks to list when no task_id given.")] = 10,
    stdout: Annotated[bool, typer.Option("--stdout", help="Download stdout log.")] = False,
    stderr: Annotated[bool, typer.Option("--stderr", help="Download stderr log.")] = False,
    all_logs: Annotated[bool, typer.Option("--all", help="Download all log files.")] = False,
) -> None:
    """Without a task_id, list recent completed/failed tasks. With one, fetch its logs."""
    client = _make_client()
    project_id = project or client.config.project

    if not task_id:
        try:
            _list_recent_tasks(client, project_id, statuses, limit)
        except SevenBridgesError as exc:
            _handle_error(exc)
        return

    try:
        task = client.request(f"tasks/{task_id}")
        details = client.request(f"tasks/{task_id}/execution_details")
    except SevenBridgesError as exc:
        _handle_error(exc)

    task_name = task.get("name", task_id)
    typer.echo(f"Task: {task_name} ({task.get('status', 'unknown')})")

    jobs = details.get("jobs", [])
    if not jobs:
        typer.echo(f"No jobs found (status: {details.get('status')})")
        return

    task_dir = output_dir / task_name
    task_dir.mkdir(parents=True, exist_ok=True)

    if not (stdout or stderr or all_logs):
        stderr = True  # default to stderr when no flag specified

    wanted: set[str] | None
    if all_logs:
        wanted = None
    else:
        wanted = set()
        if stdout:
            wanted.add("stdout_dm_bip.log")
        if stderr:
            wanted.add("stderr_dm_bip.log")

    for job in jobs:
        job_name = job.get("name", "unknown")
        typer.echo(f"\n  Job: {job_name} ({job.get('status', 'unknown')})")
        for log_name, download_info_url in (job.get("logs") or {}).items():
            if not download_info_url:
                continue
            if wanted is not None and log_name not in wanted:
                continue
            try:
                content = _fetch_log(client, download_info_url)
                log_path = task_dir / f"{job_name}.{log_name}"
                log_path.write_text(content)
                typer.echo(f"    {log_name} ({len(content):,} bytes) → {log_path}")
            except SevenBridgesError as exc:
                typer.echo(f"    {log_name}: failed ({exc})")

    typer.echo(f"\nLogs saved to {task_dir}")


def _list_recent_tasks(client: Client, project: str, statuses: str, limit: int) -> None:
    for s in (s.strip() for s in statuses.split(",") if s.strip()):
        resp = client.request(f"tasks?project={project}&status={s}&limit={limit}")
        items = resp.get("items", [])
        if items:
            typer.echo(f"\n{s} tasks:")
            for t in items:
                typer.echo(f"  {t['id']}  {t['name']}")


def _fetch_log(client: Client, download_info_url: str) -> str:
    """Two-step SBG log fetch: authed GET to download_info → returned signed URL → unauthed GET for content."""
    info = client.request(download_info_url)
    return client.download(info["url"])
