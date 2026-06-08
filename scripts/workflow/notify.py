#!/usr/bin/env python3
"""
Emit a harmonization run-completion notification (Stage-0 stub).

At the end of a harmonization run the workflow reports the outcome so the
result can be surfaced to users and the submission's JIRA lifecycle issue can
be advanced. The agreed design (see
docs/design/automated-harmonization-orchestration.md §9a) is to deliver a
structured notification to Freshdesk, which auto-creates a ticket that the
Data Submission Tool surfaces and a coordinator acts on.

This is the Stage-0 placeholder: it builds the notification and logs it. The
actual delivery (Freshdesk REST API, per §9a) is wired in Stage 2. It always
exits 0 so a notification problem never fails an otherwise-successful run.
"""

# ruff: noqa: B008

import sys

import typer

app = typer.Typer(help=(__doc__ or "").strip().splitlines()[0], add_completion=False)


def build_notification(
    status: str,
    schema: str,
    accession: str = "",
    version: str = "",
    consent: str = "",
    jira_key: str = "",
    output: str = "",
) -> tuple[str, str]:
    """
    Build the (subject, body) of the completion notification.

    The subject leads with the status and the run identity so a Freshdesk
    automation can route on it; the body carries the full run context plus the
    JIRA issue key used to correlate back to the submission lifecycle. Empty
    optional fields are omitted from the body.
    """
    ident = " ".join(p for p in (schema, accession, version) if p) or "(unknown run)"
    subject = f"[harmonization] {status}: {ident}"
    if jira_key:
        subject += f" ({jira_key})"

    fields = {
        "Status": status,
        "Schema": schema,
        "Accession": accession,
        "Version": version,
        "Consent": consent,
        "JIRA issue": jira_key,
        "Output location": output,
    }
    body = "\n".join(f"{k}: {v}" for k, v in fields.items() if v)
    return subject, body


@app.command()
def main(
    status: str = typer.Option(..., "--status", help="Run outcome: SUCCESS or FAILURE"),
    schema: str = typer.Option("", "--schema", help="Schema / study name"),
    accession: str = typer.Option("", "--accession", help="dbGaP accession (phs)"),
    version: str = typer.Option("", "--version", help="Submission version"),
    consent: str = typer.Option("", "--consent", help="Consent code"),
    jira_key: str = typer.Option("", "--jira-key", help="JIRA issue key for correlation"),
    output: str = typer.Option("", "--output", help="Output / processed directory location"),
):
    """Build the completion notification and log it (Stage-0 stub; no delivery yet)."""
    subject, body = build_notification(status, schema, accession, version, consent, jira_key, output)
    # Stage 2 will deliver this to Freshdesk; for now, log it so the hook is observable.
    print("--- harmonization notification (stub; not yet delivered) ---", file=sys.stderr)
    print(subject, file=sys.stderr)
    print(body, file=sys.stderr)


if __name__ == "__main__":
    app()
