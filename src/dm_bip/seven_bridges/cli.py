"""Typer subapp for the seven-bridges verb-group: manifest, submit, status, logs."""

from __future__ import annotations

import csv
import enum
import json
import logging
import math
import os
import sys
import time
import urllib.parse
from collections import defaultdict
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
    cohort_mode: Annotated[
        bool,
        typer.Option(
            "--cohort-mode",
            help="Group manifest rows by cohort and submit ONE Parallel Multi-Consent "
            "Execution task per cohort against the app given by --cohort-app "
            "(or SBG_DEFAULT_COHORT_APP). The task drives all consent groups in "
            "one container and runs hv_dataqc at the end.",
        ),
    ] = False,
    cohort_app: Annotated[
        Optional[str],
        typer.Option(
            "--cohort-app",
            help="SBG app ID for the Parallel Multi-Consent Execution Mode workflow. "
            "REQUIRED with --cohort-mode; no default.",
        ),
    ] = None,
    dbgap_cache: Annotated[
        Optional[str],
        typer.Option(
            "--dbgap-cache",
            help=(
                "dbGaP cache root: either an SBG folder ID or an absolute path from "
                "the project root (e.g. /_QC_STAGING/_dbGaP_cache). "
                "When a path is given, the cohort-specific subdirectory is appended "
                "automatically (e.g. copdgene, hchs_sol) and resolved to a folder ID. "
                "Defaults to /_QC_STAGING/_dbGaP_cache."
            ),
        ),
    ] = "/_QC_STAGING/_dbGaP_cache",
    allow_fail: Annotated[
        Optional[list[str]],
        typer.Option(
            "--allow-fail",
            help="Repeatable. Format: <schema>:<cg-name>. Marks a consent group as tolerated to fail.",
        ),
    ] = None,
    strict_consent_groups: Annotated[
        bool,
        typer.Option(
            "--strict-consent-groups/--no-strict-consent-groups",
            help="Cohort mode: fail-fast on unauthorized consent-group failure.",
        ),
    ] = True,
    strict_hv_dataqc: Annotated[
        bool,
        typer.Option(
            "--strict-hv-dataqc/--no-strict-hv-dataqc",
            help="Cohort mode: skip hv_dataqc if any unauthorized failure.",
        ),
    ] = True,
    hv_dataqc_branch: Annotated[
        Optional[str],
        typer.Option("--hv-dataqc-branch", help="Cohort mode: override hv_dataqc code branch."),
    ] = None,
    jobs: Annotated[
        int,
        typer.Option("--jobs", min=1, help="Cohort mode: per-consent make -j."),
    ] = 8,
    consent_parallelism: Annotated[
        Optional[int],
        typer.Option(
            "--consent-parallelism",
            help="Cohort mode: consent groups run concurrently. Default computed from vCPU.",
        ),
    ] = None,
) -> None:
    """
    Submit tasks from the manifest. Default: one task per row (per consent group).

    With `--cohort-mode`, groups rows by Schema and submits one Parallel Multi-Consent
    Execution task per cohort.
    """
    if not manifest_path.exists():
        typer.echo(f"Manifest not found: {manifest_path}. Run `dm-bip seven-bridges manifest` first.", err=True)
        raise typer.Exit(code=2)

    if cohort_mode:
        _submit_cohort_mode(
            project=project,
            cohort_app=cohort_app,
            study_root=study_root,
            manifest_path=manifest_path,
            trans_spec=trans_spec,
            throttle=throttle,
            dbgap_cache=dbgap_cache,
            allow_fail=list(allow_fail or []),
            strict_consent_groups=strict_consent_groups,
            strict_hv_dataqc=strict_hv_dataqc,
            hv_dataqc_branch=hv_dataqc_branch,
            jobs=jobs,
            consent_parallelism=consent_parallelism,
        )
        return

    client = _make_client()
    project_id = project or client.config.project
    app_id = sbg_app or client.config.app
    typer.echo(f"Project: {project_id}")
    typer.echo(f"App:     {app_id}   (from {'--app' if sbg_app else 'SBG_DEFAULT_APP'})")

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


# --- cohort-mode helpers ----------------------------------------------------

# Mirrors the mapping in scripts/workflow/hv-dataqc-cohort.sh.
_COHORT_CACHE_SUBDIR: dict[str, str] = {
    "hchs": "hchs_sol",
    "hchs-sol": "hchs_sol",
}


def _cohort_cache_subdir(schema: str) -> str:
    """Return the dbGaP cache subdirectory name for a cohort schema string."""
    return _COHORT_CACHE_SUBDIR.get(schema.lower(), schema.lower())


def _parse_allow_fail(items: list[str]) -> dict[str, list[str]]:
    """
    Parse `--allow-fail <schema>:<cg>` entries into {schema: [cg, ...]}.

    Rows without a schema prefix are rejected — global allow-fail across cohorts
    is not a useful semantic since consent-group names collide across cohorts.
    """
    out: dict[str, list[str]] = defaultdict(list)
    for item in items:
        if ":" not in item:
            typer.echo(
                f"ERROR: --allow-fail entry '{item}' must use <schema>:<cg-name> form.",
                err=True,
            )
            raise typer.Exit(code=2)
        schema, cg = item.split(":", 1)
        schema = schema.strip()
        cg = cg.strip()
        if not schema or not cg:
            typer.echo(f"ERROR: --allow-fail entry '{item}' has an empty component.", err=True)
            raise typer.Exit(code=2)
        out[schema].append(cg)
    return dict(out)


def _build_cohort_task_bodies(
    project_id: str,
    cohort_app: str,
    manifest_path: Path,
    study_root: str,
    trans_spec: str,
    dbgap_cache: Optional[str],
    allow_fail_by_cohort: dict[str, list[str]],
    strict_consent_groups: bool,
    strict_hv_dataqc: bool,
    hv_dataqc_branch: Optional[str],
    jobs: int,
    consent_parallelism: Optional[int],
    resolve_folders: bool,
) -> list[dict]:
    """
    Return one task body per cohort, ready for SBG task-create.

    When `resolve_folders` is True, SBG API is used to translate consent-group
    folder names to folder IDs. When False (dry-run / plan), the raw folder
    names are echoed back — no network calls required.
    """
    with manifest_path.open() as f:
        rows = list(csv.DictReader(f))

    by_cohort: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_cohort[row["Schema"]].append(row["Filename"])

    if resolve_folders:
        client = _make_client()
        root_folders = client.get_folders(project=project_id)
        pilot_root = next((f for f in root_folders if f["name"] == study_root), None)
        if not pilot_root:
            typer.echo(f"Could not find '{study_root}' folder in {project_id}.", err=True)
            raise typer.Exit(code=1)
        cohort_lookup = {f["name"]: f["id"] for f in client.get_folders(parent=pilot_root["id"])}
    else:
        cohort_lookup = {}

    bodies: list[dict] = []
    for schema, cg_names in by_cohort.items():
        consent_group_refs: list[dict] = []
        if resolve_folders:
            parent_id = cohort_lookup.get(schema)
            if not parent_id:
                typer.echo(f"WARN: cohort folder '{schema}' not found; skipping.", err=True)
                continue
            for name in cg_names:
                encoded = urllib.parse.quote(name, safe="")
                try:
                    resp = client.request(f"files?parent={parent_id}&name={encoded}")
                except SevenBridgesError as exc:
                    typer.echo(f"WARN: {schema}/{name} lookup failed ({exc}); skipping.", err=True)
                    continue
                folder = next(
                    (f for f in resp.get("items", []) if f["type"] == "folder" and f["name"] == name),
                    None,
                )
                if not folder:
                    typer.echo(f"WARN: {schema}/{name} folder not found; skipping.", err=True)
                    continue
                consent_group_refs.append({"class": "Directory", "path": folder["id"]})
        else:
            consent_group_refs = [{"class": "Directory", "path": f"<{schema}/{n}>"} for n in cg_names]

        # Resolve dbGaP cache folder for this cohort.
        # When dbgap_cache is a path (starts with /), append the cohort-specific
        # subdirectory (mirrors the mapping in hv-dataqc-cohort.sh) and resolve
        # to a folder ID via the SBG API. When it's already a folder ID, pass
        # it through unchanged — the container handles subdirectory routing internally.
        cache_ref: dict | None = None
        if dbgap_cache:
            if dbgap_cache.startswith("/"):
                cache_subdir = _cohort_cache_subdir(schema)
                cache_path = f"{dbgap_cache.rstrip('/')}/{cache_subdir}"
                if resolve_folders:
                    try:
                        cache_folder_id = client.resolve_folder_path(project_id, cache_path)
                        cache_ref = {"class": "Directory", "path": cache_folder_id}
                    except SevenBridgesError as exc:
                        typer.echo(
                            f"WARN: dbGaP cache path not found for {schema} ({cache_path!r}): {exc}. "
                            "hv_dataqc compare step may degrade.",
                            err=True,
                        )
                else:
                    cache_ref = {"class": "Directory", "path": f"<resolve:{cache_path}>"}
            else:
                cache_ref = {"class": "Directory", "path": dbgap_cache}

        inputs: dict = {
            "Schema": schema,
            "ConsentGroups": consent_group_refs,
            "StrictConsentGroups": str(strict_consent_groups).lower(),
            "StrictHvDataqc": str(strict_hv_dataqc).lower(),
            "Jobs": jobs,
        }
        if cache_ref is not None:
            inputs["DbgapCache"] = cache_ref
        cohort_allow = allow_fail_by_cohort.get(schema, [])
        if cohort_allow:
            inputs["AllowFail"] = cohort_allow
        if hv_dataqc_branch:
            inputs["HvDataqcBranch"] = hv_dataqc_branch
        if consent_parallelism is not None:
            inputs["ConsentParallelism"] = consent_parallelism
        if trans_spec:
            inputs["TransSpec"] = trans_spec

        bodies.append(
            {
                "project": project_id,
                "app": cohort_app,
                "name": f"Harmonization_{schema}_cohort",
                "inputs": inputs,
            }
        )
    return bodies


def _submit_cohort_mode(
    project: Optional[str],
    cohort_app: Optional[str],
    study_root: str,
    manifest_path: Path,
    trans_spec: str,
    throttle: int,
    dbgap_cache: Optional[str],
    allow_fail: list[str],
    strict_consent_groups: bool,
    strict_hv_dataqc: bool,
    hv_dataqc_branch: Optional[str],
    jobs: int,
    consent_parallelism: Optional[int],
) -> None:
    client = _make_client()
    project_id = project or client.config.project
    # No fallback to client.config.app: that is the single-consent app, and running
    # cohort mode against it would submit a task the app cannot service.
    app_id = cohort_app or client.config.cohort_app
    if not app_id:
        typer.echo(
            "ERROR: --cohort-mode requires an app ID. Pass --cohort-app <owner/project/app>, "
            "or set SBG_DEFAULT_COHORT_APP. There is no default: the app's own Docker "
            "Repository field decides which image runs, so it must be chosen deliberately.",
            err=True,
        )
        raise typer.Exit(code=2)

    # Echo the resolved target before doing anything. An app ID with no trailing
    # /<revision> runs the app's latest revision, which is what picks up a changed
    # Docker Repository field; a pinned revision does not.
    source = "--cohort-app" if cohort_app else "SBG_DEFAULT_COHORT_APP"
    typer.echo(f"Project: {project_id}")
    typer.echo(f"App:     {app_id}   (from {source})")

    allow_fail_by_cohort = _parse_allow_fail(allow_fail)

    bodies = _build_cohort_task_bodies(
        project_id=project_id,
        cohort_app=app_id,
        manifest_path=manifest_path,
        study_root=study_root,
        trans_spec=trans_spec,
        dbgap_cache=dbgap_cache,
        allow_fail_by_cohort=allow_fail_by_cohort,
        strict_consent_groups=strict_consent_groups,
        strict_hv_dataqc=strict_hv_dataqc,
        hv_dataqc_branch=hv_dataqc_branch,
        jobs=jobs,
        consent_parallelism=consent_parallelism,
        resolve_folders=True,
    )

    typer.echo(f"Submitting {len(bodies)} cohort tasks (one per Schema)")
    for i, body in enumerate(bodies):
        typer.echo(f"  {body['name']}...", nl=False)
        try:
            created = client.request("tasks", method="POST", body=body)
            client.request(f"tasks/{created['id']}/actions/run", method="POST")
            typer.echo(f" [RUNNING: {created['id']}]")
        except SevenBridgesError as exc:
            typer.echo(f" [FAILED: {exc}]")

        if i < len(bodies) - 1 and throttle > 0:
            typer.echo(f"  Waiting {throttle}s...")
            time.sleep(throttle)

    typer.echo("\nCohort-mode batch complete.")


# --- plan (dry-run) ---------------------------------------------------------


@app.command()
def plan(
    project: Annotated[
        Optional[str], typer.Option("--project", help="SBG project ID (defaults to SBG_DEFAULT_PROJECT).")
    ] = None,
    cohort_app: Annotated[
        Optional[str],
        typer.Option(
            "--cohort-app",
            help="App ID for the Parallel Multi-Consent Execution Mode workflow. REQUIRED; no default.",
        ),
    ] = None,
    study_root: Annotated[
        str, typer.Option("--study-root", help="Root folder containing cohorts.")
    ] = DEFAULT_STUDY_ROOT,
    manifest_path: Annotated[Path, typer.Option("--manifest", help="Task manifest CSV.")] = DEFAULT_MANIFEST_PATH,
    trans_spec: Annotated[str, typer.Option("--trans-spec", help="Trans-spec slug (OWNER/REPO@REF:PATH).")] = "",
    dbgap_cache: Annotated[
        Optional[str],
        typer.Option(
            "--dbgap-cache",
            help=(
                "dbGaP cache root: folder ID or absolute path from project root "
                "(e.g. /_QC_STAGING/_dbGaP_cache). Defaults to /_QC_STAGING/_dbGaP_cache."
            ),
        ),
    ] = "/_QC_STAGING/_dbGaP_cache",
    allow_fail: Annotated[
        Optional[list[str]], typer.Option("--allow-fail", help="Repeatable. <schema>:<cg-name>.")
    ] = None,
    strict_consent_groups: Annotated[bool, typer.Option("--strict-consent-groups/--no-strict-consent-groups")] = True,
    strict_hv_dataqc: Annotated[bool, typer.Option("--strict-hv-dataqc/--no-strict-hv-dataqc")] = True,
    hv_dataqc_branch: Annotated[Optional[str], typer.Option("--hv-dataqc-branch")] = None,
    jobs: Annotated[int, typer.Option("--jobs", min=1)] = 8,
    consent_parallelism: Annotated[Optional[int], typer.Option("--consent-parallelism")] = None,
    resolve_folders: Annotated[
        bool,
        typer.Option(
            "--resolve-folders/--no-resolve-folders",
            help="When true, contact SBG API to resolve consent-group folder IDs. Off by default so plan runs offline.",
        ),
    ] = False,
) -> None:
    """
    Dry-run: emit the JSON task bodies that `submit --cohort-mode` would post.

    Use `--resolve-folders` to hit the SBG API for real folder IDs, or leave off
    for a pure offline preview (folder IDs shown as `<schema/cg-name>`).
    """
    if not manifest_path.exists():
        typer.echo(f"Manifest not found: {manifest_path}. Run `dm-bip seven-bridges manifest` first.", err=True)
        raise typer.Exit(code=2)

    project_id = project or ""
    if resolve_folders and not project_id:
        client = _make_client()
        project_id = client.config.project
    app_id = cohort_app or os.environ.get("SBG_DEFAULT_COHORT_APP", "")
    if not app_id:
        typer.echo(
            "ERROR: plan requires an app ID. Pass --cohort-app <owner/project/app>, or set SBG_DEFAULT_COHORT_APP.",
            err=True,
        )
        raise typer.Exit(code=2)

    allow_fail_by_cohort = _parse_allow_fail(list(allow_fail or []))

    bodies = _build_cohort_task_bodies(
        project_id=project_id or "<project-id>",
        cohort_app=app_id,
        manifest_path=manifest_path,
        study_root=study_root,
        trans_spec=trans_spec,
        dbgap_cache=dbgap_cache,
        allow_fail_by_cohort=allow_fail_by_cohort,
        strict_consent_groups=strict_consent_groups,
        strict_hv_dataqc=strict_hv_dataqc,
        hv_dataqc_branch=hv_dataqc_branch,
        jobs=jobs,
        consent_parallelism=consent_parallelism,
        resolve_folders=resolve_folders,
    )

    typer.echo(json.dumps(bodies, indent=2))


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
