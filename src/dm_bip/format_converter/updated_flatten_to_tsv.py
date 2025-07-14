"""
Flatten LinkML YAML data into TSV files.

This script loads a LinkML model and a YAML instance file, flattens the data,
and outputs TSV files for each top-level class.
"""

import argparse
import itertools
import json
from pathlib import Path

import pandas as pd
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import YAMLRoot


def flatten_dict(d, parent_key="", sep="__"):
    """Flatten dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def explode_rows(flat_records, list_keys):
    """Explode nested values to additional rows."""
    exploded = []
    for record in flat_records:
        lists = {k: v for k, v in record.items() if k in list_keys and isinstance(v, list)}
        if not lists:
            exploded.append(record)
            continue
        keys, values = zip(*lists.items(), strict=False)
        for combo in itertools.product(*values):
            new_record = record.copy()
            for k, v in zip(keys, combo, strict=False):
                if isinstance(v, dict):
                    new_record[k] = json.dumps(v, separators=(",", ":"))
                else:
                    new_record[k] = v
            exploded.append({k: v for k, v in new_record.items() if not isinstance(v, list)})
    return exploded


def join_lists(records, list_keys, join_str=","):
    """Join lists."""
    for record in records:
        for k in list_keys:
            value = record.get(k)
            if isinstance(value, list):
                record[k] = join_str.join(
                    json.dumps(item, separators=(",", ":")) if isinstance(item, dict) else str(item) for item in value
                )
    return records


def get_slot_order(schemaview: SchemaView, class_name: str):
    """Get the slot order from the model."""
    cls = schemaview.get_class(class_name)
    if not cls:
        raise ValueError(f"Class {class_name} not found in schema")
    return schemaview.class_slots(cls.name)


def get_scalar_slots(sv: SchemaView, class_name: str, instance_class_names: set):
    """
    Get the scalar slot names for a class.

    Args:
        sv: The LinkML schema view.
        class_name: The name of the class to inspect.
        instance_class_names: Set of all class names found in the instance data.

    Returns:
        A list of slot names that are scalar fields for the given class.

    Notes:
        Scalar slots are those whose ranges are not other collected classes.
        They usually include strings, numbers, enums, or dates.

    """
    scalar_slots = []
    print("\n\n")
    for slot_name in sv.class_slots(class_name, attributes=True):
        slot = sv.get_slot(slot_name)
        if slot is None:
            continue
        # Exclude links to other classes that are collected as their own files
        if slot.range in instance_class_names and not slot.inlined:
            continue
        scalar_slots.append(slot.name)
    print(f"Scalar slots for {class_name}: {scalar_slots}")
    return scalar_slots


def get_reference_slots(
    schemaview: SchemaView,
    class_name: str,
    instance_class_names,
    container_key=None,
    container_class=None,
    scalar_slots=None,
):
    """
    Identify reference-type slots for a given class.

    Args:
        schemaview: The LinkML schema view.
        class_name: The class to inspect.
        instance_class_names: The set of class names found in the instance data.
        container_key: Not currently used, reserved for future logic.
        container_class: Not currently used, reserved for future logic.
        scalar_slots: List of known scalar slots to exclude from reference detection.

    Returns:
        A list of slot names that should be treated as scalar references to other classes.

    """
    scalar_slots = set(scalar_slots or [])
    reference_slots = []

    for slot_name in schemaview.class_slots(class_name, attributes=True):
        if slot_name in scalar_slots:
            continue

        slot = schemaview.get_slot(slot_name)
        if not slot:
            continue

        # Reference to another class but not embedded (i.e., inlined=False)
        if slot.range in instance_class_names and not slot.inlined and not slot.multivalued:
            reference_slots.append(slot.name)

        # Also include if it refers to a class that is NOT included in our flattened output
        elif slot.range not in instance_class_names and slot.range in schemaview.all_classes():
            reference_slots.append(slot.name)

    return reference_slots


def collect_instances_by_class(instance_data, container_key, container_class, sv):
    """Collect instances of all schema-defined classes starting from the container."""
    container_data = instance_data.get(container_key, [])
    if not isinstance(container_data, list):
        raise ValueError(f"Expected a list for container key '{container_key}', got {type(container_data)}")

    collected = {}

    def recurse(obj, expected_class):
        if isinstance(obj, dict):
            collected.setdefault(expected_class, []).append(obj)
            # Recurse into child objects based on schema-defined slots
            for slot_name in sv.class_slots(expected_class):
                slot = sv.induced_slot(slot_name, expected_class)
                value = obj.get(slot.name)
                if value is None:
                    continue
                if slot.range in sv.all_classes():
                    if isinstance(value, list):
                        for item in value:
                            recurse(item, slot.range)
                    elif isinstance(value, dict):
                        recurse(value, slot.range)

    for top_level_obj in container_data:
        recurse(top_level_obj, container_class)

    print(f"\nCollected instances for classes: {list(collected.keys())}")
    return collected


def main():
    """Flatten linkml file to multiple TSV files, one for each model class in the data."""
    parser = argparse.ArgumentParser(description="Flatten all top-level classes in LinkML data to TSV")
    parser.add_argument("schema", help="Path to LinkML schema (YAML)")
    parser.add_argument("input", help="Input YAML instance file")
    parser.add_argument("output_dir", help="Output directory for TSV files")
    parser.add_argument("--container-key", required=True, help="Top-level key in instance data (e.g., 'persons')")
    parser.add_argument("--container-class", required=True, help="Class name for the top-level key (e.g., 'Person')")
    parser.add_argument("--mode", choices=["wide", "per-class"], default="per-class", help="Output mode")
    parser.add_argument("--list-style", choices=["join", "explode"], default="join", help="How to handle list values")
    args = parser.parse_args()

    sv = SchemaView(args.schema)
    with open(args.input) as f:
        data = yaml.safe_load(f)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    if args.mode == "wide":
        raise NotImplementedError("Only per-class mode is supported in this version.")
    else:
        instances_by_class = collect_instances_by_class(data, args.container_key, args.container_class, sv)

        for class_name, records in instances_by_class.items():
            scalar_slots = get_scalar_slots(sv, class_name, instances_by_class.keys())
            print(f"{class_name} scalar slots: {scalar_slots}")

            ref_slots = get_reference_slots(
                sv, class_name, instances_by_class.keys(), args.container_key, args.container_class, scalar_slots
            )
            print(f"{class_name} reference slots: {ref_slots}")

            flat_records = []
            list_fields = set()

            for inst in records:
                raw = inst.dict(exclude_unset=True) if isinstance(inst, YAMLRoot) else inst
                flat = flatten_dict(raw)
                print(f"Flattened keys for class {class_name}: {list(flat.keys())}")

                # Get all slots for the class
                all_slots = sv.class_slots(class_name, attributes=True)

                # Determine which slots represent nested classes and should be excluded
                excluded_nested_slots = {
                    s
                    for s in all_slots
                    if (
                        (slot := sv.get_slot(s))
                        and slot.range in instances_by_class.keys()
                        and not slot.inlined  # Only exclude if NOT inlined
                        and s not in ref_slots
                    )
                }
                print(f"Excluding nested class slots for {class_name}: {excluded_nested_slots}")

                # Filter flattened keys: include scalar and reference slots and all inlined subfields, exclude nested class slots
                filtered = {
                    k: v
                    for k, v in flat.items()
                    if (
                        any(k == s or k.startswith(f"{s}__") for s in scalar_slots + ref_slots)
                        and not any(k == s or k.startswith(f"{s}__") for s in excluded_nested_slots)
                    )
                }
                print(f"Filtered: {filtered}")

                for k, v in filtered.items():
                    if isinstance(v, list):
                        list_fields.add(k)
                flat_records.append(filtered)

            if args.list_style == "explode":
                flat_records = explode_rows(flat_records, list_fields)
            else:
                flat_records = join_lists(flat_records, list_fields)

            df = pd.DataFrame(flat_records)
            print(f"{class_name} columns in output: {df.columns.tolist()}")

            slot_order = [s for s in scalar_slots if s in df.columns]
            extra_cols = [c for c in df.columns if c not in slot_order]
            df = df[slot_order + extra_cols]

            out_path = Path(args.output_dir) / f"{class_name}.tsv"
            df.to_csv(out_path, sep="\t", index=False)
            print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
