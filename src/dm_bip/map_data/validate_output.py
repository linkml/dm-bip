"""
Validate mapped output against the target schema and write an advisory report.

The map step hands ``linkml-map`` a ``--target-schema``, but that schema only shapes
the transformation — nothing downstream asserts that the emitted records actually
conform to it. This module closes that gap by validating the mapped output and
summarizing what it finds.

The report is advisory: this module always exits 0, so a failing report never breaks
a pipeline run. Findings are aggregated by (entity, slot path, constraint) rather than
listed per record, because a single systematic mismatch can affect every row and a
per-record dump would be unreadable at real data volumes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin

# NB: a Validator built without plugins runs no checks at all and reports everything
# as valid. The plugin list below is what makes this validation real.
VALIDATION_PLUGINS = [JsonschemaValidationPlugin(closed=True)]

STRUCTURED_SUFFIXES = {".yaml", ".yml", ".json", ".jsonl"}

MAX_EXAMPLES_PER_ISSUE = 3


@dataclass
class Issue:
    """One aggregated conformance finding, counted across all records of an entity."""

    slot_path: str
    constraint: str
    expected: str
    count: int = 0
    examples: list[str] = field(default_factory=list)


@dataclass
class EntityReport:
    """Validation outcome for a single mapped entity file."""

    entity: str
    path: Path
    total_records: int = 0
    checked_records: int = 0
    invalid_records: int = 0
    issues: dict[tuple[str, str, str], Issue] = field(default_factory=dict)
    skipped_reason: str = ""

    @property
    def is_clean(self) -> bool:
        """True when records were actually checked and all of them conformed."""
        return self.checked_records > 0 and self.invalid_records == 0 and not self.skipped_reason


def load_records(path: Path) -> list[dict[str, Any]]:
    """
    Read mapped output into a flat list of record dicts.

    ``linkml-map`` has emitted more than one YAML shape across versions, so all are
    handled: a multi-document stream (``---`` between records), and a collection under
    a single pluralized container key (``participants:``, ``demographys:``) that the
    target schema does not define and which is stripped before validating.

    Args:
        path: Mapped output file (``.yaml``, ``.yml``, ``.json``, or ``.jsonl``).

    Returns:
        List of record dicts; empty when the file holds no records.

    """
    if path.suffix == ".jsonl":
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        return [r for r in records if isinstance(r, dict)]

    if path.suffix == ".json":
        doc = json.loads(path.read_text())
    else:
        docs = [d for d in yaml.safe_load_all(path.read_text()) if d is not None]
        if len(docs) > 1:
            # Multi-document stream: one record per document.
            return [d for d in docs if isinstance(d, dict)]
        doc = docs[0] if docs else None

    if doc is None:
        return []
    if isinstance(doc, list):
        return [r for r in doc if isinstance(r, dict)]
    if isinstance(doc, dict):
        # Single container key wrapping the collection.
        if len(doc) == 1:
            (inner,) = doc.values()
            if isinstance(inner, list):
                return [r for r in inner if isinstance(r, dict)]
        # Otherwise treat the document itself as one record.
        return [doc]
    return []


def normalize_slot_path(slot_path: str) -> str:
    """
    Collapse array indices in a JSON path so findings aggregate across list elements.

    ``$.observations[0].value`` and ``$.observations[1].value`` describe the same
    systematic problem. Without this, a multivalued slot produces one finding per
    index and the report degenerates back into a per-record dump.

    Args:
        slot_path: JSON path from the validator, e.g. ``$.observations[3].value``.

    Returns:
        Path with numeric indices replaced by ``[*]``.

    """
    return re.sub(r"\[\d+\]", "[*]", slot_path)


def issue_key(result: Any) -> tuple[str, str, str]:
    """
    Derive a stable (slot_path, constraint, expected) key for aggregating a result.

    Prefers the structured jsonschema error carried on ``result.source``; falls back to
    the human-readable message when a plugin does not supply one.

    Args:
        result: A ``ValidationResult`` from the linkml validator.

    Returns:
        Tuple identifying the kind of finding, independent of the offending value.

    """
    source = getattr(result, "source", None)
    slot_path = getattr(source, "json_path", None)
    constraint = getattr(source, "validator", None)
    expected = getattr(source, "validator_value", None)

    if slot_path is None:
        return ("<unknown>", "unknown", str(result.message))
    return (normalize_slot_path(str(slot_path)), str(constraint), str(expected))


def validate_file(entity: str, path: Path, validator: Validator, limit: int = 0) -> EntityReport:
    """
    Validate one mapped entity file against the target schema.

    Args:
        entity: Target-schema class name to validate records against.
        path: Mapped output file.
        validator: Configured linkml ``Validator``.
        limit: Maximum records to check; ``0`` checks all of them.

    Returns:
        Aggregated :class:`EntityReport` for the file.

    """
    report = EntityReport(entity=entity, path=path)

    if not path.exists():
        report.skipped_reason = "file not found"
        return report
    if path.suffix not in STRUCTURED_SUFFIXES:
        report.skipped_reason = f"unsupported format '{path.suffix}' (needs yaml, json, or jsonl)"
        return report

    records = load_records(path)
    if not records:
        # An empty output file means the map step produced nothing for this entity.
        # That is a failure signal, never a clean pass.
        report.skipped_reason = "no records in output (map step produced an empty file)"
        return report

    report.total_records = len(records)
    if limit > 0:
        records = records[:limit]
    report.checked_records = len(records)

    for record in records:
        results = list(validator.validate(record, target_class=entity).results)
        if not results:
            continue
        report.invalid_records += 1
        for result in results:
            key = issue_key(result)
            issue = report.issues.get(key)
            if issue is None:
                issue = Issue(slot_path=key[0], constraint=key[1], expected=key[2])
                report.issues[key] = issue
            issue.count += 1
            if len(issue.examples) < MAX_EXAMPLES_PER_ISSUE:
                issue.examples.append(str(result.message))

    return report


def render_report(reports: list[EntityReport], target_schema: Path, limit: int) -> str:
    """
    Render the aggregated findings as a plain-text report.

    Args:
        reports: Per-entity validation outcomes.
        target_schema: Schema the output was validated against.
        limit: Per-entity record cap that was applied (``0`` means all).

    Returns:
        The formatted report body.

    """
    lines: list[str] = []
    lines.append("Mapped Output Validation Report")
    lines.append("=" * 60)
    lines.append(f"Target schema: {target_schema}")
    lines.append(f"Record limit:  {limit if limit > 0 else 'none (all records)'}")
    lines.append("")
    lines.append("This report is advisory and does not fail the pipeline.")
    lines.append("")

    total_checked = sum(r.checked_records for r in reports)
    total_invalid = sum(r.invalid_records for r in reports)

    lines.append("Summary")
    lines.append("-" * 60)
    for report in reports:
        if report.skipped_reason:
            lines.append(f"  {report.entity:<32} SKIPPED — {report.skipped_reason}")
            continue
        pct = (report.invalid_records / report.checked_records * 100) if report.checked_records else 0.0
        status = "ok" if report.is_clean else "FAIL"
        lines.append(
            f"  {report.entity:<32} {report.checked_records:>7} checked  "
            f"{report.invalid_records:>7} invalid ({pct:5.1f}%)  [{status}]"
        )
    lines.append("")
    overall = (total_invalid / total_checked * 100) if total_checked else 0.0
    lines.append(f"  {'TOTAL':<32} {total_checked:>7} checked  {total_invalid:>7} invalid ({overall:5.1f}%)")
    lines.append("")

    reports_with_issues = [r for r in reports if r.issues]
    if not reports_with_issues:
        lines.append("No conformance issues found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("Findings by entity")
    lines.append("-" * 60)
    for report in reports_with_issues:
        lines.append(f"{report.entity}  ({report.path})")
        for issue in sorted(report.issues.values(), key=lambda i: i.count, reverse=True):
            lines.append(f"    {issue.count:>7}x  {issue.slot_path}  [{issue.constraint}: expected {issue.expected}]")
            for example in issue.examples:
                lines.append(f"             e.g. {example}")
        lines.append("")

    return "\n".join(lines)


def read_entity_list(path: Path) -> list[str]:
    """
    Read entity names from the list written by the map step.

    Args:
        path: File holding one entity name per line.

    Returns:
        Entity names, or ``[]`` when the file is missing or empty.

    """
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def entity_output_path(mapped_dir: Path, entity: str, prefix: str = "", postfix: str = "", fmt: str = "yaml") -> Path:
    """
    Rebuild the mapped output path for an entity.

    Mirrors the ``_map_base`` function in ``pipeline.Makefile``, which names outputs
    ``{prefix}-{entity}-{postfix}.{fmt}`` while omitting empty parts.

    Args:
        mapped_dir: Directory holding mapped output.
        entity: Entity (target class) name.
        prefix: Optional filename prefix.
        postfix: Optional filename postfix.
        fmt: Output format suffix.

    Returns:
        Path to the entity's mapped output file.

    """
    parts = [part for part in (prefix, entity, postfix) if part]
    return mapped_dir / f"{'-'.join(parts)}.{fmt}"


def _emit(body: str, report_path: Path | None) -> None:
    """Write the report to ``report_path``, or to stdout when no path is given."""
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(body)
        print(f"Output validation report written to {report_path}")
    else:
        print(body)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Always returns 0 — this validation is advisory."""
    parser = argparse.ArgumentParser(
        prog="validate_output",
        description="Validate mapped output against the target schema (advisory; never fails).",
    )
    parser.add_argument("--target-schema", required=True, type=Path, help="Target schema to validate against")
    parser.add_argument("--mapped-dir", required=True, type=Path, help="Directory holding mapped output")
    parser.add_argument("--entity-list", required=True, type=Path, help="File listing one entity name per line")
    parser.add_argument("--prefix", default="", help="Mapped output filename prefix")
    parser.add_argument("--postfix", default="", help="Mapped output filename postfix")
    parser.add_argument("--format", default="yaml", help="Mapped output format suffix (default: yaml)")
    parser.add_argument("--report", type=Path, help="Write the report here (default: stdout)")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max records to check per entity (0 = all). Use to bound runtime on large datasets.",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    # Skips still emit a report, so the reason is recorded and Make sees the target built.
    skip_reason = ""
    if not str(args.target_schema):
        skip_reason = "No target schema configured (DM_MAP_TARGET_SCHEMA is unset)."
    elif not args.target_schema.exists():
        skip_reason = f"Target schema not found: {args.target_schema}"

    entities = [] if skip_reason else read_entity_list(args.entity_list)
    if not skip_reason and not entities:
        skip_reason = f"No entities listed in {args.entity_list}"

    if skip_reason:
        body = f"Mapped Output Validation Report\n{'=' * 60}\nSkipped — {skip_reason}\n"
        _emit(body, args.report)
        return 0

    validator = Validator(str(args.target_schema), validation_plugins=VALIDATION_PLUGINS)

    reports = []
    for entity in entities:
        path = entity_output_path(args.mapped_dir, entity, args.prefix, args.postfix, args.format)
        try:
            reports.append(validate_file(entity, path, validator, limit=args.limit))
        except Exception as exc:  # noqa: BLE001 - advisory: one bad file must not stop the report
            failed = EntityReport(entity=entity, path=path)
            failed.skipped_reason = f"{type(exc).__name__}: {exc}"
            reports.append(failed)

    _emit(render_report(reports, args.target_schema, args.limit), args.report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
