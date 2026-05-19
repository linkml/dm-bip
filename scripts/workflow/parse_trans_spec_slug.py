#!/usr/bin/env python3
"""Parse a --trans-spec slug into Unit-Separator-delimited fields.

Slug format: OWNER/REPO[@REF][:PATH]

Prints one line on stdout, fields joined by ASCII Unit Separator (0x1F):
    OWNER_REPO  REPO_NAME  REF  EXPLICIT_PATH

REF and EXPLICIT_PATH are empty when absent. Unit Separator avoids two
pitfalls of more obvious choices: `$()` would strip trailing newlines
(losing empty trailing fields in a multi-line format), and `IFS=$'\\t'`
would fold consecutive tabs (collapsing empty middle fields).

Errors go to stderr; exits non-zero on invalid input.
"""

import re
import sys

import typer

OWNER_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")

app = typer.Typer(help=__doc__.splitlines()[0], add_completion=False)


def parse_slug(slug: str) -> dict[str, str]:
    """Split slug into owner_repo, repo_name, ref, explicit_path.

    Args:
        slug: A string of the form OWNER/REPO[@REF][:PATH].

    Returns:
        Dict with keys owner_repo, repo_name, ref, explicit_path.
        Missing optional fields are empty strings.

    Raises:
        ValueError: If the slug fails validation.
    """
    remainder = slug

    explicit_path = ""
    if ":" in remainder:
        remainder, explicit_path = remainder.rsplit(":", 1)

    ref = ""
    if "@" in remainder:
        remainder, ref = remainder.rsplit("@", 1)

    if not OWNER_REPO_RE.match(remainder):
        raise ValueError(
            f"Invalid --trans-spec slug '{slug}'\n       Expected OWNER/REPO[@REF][:PATH]"
        )

    if explicit_path and (explicit_path.startswith("/") or ".." in explicit_path):
        raise ValueError(
            f"Explicit trans-spec path must be relative and not contain '..': {explicit_path}"
        )

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
