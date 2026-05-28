#!/usr/bin/env python3
r"""
Parse a --trans-spec slug into Unit-Separator-delimited fields.

Slug format: OWNER/REPO[@REF][:PATH]

Prints one line on stdout, fields joined by ASCII Unit Separator (0x1F):
    OWNER_REPO  REPO_NAME  REF  EXPLICIT_PATH

REF and EXPLICIT_PATH are empty when absent. Unit Separator avoids two
pitfalls of more obvious choices: `$()` would strip trailing newlines
(losing empty trailing fields in a multi-line format), and `IFS=$'\t'`
would fold consecutive tabs (collapsing empty middle fields).

Errors go to stderr; exits non-zero on invalid input.
"""

# ruff: noqa: B008

import re
import sys

import typer

OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")

app = typer.Typer(help=(__doc__ or "").strip().splitlines()[0], add_completion=False)


def parse_slug(slug: str) -> dict[str, str]:
    """Split a slug `OWNER/REPO[@REF][:PATH]` into its four fields (missing optionals as empty strings)."""
    remainder = slug

    explicit_path = ""
    if ":" in remainder:
        remainder, explicit_path = remainder.rsplit(":", 1)

    ref = ""
    if "@" in remainder:
        remainder, ref = remainder.rsplit("@", 1)

    if not OWNER_REPO_RE.match(remainder):
        raise ValueError(f"Invalid --trans-spec slug '{slug}'\n       Expected OWNER/REPO[@REF][:PATH]")

    # bdc-workflow.sh unconditionally appends `.git` when cloning, so accepting
    # a `.git` suffix here would produce a `.git.git` URL that fails to clone.
    if remainder.endswith(".git"):
        raise ValueError(f"Repo segment must not include the '.git' suffix: {slug}")

    if explicit_path and (explicit_path.startswith("/") or ".." in explicit_path):
        raise ValueError(f"Explicit trans-spec path must be relative and not contain '..': {explicit_path}")

    # Control characters in ref/explicit_path would corrupt the \x1f-delimited
    # output and let bash mis-split the fields. Forbid them in both.
    for field_name, field_value in (("ref", ref), ("explicit path", explicit_path)):
        if any(ord(c) < 0x20 for c in field_value):
            raise ValueError(f"Trans-spec {field_name} must not contain control characters")

    return {
        "owner_repo": remainder,
        "repo_name": remainder.rsplit("/", 1)[1],
        "ref": ref,
        "explicit_path": explicit_path,
    }


@app.command()
def main(slug: str = typer.Argument(..., help="Slug of the form OWNER/REPO[@REF][:PATH]")):
    """Parse the slug and print fields on a single Unit-Separator-delimited line."""
    try:
        fields = parse_slug(slug)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        raise typer.Exit(1) from e

    print("\x1f".join([fields["owner_repo"], fields["repo_name"], fields["ref"], fields["explicit_path"]]))


if __name__ == "__main__":
    app()
