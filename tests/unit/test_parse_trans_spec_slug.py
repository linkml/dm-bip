"""Unit tests for scripts/workflow/parse_trans_spec_slug.py."""

import importlib.util
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "workflow" / "parse_trans_spec_slug.py"


def _load_module():
    """Import the script as a module so we can test parse_slug directly."""
    spec = importlib.util.spec_from_file_location("parse_trans_spec_slug", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


parse_slug = _load_module().parse_slug


# --- Direct function tests --------------------------------------------------


def test_owner_repo_only():
    """Bare OWNER/REPO yields empty ref and explicit_path."""
    result = parse_slug("RTIInternational/NHLBI-BDC-DMC-HV")
    assert result == {
        "owner_repo": "RTIInternational/NHLBI-BDC-DMC-HV",
        "repo_name": "NHLBI-BDC-DMC-HV",
        "ref": "",
        "explicit_path": "",
    }


def test_with_ref():
    """@REF is extracted into ref."""
    result = parse_slug("amc-corey-cox/bdc-harmonized-variables@main")
    assert result["ref"] == "main"
    assert result["owner_repo"] == "amc-corey-cox/bdc-harmonized-variables"
    assert result["repo_name"] == "bdc-harmonized-variables"
    assert result["explicit_path"] == ""


def test_with_path():
    """:PATH is extracted into explicit_path."""
    result = parse_slug("owner/repo:trans_specs/FHS/v1.0")
    assert result["explicit_path"] == "trans_specs/FHS/v1.0"
    assert result["ref"] == ""


def test_with_ref_and_path():
    """Both @REF and :PATH parse correctly."""
    result = parse_slug("owner/repo@feature/branch:some/path")
    assert result["owner_repo"] == "owner/repo"
    assert result["ref"] == "feature/branch"
    assert result["explicit_path"] == "some/path"


def test_repo_name_is_last_segment():
    """repo_name is the part after the slash in OWNER/REPO."""
    assert parse_slug("a/b")["repo_name"] == "b"
    assert parse_slug("nested.org/my-repo.git")["repo_name"] == "my-repo.git"


@pytest.mark.parametrize(
    "bad_slug",
    [
        "no-slash",
        "/leading-slash",
        "trailing-slash/",
        "too/many/slashes",
        "spaces in/name",
        "",
    ],
)
def test_invalid_owner_repo_raises(bad_slug):
    """Malformed OWNER/REPO portion is rejected."""
    with pytest.raises(ValueError, match="Invalid"):
        parse_slug(bad_slug)


def test_absolute_explicit_path_rejected():
    """Absolute paths are rejected to avoid escaping the repo dir."""
    with pytest.raises(ValueError, match="must be relative"):
        parse_slug("owner/repo:/etc/passwd")


def test_path_traversal_rejected():
    """Paths containing '..' are rejected to avoid escaping the repo dir."""
    with pytest.raises(ValueError, match="must be relative"):
        parse_slug("owner/repo:../outside")


@pytest.mark.parametrize(
    "bad_slug",
    [
        "owner/repo@bad\x1fref",  # ref contains Unit Separator
        "owner/repo@bad\nref",  # ref contains newline
        "owner/repo:bad\x1fpath",  # path contains Unit Separator
        "owner/repo:bad\tpath",  # path contains tab
    ],
)
def test_control_chars_in_ref_or_path_rejected(bad_slug):
    r"""Control chars would corrupt the \x1f-delimited output and break bash IFS-split."""
    with pytest.raises(ValueError, match="control characters"):
        parse_slug(bad_slug)


# --- CLI / shell-contract tests ---------------------------------------------


def _run(*args) -> subprocess.CompletedProcess:
    """Invoke the script and return the completed process."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_prints_single_us_separated_line():
    """Output is exactly one Unit-Separator-delimited line."""
    result = _run("owner/repo@main:sub/dir")
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert lines == ["owner/repo\x1frepo\x1fmain\x1fsub/dir"]


def test_cli_emits_empty_fields_for_missing_optionals():
    """Missing ref and explicit_path appear as empty fields between separators."""
    result = _run("owner/repo")
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    assert lines == ["owner/repo\x1frepo\x1f\x1f"]


@pytest.mark.parametrize(
    ("slug", "expected"),
    [
        ("owner/repo@v1.0:nested/path", "owner/repo|repo|v1.0|nested/path"),
        # Regression cases that broke earlier formats:
        ("owner/repo", "owner/repo|repo||"),  # empty trailing fields must survive $()
        ("owner/repo@main", "owner/repo|repo|main|"),
        ("owner/repo:some/path", "owner/repo|repo||some/path"),  # empty middle field must not fold
    ],
)
def test_cli_consumable_via_bash_capture_and_read(slug, expected):
    """Mirror the exact $()+`read` pattern in bdc-workflow.sh, including empty fields."""
    # Production call site quotes the slug as "$TRANS_SPEC_SLUG"; mirror that here.
    bash_script = (
        f"slug_fields=$({shlex.quote(sys.executable)} {shlex.quote(str(SCRIPT))} {shlex.quote(slug)}) || exit 1; "
        "IFS=$'\\x1f' read -r OWNER REPO REF EXPLICIT_PATH <<< \"$slug_fields\"; "
        'echo "$OWNER|$REPO|$REF|$EXPLICIT_PATH"'
    )
    bash = subprocess.run(  # noqa: S603
        ["bash", "-euo", "pipefail", "-c", bash_script],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    assert bash.stdout.strip() == expected


def test_cli_bad_slug_exits_nonzero_with_stderr_message():
    """Invalid slug returns non-zero and writes ERROR to stderr."""
    result = _run("bad-no-slash")
    assert result.returncode != 0
    assert "ERROR" in result.stderr
    assert "OWNER/REPO" in result.stderr


def test_cli_shell_injection_in_slug_does_not_execute():
    """A slug containing shell metacharacters is rejected, not executed."""
    result = _run("owner/repo;rm -rf /")
    assert result.returncode != 0
    assert "ERROR" in result.stderr
