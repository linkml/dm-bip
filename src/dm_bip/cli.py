"""Command line interface for dm-bip."""

import logging
import re
from pathlib import Path
from typing import Annotated, Optional

import typer

from dm_bip import __version__
from dm_bip.seven_bridges.cli import app as seven_bridges_app

__all__ = [
    "app",
    "main",
]

logger = logging.getLogger(__name__)

# A real study id carries a dbGaP accession (``bdchm:Study/phs000280``); a placeholder does not.
_PHS_RE = re.compile(r"phs\d+")

app = typer.Typer(
    help="CLI for dm-bip.",
    epilog="For pipeline orchestration (schema generation, validation, mapping), use `make help`.",
)
app.add_typer(seven_bridges_app, name="seven-bridges")


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        typer.echo(f"dm-bip {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    verbose: Annotated[int, typer.Option("-v", "--verbose", count=True, help="Increase verbosity")] = 0,
    quiet: Annotated[Optional[bool], typer.Option("-q", "--quiet", help="Suppress output")] = None,
    version: Annotated[
        Optional[bool], typer.Option("--version", callback=version_callback, is_eager=True, help="Show version")
    ] = None,
):
    """CLI for dm-bip."""
    if verbose >= 2:
        logger.setLevel(level=logging.DEBUG)
    elif verbose == 1:
        logger.setLevel(level=logging.INFO)
    else:
        logger.setLevel(level=logging.WARNING)
    if quiet:
        logger.setLevel(level=logging.ERROR)


@app.command()
def run():
    """Display usage information for the dm-bip pipeline."""
    typer.echo("The dm-bip pipeline is run using make.")
    typer.echo("Run 'make help' to see available targets and usage information.")


@app.command()
def generate_trans_specs(
    input_csv: Annotated[Path, typer.Option("--input", "-i", help="Path to the metadata CSV")],
    output_dir: Annotated[Path, typer.Option("--output", "-o", help="Directory for YAML output files")],
    cohort: Annotated[str, typer.Option("--cohort", "-c", help="Cohort to filter on (e.g. aric, jhs, whi)")],
    entity: Annotated[str, typer.Option("--entity", "-e", help="Entity type to filter on")] = "MeasurementObservation",
):
    """Generate trans-spec YAML files from a metadata CSV."""
    from dm_bip.trans_spec_gen.generate_trans_specs import ENTITY_REGISTRY, generate_yaml

    if entity not in ENTITY_REGISTRY:
        raise typer.BadParameter(
            f"{entity!r} is not a registered entity; choose from {sorted(ENTITY_REGISTRY)}",
            param_hint="--entity",
        )

    results = generate_yaml(
        input_csv=input_csv,
        output_dir=output_dir,
        entity=entity,
        cohort=cohort,
    )
    if results:
        typer.echo(f"Generated {len(results)} YAML files in {output_dir}")
        for path in results:
            typer.echo(f"  {path}")
    else:
        typer.echo(f"No matching rows for entity={entity}, cohort={cohort}")
        raise typer.Exit(code=1)


@app.command()
def prepare_metadata(
    raw_files: Annotated[list[Path], typer.Option("--raw", "-r", help="Raw metadata Excel file(s)")],
    bdchv_defs: Annotated[Path, typer.Option("--bdchv-defs", help="Path to bdchv_defs.csv")],
    contextual_vars: Annotated[Path, typer.Option("--contextual-vars", help="Path to contextual_variables_key.csv")],
    unit_key: Annotated[Path, typer.Option("--unit-key", help="Path to unit_key.xlsx")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output CSV path")],
    cleanup_rules: Annotated[Optional[Path], typer.Option("--cleanup-rules", help="Curator cleanup rules CSV")] = None,
):
    """Prepare metadata for trans-spec generation from raw dbGaP exports."""
    from dm_bip.trans_spec_gen.prepare_metadata import prepare_metadata as _prepare

    result = _prepare(
        raw_files=raw_files,
        bdchv_defs_path=bdchv_defs,
        contextual_vars_path=contextual_vars,
        unit_key_path=unit_key,
        output_path=output,
        cleanup_rules_path=cleanup_rules,
    )
    if result is None:
        typer.echo("No data loaded from raw files")
        raise typer.Exit(code=1)
    typer.echo(f"Output written to {result}")


@app.command()
def fetch_digests(
    cohort_key: Annotated[
        Optional[str],
        typer.Argument(help="Cohort key (e.g. jhs, aric). Omit with --list to list cohorts."),
    ] = None,
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="Local cache directory")] = Path(".dbgap-cache"),
    refresh: Annotated[bool, typer.Option("--refresh", help="Force re-fetch of cached files")] = False,
    list_cohorts: Annotated[bool, typer.Option("--list", help="List available cohorts and exit")] = False,
):
    """Fetch dbGaP variable digest files (data_dict.xml, var_report.xml) for a cohort."""
    from dm_bip.prepare_study.fetch_digests import fetch_digests as _fetch
    from dm_bip.prepare_study.fetch_digests import load_cohorts, write_pairs_mk

    cohorts = load_cohorts(cache_dir=cache_dir, refresh=refresh)

    if list_cohorts:
        for key, cohort in sorted(cohorts.items()):
            typer.echo(f"  {key:<12} {cohort.study_id}.{cohort.data_version}  {cohort.display_name}")
        return

    if cohort_key is None:
        typer.echo("Error: cohort_key is required (use --list to see options)")
        raise typer.Exit(code=2)

    if cohort_key not in cohorts:
        typer.echo(f"Unknown cohort '{cohort_key}'. Available: {', '.join(sorted(cohorts))}")
        raise typer.Exit(code=2)

    result = _fetch(cohorts[cohort_key], cache_root=cache_dir, refresh=refresh)
    pairs_mk = write_pairs_mk(result, cache_dir / cohort_key / "digest_pairs.mk")
    typer.echo(
        f"Cached {len(result.data_dicts)} data_dict.xml + {len(result.var_reports)} var_report.xml "
        f"under {result.cache_root}; pairings in {pairs_mk}"
    )


@app.command()
def extract_mapping_provenance(
    paths: Annotated[list[Path], typer.Argument(exists=True, help="Transformation spec files or directories")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output YAML file (default: stdout)")] = None,
):
    """Extract mapping provenance (study, dataset, and variable sources) from transformation specs."""
    from datetime import datetime, timezone

    from dm_bip.mapping_prov.extract import collect_spec_paths, extract_provenance, run_activity, to_yaml

    spec_paths = collect_spec_paths(paths)
    if not spec_paths:
        typer.echo("No transformation spec files found", err=True)
        raise typer.Exit(code=1)

    started_at = datetime.now(timezone.utc)
    studies = extract_provenance(spec_paths)
    activity = run_activity(studies, started_at, datetime.now(timezone.utc))
    serialized = to_yaml([activity, *studies])
    if output is None:
        typer.echo(serialized)
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized)
        typer.echo(f"Mapping provenance written to {output}")


def _dbgap_metadata(records, classify, cohort_key, cache_dir, fetch, with_var_report, refresh):
    """
    Build a dbGaP metadata source covering the datasets these records name, or None.

    Returning None is a normal outcome, not a failure: a study with no dbGaP presence still
    yields entries, just without the descriptive slots.
    """
    from dm_bip.prepare_study.fetch_digests import (
        cached_digests,
        cohort_for_study,
        fetch_digests,
        load_cohorts,
    )
    from dm_bip.variable_lib.dbgap_metadata import metadata_for

    if not records:
        return None

    # Auto-detect needs the cohort registry, which is fetched over the network the first time.
    # Studies carrying no phs accession — a spec directory with no researchstudy.yaml gets a
    # placeholder id — can never match one, so rule that out before reaching for it.
    studies = sorted({record.study_id for record in records.values() if record.study_id})
    if cohort_key is None and not any(_PHS_RE.search(study) for study in studies):
        typer.echo("No study accession in these specs; descriptive slots will be empty", err=True)
        return None

    cohorts = load_cohorts(cache_dir=cache_dir)
    if cohort_key is not None:
        cohort = cohorts.get(cohort_key)
        if cohort is None:
            typer.echo(f"Unknown cohort '{cohort_key}'. Available: {', '.join(sorted(cohorts))}", err=True)
            raise typer.Exit(code=2)
    else:
        cohort = next((found for study in studies if (found := cohort_for_study(study, cohorts))), None)
        if cohort is None:
            typer.echo("No dbGaP cohort matches these specs; descriptive slots will be empty", err=True)
            return None
        typer.echo(f"Using dbGaP cohort {cohort.key} ({cohort.study_id}.{cohort.data_version})", err=True)

    datasets = {record.sole_dataset() for record in records.values()}
    kinds = None if with_var_report else frozenset({"data_dict"})
    if fetch:
        digests = fetch_digests(cohort, cache_root=cache_dir, refresh=refresh, datasets=datasets, kinds=kinds)
    else:
        digests = cached_digests(cohort, cache_dir, datasets=datasets, kinds=kinds)

    found = {pht for path in digests.data_dicts if (pht := _pht_of(path.name))}
    if missing := datasets - found:
        typer.echo(
            f"{len(missing)} of {len(datasets)} datasets have no dbGaP data dictionary: {', '.join(sorted(missing))}",
            err=True,
        )
    return metadata_for(digests, classify, with_var_report=with_var_report)


def _pht_of(filename):
    """Return the bare pht in a digest filename, deferring the import for CLI startup speed."""
    from dm_bip.prepare_study.fetch_digests import pht_from_filename

    return pht_from_filename(filename)


@app.command()
def extract_variable_library(
    paths: Annotated[list[Path], typer.Argument(exists=True, help="Transformation spec files or directories")],
    source_schema: Annotated[
        Optional[Path],
        typer.Option("--source-schema", "-s", exists=True, help="schema-automator output, used to type each variable"),
    ] = None,
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Output YAML file (default: stdout)")] = None,
    cohort: Annotated[
        Optional[str],
        typer.Option("--cohort", help="dbGaP cohort key; omit to detect it from the specs' researchstudy.yaml"),
    ] = None,
    dbgap_cache: Annotated[
        Path, typer.Option("--dbgap-cache", help="Local cache directory for dbGaP digest XMLs")
    ] = Path(".dbgap-cache"),
    fetch: Annotated[
        bool, typer.Option("--fetch/--no-fetch", help="Fetch missing digests; --no-fetch uses only what is cached")
    ] = True,
    with_var_report: Annotated[
        bool,
        typer.Option("--var-report/--no-var-report", help="Use var_report.xml for data types and observed bounds"),
    ] = True,
    refresh: Annotated[bool, typer.Option("--refresh", help="Force re-fetch of cached digest files")] = False,
):
    """
    Emit BDC variable library entries for the source variables named in transformation specs.

    The specs say which variables exist and ``--source-schema`` says whether each is
    continuous or categorical. Descriptive slots — name, units, bounds, coded values — come
    from dbGaP, fetched for exactly the datasets the specs name and no others.
    """
    from dm_bip.mapping_prov.extract import collect_spec_paths
    from dm_bip.variable_lib.classify import classifier_for
    from dm_bip.variable_lib.emit import to_entries, to_yaml
    from dm_bip.variable_lib.extract import collect_variables

    spec_paths = collect_spec_paths(paths)
    if not spec_paths:
        typer.echo("No transformation spec files found", err=True)
        raise typer.Exit(code=1)

    records = collect_variables(spec_paths)
    classify = classifier_for(source_schema)
    metadata = _dbgap_metadata(records, classify, cohort, dbgap_cache, fetch, with_var_report, refresh)
    entries = to_entries(records, classify, metadata=metadata)
    serialized = to_yaml(entries)
    if output is None:
        typer.echo(serialized)
    else:
        output.write_text(serialized)
        typer.echo(f"Variable library written to {output}")

    typer.echo(
        f"{len(entries)} entries from {len(records)} source variables "
        f"({len(entries.continuous)} continuous, {len(entries.categorical)} categorical)",
        err=True,
    )
    if entries.unclassified:
        hint = "" if source_schema else " (no --source-schema supplied)"
        typer.echo(f"{len(entries.unclassified)} variables could not be typed and were skipped{hint}", err=True)


@app.command()
def apply_overrides(
    pipeline_csv: Annotated[Path, typer.Option("--input", "-i", help="Pipeline output CSV")],
    fixes_csv: Annotated[Path, typer.Option("--fixes", "-f", help="Curator fixes CSV")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Corrected output CSV")],
):
    """Apply per-row curator overrides to a prepared-metadata CSV."""
    from dm_bip.trans_spec_gen.apply_overrides import apply_curator_overrides

    result = apply_curator_overrides(pipeline_csv=pipeline_csv, fixes_csv=fixes_csv, output_csv=output)
    typer.echo(f"Corrected output written to {result}")


if __name__ == "__main__":
    app()
