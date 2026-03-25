"""
Generate enum_derivations specs from value_mappings and inferred source enums.

Reads a source schema (with inferred enums), existing transformation specs
(with value_mappings), and a target schema, then generates:
1. New spec files with enum_derivations replacing value_mappings
2. A new target schema with enum definitions added

See issue-211-planning.md for the full algorithm description.
"""

import copy
import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
import yaml
from linkml_runtime import SchemaView

logger = logging.getLogger(__name__)


@dataclass
class ValueMappingInfo:
    """A value_mapping found in a spec block, with context for comment generation."""

    source_slot: str
    target_slot: str
    target_class: str
    mapping: dict[str, str]  # {source_val: target_val}
    nesting_path: str  # e.g., "Demography.sex" or "MeasurementObservation.value_quantity→Quantity.value_concept"
    spec_file: str
    block_index: int


@dataclass
class TargetEnumInfo:
    """A deduplicated target enum to be added to the target schema."""

    name: str
    permissible_values: list[str]
    source_slots: list[str] = field(default_factory=list)
    nesting_paths: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 1: Parse source schema
# ---------------------------------------------------------------------------


def parse_source_schema(schema_path: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    """
    Build slot_to_enum and enum_pvs maps from the source schema.

    Returns:
        slot_to_enum: slot_name → enum_name (e.g., "phv00000002" → "phv00000002_enum")
        enum_pvs: enum_name → list of permissible value texts

    """
    sv = SchemaView(str(schema_path))
    slot_to_enum: dict[str, str] = {}
    enum_pvs: dict[str, list[str]] = {}

    for enum_name, enum_def in sv.all_enums().items():
        enum_pvs[str(enum_name)] = [str(pv) for pv in enum_def.permissible_values]

    for slot_name, slot_def in sv.all_slots().items():
        range_str = str(slot_def.range) if slot_def.range else None
        if range_str and range_str in enum_pvs:
            slot_to_enum[str(slot_name)] = range_str

    return slot_to_enum, enum_pvs


# ---------------------------------------------------------------------------
# Step 2: Collect all value_mappings from specs
# ---------------------------------------------------------------------------


def _walk_class_derivations(
    class_derivations: dict,
    *,
    spec_file: str,
    block_index: int,
    parent_path: str = "",
) -> list[ValueMappingInfo]:
    """Recursively walk class_derivations (including nested object_derivations)."""
    results: list[ValueMappingInfo] = []

    for class_name, class_spec in class_derivations.items():
        slot_derivations = class_spec.get("slot_derivations", {})
        for slot_name, slot_spec in slot_derivations.items():
            if not isinstance(slot_spec, dict):
                continue

            segment = f"{class_name}.{slot_name}"
            path = segment if not parent_path else f"{parent_path}→{segment}"

            if "value_mappings" in slot_spec and "populated_from" in slot_spec:
                mapping = {str(k): str(v) for k, v in slot_spec["value_mappings"].items()}
                results.append(
                    ValueMappingInfo(
                        source_slot=slot_spec["populated_from"],
                        target_slot=slot_name,
                        target_class=class_name,
                        mapping=mapping,
                        nesting_path=path,
                        spec_file=spec_file,
                        block_index=block_index,
                    )
                )

            # Recurse into object_derivations
            obj_derivs = slot_spec.get("object_derivations")
            if isinstance(obj_derivs, list):
                for obj_deriv in obj_derivs:
                    nested_cd = obj_deriv.get("class_derivations", {})
                    results.extend(
                        _walk_class_derivations(
                            nested_cd,
                            spec_file=spec_file,
                            block_index=block_index,
                            parent_path=path,
                        )
                    )

    return results


def collect_value_mappings(spec_dir: Path) -> tuple[list[ValueMappingInfo], dict[str, list[dict]]]:
    """
    Collect all value_mappings from spec files and return the parsed specs.

    Returns:
        all_mappings: list of ValueMappingInfo
        specs_by_file: filename → list of parsed YAML blocks

    """
    all_mappings: list[ValueMappingInfo] = []
    specs_by_file: dict[str, list[dict]] = {}

    yaml_files = sorted(spec_dir.glob("*.yaml"))
    for yaml_file in yaml_files:
        with open(yaml_file) as f:
            specs = yaml.safe_load(f)
        if not isinstance(specs, list):
            continue
        specs_by_file[yaml_file.name] = specs
        for block_index, block in enumerate(specs):
            cd = block.get("class_derivations", {})
            all_mappings.extend(
                _walk_class_derivations(
                    cd,
                    spec_file=yaml_file.name,
                    block_index=block_index,
                )
            )

    return all_mappings, specs_by_file


# ---------------------------------------------------------------------------
# Step 2 supplement: Collect all populated_from slots across specs
# ---------------------------------------------------------------------------


def _collect_populated_from_slots(specs_by_file: dict[str, list[dict]]) -> set[str]:
    """Walk all specs and collect every slot name used in populated_from."""
    slots: set[str] = set()

    def _walk(class_derivations: dict) -> None:
        for _class_name, class_spec in class_derivations.items():
            if isinstance(class_spec, dict) and "populated_from" in class_spec:
                # This is the class-level populated_from (pht ID), not a slot
                pass
            for _slot_name, slot_spec in class_spec.get("slot_derivations", {}).items():
                if not isinstance(slot_spec, dict):
                    continue
                if "populated_from" in slot_spec:
                    slots.add(slot_spec["populated_from"])
                obj_derivs = slot_spec.get("object_derivations")
                if isinstance(obj_derivs, list):
                    for obj_deriv in obj_derivs:
                        _walk(obj_deriv.get("class_derivations", {}))

    for specs in specs_by_file.values():
        for block in specs:
            _walk(block.get("class_derivations", {}))

    return slots


# ---------------------------------------------------------------------------
# Step 3: Deduplicate and name target enums
# ---------------------------------------------------------------------------


def deduplicate_and_name_enums(
    all_mappings: list[ValueMappingInfo],
    target_sv: SchemaView,
) -> tuple[dict[str, TargetEnumInfo], dict[tuple[str, int], dict[str, str]]]:
    """
    Deduplicate value_mappings and assign target enum names.

    Returns:
        target_enums: enum_name → TargetEnumInfo
        block_enum_assignments: (spec_file, block_index) → {source_slot: target_enum_name}

    """
    # Group by target_slot to detect collisions
    by_target_slot: dict[str, list[ValueMappingInfo]] = defaultdict(list)
    for vm in all_mappings:
        by_target_slot[vm.target_slot].append(vm)

    # For each target_slot, find distinct mappings
    target_enums: dict[str, TargetEnumInfo] = {}
    # Maps mapping content (as frozen json) → assigned enum name
    content_to_name: dict[str, str] = {}
    block_enum_assignments: dict[tuple[str, int], dict[str, str]] = defaultdict(dict)

    for target_slot, vms in by_target_slot.items():
        # Group by mapping content
        by_content: dict[str, list[ValueMappingInfo]] = defaultdict(list)
        for vm in vms:
            key = json.dumps(vm.mapping, sort_keys=True)
            by_content[key].append(vm)

        # Check if target schema already defines an enum on this slot
        existing_enum = None
        for vm in vms:
            slot_def = target_sv.get_slot(target_slot)
            if slot_def and slot_def.range:
                enum_def = target_sv.get_enum(slot_def.range)
                if enum_def:
                    existing_enum = slot_def.range
                    break
            # Also check class attributes
            class_def = target_sv.get_class(vm.target_class)
            if class_def and target_slot in (class_def.attributes or {}):
                attr = class_def.attributes[target_slot]
                if attr.range:
                    enum_def = target_sv.get_enum(attr.range)
                    if enum_def:
                        existing_enum = attr.range
                        break

        needs_disambiguation = len(by_content) > 1

        for content_key, content_vms in by_content.items():
            # Check if we already assigned a name for this exact mapping content
            if content_key in content_to_name:
                enum_name = content_to_name[content_key]
            elif existing_enum and not needs_disambiguation:
                enum_name = existing_enum
                content_to_name[content_key] = enum_name
            elif needs_disambiguation:
                # Use source slot for disambiguation
                source_slot = content_vms[0].source_slot
                enum_name = f"{target_slot}_{source_slot}_enum"
                content_to_name[content_key] = enum_name
            else:
                enum_name = f"{target_slot}_enum"
                content_to_name[content_key] = enum_name

            if enum_name not in target_enums:
                mapping = content_vms[0].mapping
                target_enums[enum_name] = TargetEnumInfo(
                    name=enum_name,
                    permissible_values=[v for v in mapping.values() if v != "None"],
                    source_slots=[vm.source_slot for vm in content_vms],
                    nesting_paths=[vm.nesting_path for vm in content_vms],
                )
            else:
                # Add additional source slots / paths
                for vm in content_vms:
                    if vm.source_slot not in target_enums[enum_name].source_slots:
                        target_enums[enum_name].source_slots.append(vm.source_slot)
                    if vm.nesting_path not in target_enums[enum_name].nesting_paths:
                        target_enums[enum_name].nesting_paths.append(vm.nesting_path)

            for vm in content_vms:
                block_enum_assignments[(vm.spec_file, vm.block_index)][vm.source_slot] = enum_name

    return target_enums, block_enum_assignments


# ---------------------------------------------------------------------------
# Step 4: Generate target schema with enums
# ---------------------------------------------------------------------------


def generate_target_schema(
    target_schema_path: Path,
    target_enums: dict[str, TargetEnumInfo],
    all_mappings: list[ValueMappingInfo],
    output_path: Path,
) -> None:
    """Write a new target schema with enum definitions and range annotations added."""
    with open(target_schema_path) as f:
        schema = yaml.safe_load(f)

    # Add enums section
    if "enums" not in schema:
        schema["enums"] = {}

    for enum_name, enum_info in sorted(target_enums.items()):
        schema["enums"][enum_name] = {
            "permissible_values": {pv: {} for pv in enum_info.permissible_values},
        }

    # Add range annotations on target slots
    # Build mapping: (target_class, target_slot) → set of enum_names
    slot_enum_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for vm in all_mappings:
        for enum_name, enum_info in target_enums.items():
            if vm.source_slot in enum_info.source_slots:
                slot_enum_map[(vm.target_class, vm.target_slot)].add(enum_name)
                break

    for (target_class, target_slot), enum_names in slot_enum_map.items():
        if len(enum_names) > 1:
            # Multiple distinct enums map to the same slot — can't assign a single range
            logger.warning(
                "Slot %s.%s has %d distinct enum mappings — skipping range assignment",
                target_class,
                target_slot,
                len(enum_names),
            )
            continue
        enum_name = next(iter(enum_names))
        classes = schema.get("classes", {})
        class_def = classes.get(target_class, {})
        attrs = class_def.get("attributes", {})
        if target_slot in attrs:
            attr = attrs[target_slot]
            if isinstance(attr, dict):
                attr["range"] = enum_name
            elif attr is None:
                attrs[target_slot] = {"range": enum_name}

    os.makedirs(output_path.parent, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(schema, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    logger.info("Wrote target schema with %d enums to %s", len(target_enums), output_path)


# ---------------------------------------------------------------------------
# Step 5: Generate new specs with enum_derivations
# ---------------------------------------------------------------------------


def _build_enum_derivation(
    source_enum_name: str,
    target_enum_name: str,
    mapping: dict[str, str],
    nesting_path: str,
    source_pvs: list[str],
) -> dict:
    """Build a single enum_derivation dict."""
    pv_derivations = {}
    for source_val, target_val in mapping.items():
        if target_val == "None":
            continue
        pv_derivations[target_val] = {"populated_from": str(source_val)}

    return {
        "_comment": f"{nesting_path} — source permissible values: {', '.join(repr(pv) for pv in source_pvs)}",
        target_enum_name: {
            "populated_from": source_enum_name,
            "mirror_source": False,
            "permissible_value_derivations": pv_derivations,
        },
    }


def _remove_value_mappings(block: dict) -> dict:
    """Deep-copy a block, removing value_mappings from all slot_derivations (including nested)."""
    block = copy.deepcopy(block)

    def _strip(class_derivations: dict) -> None:
        for _class_name, class_spec in class_derivations.items():
            for _slot_name, slot_spec in class_spec.get("slot_derivations", {}).items():
                if not isinstance(slot_spec, dict):
                    continue
                slot_spec.pop("value_mappings", None)
                obj_derivs = slot_spec.get("object_derivations")
                if isinstance(obj_derivs, list):
                    for obj_deriv in obj_derivs:
                        _strip(obj_deriv.get("class_derivations", {}))

    _strip(block.get("class_derivations", {}))
    return block


def generate_specs(
    specs_by_file: dict[str, list[dict]],
    all_mappings: list[ValueMappingInfo],
    block_enum_assignments: dict[tuple[str, int], dict[str, str]],
    slot_to_enum: dict[str, str],
    enum_pvs: dict[str, list[str]],
    all_populated_from_slots: set[str],
    output_dir: Path,
) -> None:
    """Write new spec files with enum_derivations replacing value_mappings."""
    os.makedirs(output_dir, exist_ok=True)

    # Index mappings by (file, block_index) for lookup
    mappings_index: dict[tuple[str, int], list[ValueMappingInfo]] = defaultdict(list)
    for vm in all_mappings:
        mappings_index[(vm.spec_file, vm.block_index)].append(vm)

    # Collect all source slots that have value_mappings (across all specs)
    slots_with_value_mappings = {vm.source_slot for vm in all_mappings}

    for filename, blocks in sorted(specs_by_file.items()):
        new_blocks = []
        for block_index, block in enumerate(blocks):
            key = (filename, block_index)
            vms = mappings_index.get(key, [])

            if not vms:
                # No value_mappings in this block — check for passthrough enums
                new_block = copy.deepcopy(block)
                passthrough_derivations = _find_passthrough_enums(
                    block, slot_to_enum, enum_pvs, slots_with_value_mappings
                )
                if passthrough_derivations:
                    new_block["enum_derivations"] = passthrough_derivations
                new_blocks.append(new_block)
                continue

            # Remove value_mappings from the block
            new_block = _remove_value_mappings(block)

            # Build enum_derivations for this block
            enum_derivations = {}
            assignments = block_enum_assignments.get(key, {})

            for vm in vms:
                target_enum_name = assignments.get(vm.source_slot)
                if not target_enum_name:
                    continue

                source_enum_name = slot_to_enum.get(vm.source_slot)
                if not source_enum_name:
                    # Edge case: no source enum — leave value_mappings in place
                    logger.warning(
                        "No source enum for slot %s in %s block %d — leaving value_mappings",
                        vm.source_slot,
                        filename,
                        block_index,
                    )
                    # Restore value_mappings for this slot
                    _restore_value_mapping(new_block, vm)
                    continue

                source_pvs = enum_pvs.get(source_enum_name, [])
                derivation = _build_enum_derivation(
                    source_enum_name, target_enum_name, vm.mapping, vm.nesting_path, source_pvs
                )
                # Extract comment and derivation content
                comment = derivation.pop("_comment")
                for deriv_name, deriv_content in derivation.items():
                    enum_derivations[deriv_name] = deriv_content
                    enum_derivations[deriv_name]["_comment"] = comment

            # Also check for passthrough enums in this block
            passthrough = _find_passthrough_enums(block, slot_to_enum, enum_pvs, slots_with_value_mappings)
            enum_derivations.update(passthrough)

            if enum_derivations:
                new_block["enum_derivations"] = enum_derivations

            new_blocks.append(new_block)

        # Write output spec file
        output_path = output_dir / filename
        _write_spec_with_comments(output_path, new_blocks)
        logger.info("Wrote %s", output_path)


def _find_passthrough_enums(
    block: dict,
    slot_to_enum: dict[str, str],
    enum_pvs: dict[str, list[str]],
    slots_with_value_mappings: set[str],
) -> dict:
    """Find source enum slots used in populated_from but without value_mappings."""
    passthrough: dict = {}

    def _walk(class_derivations: dict) -> None:
        for _class_name, class_spec in class_derivations.items():
            for _slot_name, slot_spec in class_spec.get("slot_derivations", {}).items():
                if not isinstance(slot_spec, dict):
                    continue
                source_slot = slot_spec.get("populated_from")
                if not source_slot:
                    continue
                # Skip if this slot has a value_mapping (handled elsewhere)
                if "value_mappings" in slot_spec:
                    continue
                # Skip if this slot has value_mappings in other blocks
                if source_slot in slots_with_value_mappings:
                    continue
                source_enum = slot_to_enum.get(source_slot)
                if source_enum:
                    pvs = enum_pvs.get(source_enum, [])
                    pv_str = ", ".join(repr(pv) for pv in pvs)
                    passthrough[source_enum] = {
                        "populated_from": source_enum,
                        "mirror_source": True,
                        "_comment": f"CURATOR: Source permissible values: {pv_str}. Should these be mapped?",
                    }
                    logger.info(
                        "Passthrough enum %s (slot %s) — permissible values: %s",
                        source_enum,
                        source_slot,
                        pv_str,
                    )
                    # Recurse into object_derivations
                obj_derivs = slot_spec.get("object_derivations")
                if isinstance(obj_derivs, list):
                    for obj_deriv in obj_derivs:
                        _walk(obj_deriv.get("class_derivations", {}))

    _walk(block.get("class_derivations", {}))
    return passthrough


def _restore_value_mapping(block: dict, vm: ValueMappingInfo) -> None:
    """Restore a value_mapping that was stripped, for edge case handling."""
    parts = vm.nesting_path.split("→")

    def _find_slot(class_derivations: dict, remaining_parts: list[str]) -> None:
        part = remaining_parts[0]
        class_name, slot_name = part.rsplit(".", 1)
        class_spec = class_derivations.get(class_name, {})
        slot_spec = class_spec.get("slot_derivations", {}).get(slot_name, {})

        if len(remaining_parts) == 1:
            slot_spec["value_mappings"] = vm.mapping
        else:
            obj_derivs = slot_spec.get("object_derivations", [])
            for obj_deriv in obj_derivs:
                _find_slot(obj_deriv.get("class_derivations", {}), remaining_parts[1:])

    _find_slot(block.get("class_derivations", {}), parts)


# ---------------------------------------------------------------------------
# YAML writing with comments
# ---------------------------------------------------------------------------


def _write_spec_with_comments(output_path: Path, blocks: list[dict]) -> None:
    """Write spec blocks to YAML, injecting _comment fields as YAML comments."""
    lines: list[str] = []

    for block in blocks:
        # Separate enum_derivations for special handling
        enum_derivations = block.pop("enum_derivations", None)

        # Dump the main block (class_derivations etc.)
        block_yaml = yaml.dump(
            [block], default_flow_style=False, sort_keys=False, allow_unicode=True
        )
        lines.append(block_yaml.rstrip())

        # Add enum_derivations with comments
        if enum_derivations:
            lines.append("  enum_derivations:")
            for enum_name, enum_content in enum_derivations.items():
                comment = enum_content.pop("_comment", None)
                if comment:
                    lines.append(f"    # {comment}")
                enum_yaml = yaml.dump(
                    {enum_name: enum_content},
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )
                # Indent to fit under enum_derivations
                for line in enum_yaml.rstrip().split("\n"):
                    lines.append(f"    {line}")

        lines.append("")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Step 6: Handle unreferenced enums
# ---------------------------------------------------------------------------


def report_unreferenced_enums(
    slot_to_enum: dict[str, str],
    all_populated_from_slots: set[str],
) -> None:
    """Log source enums whose slot doesn't appear in any spec."""
    for slot_name, enum_name in sorted(slot_to_enum.items()):
        if slot_name not in all_populated_from_slots:
            logger.info("NOTE: Source enum %s (slot %s) not referenced in any spec", enum_name, slot_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(
    source_schema: Annotated[
        Path,
        typer.Option(exists=True, file_okay=True, dir_okay=False, help="Source schema with inferred enums"),
    ],
    spec_dir: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False, dir_okay=True, help="Existing spec directory (with value_mappings)"),
    ],
    target_schema: Annotated[
        Path,
        typer.Option(exists=True, file_okay=True, dir_okay=False, help="Existing target schema"),
    ],
    output_spec_dir: Annotated[
        Path,
        typer.Option(file_okay=False, dir_okay=True, help="Output directory for generated specs"),
    ],
    output_target_schema: Annotated[
        Path,
        typer.Option(file_okay=True, dir_okay=False, help="Output path for target schema with enums"),
    ],
) -> None:
    """Generate enum_derivations specs from value_mappings and inferred source enums."""
    # Step 1: Parse source schema
    slot_to_enum, enum_pvs = parse_source_schema(source_schema)
    logger.info("Source schema: %d enum slots, %d enums", len(slot_to_enum), len(enum_pvs))

    # Step 2: Collect value_mappings
    all_mappings, specs_by_file = collect_value_mappings(spec_dir)
    logger.info("Found %d value_mappings across %d spec files", len(all_mappings), len(specs_by_file))

    all_populated_from_slots = _collect_populated_from_slots(specs_by_file)

    # Step 3: Deduplicate and name target enums
    target_sv = SchemaView(str(target_schema))
    target_enums, block_enum_assignments = deduplicate_and_name_enums(all_mappings, target_sv)
    logger.info("Generated %d target enums", len(target_enums))
    for name, info in sorted(target_enums.items()):
        logger.info("  %s — %d permissible values, sources: %s", name, len(info.permissible_values), info.source_slots)

    # Step 4: Generate target schema with enums
    generate_target_schema(target_schema, target_enums, all_mappings, output_target_schema)

    # Step 5: Generate specs with enum_derivations
    generate_specs(
        specs_by_file,
        all_mappings,
        block_enum_assignments,
        slot_to_enum,
        enum_pvs,
        all_populated_from_slots,
        output_spec_dir,
    )

    # Step 6: Report unreferenced enums
    report_unreferenced_enums(slot_to_enum, all_populated_from_slots)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    typer.run(main)
