"""Generate provenance YAML capturing build info, dependency versions, and pipeline parameters."""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from importlib_metadata import PackageNotFoundError, version

logger = logging.getLogger(__name__)

TRACKED_PACKAGES = ["dm-bip", "linkml-map", "schema-automator", "linkml"]


def get_build_info() -> dict:
    """Read build-time metadata from environment variables."""
    dm_bip_version = os.environ.get("DM_BIP_VERSION", "unknown")
    if dm_bip_version == "unknown":
        try:
            dm_bip_version = version("dm-bip")
        except PackageNotFoundError:
            pass
    return {
        "version": dm_bip_version,
        "git_ref": os.environ.get("DM_BIP_GIT_REF", "unknown"),
        "build_date": os.environ.get("DM_BIP_BUILD_DATE", "unknown"),
    }


def _get_package_versions() -> dict:
    """Get installed versions of tracked packages."""
    versions = {}
    for pkg in TRACKED_PACKAGES:
        try:
            versions[pkg.replace("-", "_")] = version(pkg)
        except PackageNotFoundError:
            versions[pkg.replace("-", "_")] = "not installed"
    return versions


def _load_repo_manifest(manifest_path: Path) -> dict:
    """Load pre-built repo manifest YAML. Returns empty dict on failure."""
    try:
        with open(manifest_path) as f:
            return yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error("Failed to load repo manifest %s: %s", manifest_path, e)
        return {}


def generate_provenance(
    output_path: Path,
    schema_name: str = "",
    input_dir: str = "",
    trans_spec_dir: str = "",
    target_schema: str = "",
    repo_manifest: Path | None = None,
    no_external_repos: bool = False,
) -> Path:
    """Write provenance YAML to output_path."""
    provenance = {
        "dm_bip": get_build_info(),
        "python": sys.version.split()[0],
        "dependencies": _get_package_versions(),
    }

    if no_external_repos:
        provenance["external_repos"] = "none (local run)"
    elif repo_manifest:
        provenance["external_repos"] = _load_repo_manifest(repo_manifest)

    provenance["pipeline"] = {
        k: v
        for k, v in {
            "schema_name": schema_name,
            "input_dir": input_dir,
            "trans_spec_dir": trans_spec_dir,
            "target_schema": target_schema,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }.items()
        if v
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.safe_dump(provenance, f, default_flow_style=False, sort_keys=False)

    logger.info("Provenance written to %s", output_path)
    return output_path


def main():
    """CLI entry point for generating pipeline provenance YAML."""
    parser = argparse.ArgumentParser(description="Generate pipeline provenance YAML")
    parser.add_argument("--output", required=True, type=Path, help="Output YAML path")
    parser.add_argument("--schema-name", default="")
    parser.add_argument("--input-dir", default="")
    parser.add_argument("--trans-spec-dir", default="")
    parser.add_argument("--target-schema", default="")
    parser.add_argument("--repo-manifest", type=Path, help="Path to repo-manifest.yaml with pre-captured git info")
    parser.add_argument("--no-external-repos", action="store_true", help="Indicate no external repos are expected")
    args = parser.parse_args()

    generate_provenance(
        output_path=args.output,
        schema_name=args.schema_name,
        input_dir=args.input_dir,
        trans_spec_dir=args.trans_spec_dir,
        target_schema=args.target_schema,
        repo_manifest=args.repo_manifest,
        no_external_repos=args.no_external_repos,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
