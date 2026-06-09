"""Unit tests for scripts/workflow/notify.py."""

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "workflow" / "notify.py"


def _load_module():
    """Import the script as a module so we can test its functions directly."""
    spec = importlib.util.spec_from_file_location("notify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_notification = _load_module().build_notification


# --- Subject ----------------------------------------------------------------


def test_subject_leads_with_status_and_identity():
    """Subject leads with the status and the run identity for routing."""
    subject, _ = build_notification("SUCCESS", "FHS", accession="phs000007", version="v3")
    assert subject.startswith("[harmonization] SUCCESS:")
    assert "FHS" in subject
    assert "phs000007" in subject


def test_subject_includes_jira_key_when_present():
    """The JIRA issue key is appended to the subject for correlation."""
    subject, _ = build_notification("FAILURE", "FHS", jira_key="DMC-123")
    assert "DMC-123" in subject


def test_unknown_identity_when_all_blank():
    """With no schema/accession/version, the subject still renders a placeholder."""
    subject, _ = build_notification("FAILURE", "")
    assert "(unknown run)" in subject


# --- Body -------------------------------------------------------------------


def test_body_includes_populated_fields_only():
    """Populated fields appear; empty optional fields are omitted."""
    _, body = build_notification("SUCCESS", "FHS", accession="phs000007", jira_key="DMC-1")
    assert "Status: SUCCESS" in body
    assert "Schema: FHS" in body
    assert "Accession: phs000007" in body
    assert "JIRA issue: DMC-1" in body
    assert "Version:" not in body
    assert "Consent:" not in body


# --- CLI --------------------------------------------------------------------


def test_cli_always_exits_zero():
    """The stub must never fail a run; it logs to stderr and exits 0."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "--status", "SUCCESS", "--schema", "FHS", "--jira-key", "DMC-9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "harmonization notification" in result.stderr
    assert "DMC-9" in result.stderr
