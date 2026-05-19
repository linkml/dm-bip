"""Typer subapp for the AI harmonize verb-group: set-token, submit, status, fetch, wait, list."""

from __future__ import annotations

import enum
import json as json_module
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Optional

import typer

from dm_bip.ai_harmonize import storage
from dm_bip.ai_harmonize.client import Client, HarmonizeError, content_type_for, decode_jwt_expiry
from dm_bip.ai_harmonize.config import load_config

logger = logging.getLogger("dm_bip.ai_harmonize")

POLL_INTERVAL_SECONDS = 10
TERMINAL_STATUSES = frozenset({"completed", "failed"})


class LogLevel(str, enum.Enum):
    """Verbosity controls for the ai-harmonize subapp."""

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


app = typer.Typer(help="AI-assisted variable harmonization (RTI hosted API).")


@app.callback()
def _configure(
    log_level: Annotated[
        LogLevel,
        typer.Option("--log-level", help="Set verbosity for this command."),
    ] = LogLevel.info,
) -> None:
    """Configure logging for the ai-harmonize subapp."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.handlers = [handler]
    logger.setLevel(_LOG_LEVEL_MAP[log_level])
    logger.propagate = False


def _handle_api_error(exc: HarmonizeError) -> None:
    typer.echo(f"Error: {exc}", err=True)
    raise typer.Exit(code=1) from exc


@app.command(name="set-token")
def set_token(
    token: Annotated[str, typer.Argument(help="JWT id-token obtained from Cognito.")],
) -> None:
    """Cache a JWT id-token for subsequent API calls; expiry comes from the JWT's `exp` claim."""
    config = load_config()
    expires_at = decode_jwt_expiry(token)
    storage.save_token(
        config.token_cache_path,
        storage.CachedToken(token=token, expires_at=expires_at),
    )
    if expires_at is None:
        typer.echo(
            f"Token cached at {config.token_cache_path}.\n"
            "Note: this doesn't look like a JWT; expiry could not be determined."
        )
    else:
        when = time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime(expires_at))
        typer.echo(f"Token cached at {config.token_cache_path}; expires {when}.")


@app.command()
def submit(
    input_file: Annotated[Path, typer.Argument(help="CSV/TSV/Excel file containing variable descriptions.")],
    colname: Annotated[str, typer.Option("--col", "-c", help="Column name holding the descriptions to harmonize.")],
    subset: Annotated[str, typer.Option("--subset", help="Python slice for sampling rows (e.g. '::1000').")] = "",
    pool: Annotated[int, typer.Option("--pool", help="MongoDB vector search pool size.")] = 10,
    chunk_size: Annotated[int, typer.Option("--chunk-size", help="Embedding batch size.")] = 10,
    lim: Annotated[Optional[int], typer.Option("--lim", help="Number of top matches to return per variable.")] = None,
) -> None:
    """Submit a file for harmonization; prints the assigned job_id."""
    if not input_file.exists():
        typer.echo(f"Input file not found: {input_file}", err=True)
        raise typer.Exit(code=2)

    client = Client(load_config())
    try:
        response = client.request_upload_url(
            filename=input_file.name,
            colname=colname,
            subset=subset,
            pool=pool,
            chunk_size=chunk_size,
            lim=lim,
        )
        client.upload_file(response["upload_url"], input_file, content_type_for(input_file.name))
    except HarmonizeError as exc:
        _handle_api_error(exc)

    manifest = storage.JobManifest(
        job_id=response["job_id"],
        submitted_at=time.time(),
        parameters={
            "filename": input_file.name,
            "colname": colname,
            "subset": subset,
            "pool": pool,
            "chunk_size": chunk_size,
            "lim": lim,
        },
        s3_input_key=response.get("s3_key"),
    )
    storage.save_manifest(client.config.job_manifest_dir, manifest)
    typer.echo(response["job_id"])


@app.command()
def status(
    job_id: Annotated[str, typer.Argument(help="Job ID returned by `submit`.")],
    as_json: Annotated[bool, typer.Option("--json", help="Emit the raw API response as JSON.")] = False,
) -> None:
    """Print the current status of a submitted job."""
    client = Client(load_config())
    try:
        payload = client.get_status(job_id)
    except HarmonizeError as exc:
        _handle_api_error(exc)

    if as_json:
        typer.echo(json_module.dumps(payload, indent=2))
    else:
        typer.echo(payload.get("status", "unknown"))

    manifest = storage.load_manifest(client.config.job_manifest_dir, job_id)
    if manifest is not None:
        manifest.last_status = payload.get("status")
        manifest.s3_output_path = payload.get("s3_output_path") or manifest.s3_output_path
        storage.save_manifest(client.config.job_manifest_dir, manifest)


@app.command()
def fetch(
    job_id: Annotated[str, typer.Argument(help="Job ID of a completed job.")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Where to write the results CSV.")],
) -> None:
    """Download results for a completed job."""
    client = Client(load_config())
    try:
        payload = client.get_status(job_id, include_download_url=True)
    except HarmonizeError as exc:
        _handle_api_error(exc)

    if payload.get("status") != "completed":
        typer.echo(f"Job {job_id} is not complete (status: {payload.get('status')}).", err=True)
        raise typer.Exit(code=1)
    url = payload.get("download_url")
    if not url:
        typer.echo("API did not return a download URL.", err=True)
        raise typer.Exit(code=1)

    try:
        client.download_results(url, output)
    except HarmonizeError as exc:
        _handle_api_error(exc)
    typer.echo(str(output))


@app.command()
def wait(
    job_id: Annotated[str, typer.Argument(help="Job ID to wait on.")],
    output: Annotated[
        Optional[Path], typer.Option("--output", "-o", help="Also fetch results to this path when complete.")
    ] = None,
    interval: Annotated[
        int, typer.Option("--interval", min=0, help="Poll interval in seconds.")
    ] = POLL_INTERVAL_SECONDS,
) -> None:
    """Poll until a job reaches a terminal status; optionally fetch results."""
    client = Client(load_config())
    while True:
        try:
            payload = client.get_status(job_id)
        except HarmonizeError as exc:
            _handle_api_error(exc)
        current = payload.get("status", "unknown")
        logger.info("job %s: %s", job_id, current)
        if current in TERMINAL_STATUSES:
            break
        time.sleep(interval)

    if current == "failed":
        typer.echo(f"Job {job_id} failed: {payload.get('error_message', '(no message)')}", err=True)
        raise typer.Exit(code=1)

    if output is not None:
        fetch(job_id=job_id, output=output)
    else:
        typer.echo("completed")


@app.command(name="list")
def list_jobs(
    as_json: Annotated[bool, typer.Option("--json", help="Emit the manifest list as JSON.")] = False,
) -> None:
    """List locally-tracked harmonization jobs (newest first)."""
    config = load_config()
    manifests = storage.list_manifests(config.job_manifest_dir)
    if as_json:
        typer.echo(json_module.dumps([asdict(m) for m in manifests], indent=2, sort_keys=True))
        return

    if not manifests:
        typer.echo("(no tracked jobs)")
        return
    for m in manifests:
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.submitted_at))
        status_str = m.last_status or "?"
        typer.echo(f"{m.job_id}  {ts}  {status_str:<10}  {m.parameters.get('filename', '')}")
