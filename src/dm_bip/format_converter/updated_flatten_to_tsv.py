"""
Flatten LinkML YAML data into TSV files.

This script loads a LinkML model and a YAML instance file, flattens the data,
and outputs TSV files for each top-level class or as a single wide table.
Optionally uses a mapping file to resolve class names from YAML keys.
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

def extract_mapping_class_derivations(mapping_data):
    """Build a dict mapping top-level keys in YAML to their corresponding class names from the mapping file."""
    class_map = {}

    def recurse(node, current_key=None):
        if isinstance(node, dict):
            for key, val in node.items():
                if key == "class_derivations" and isinstance(val, dict):
                    for cls_name in val:
                        if current_key:
                            class_map[current_key] = cls_name
                        else:
                            # top-level class
                            class_map[cls_name] = cls_name
                        # recurse into class content to catch nested mappings
                        recurse(val[cls_name], current_key)
                elif key == "object_derivations" and isinstance(val, list):
                    for item in val:
                        recurse(item, current_key)
                else:
                    recurse(val, key)
        elif isinstance(node, list):
            for item in node:
                recurse(item, current_key)

    recurse(mapping_data)
    print(f'class_map: {class_map}')
    return class_map



def collect_instances_by_class(data, class_instances, schema_classes, mapping=None, parent_class=None):
    if isinstance(data, dict):
        for key, value in data.items():
            mapped_class_name = mapping.get(key) if mapping else None
            class_key = key.lower().rstrip("s").replace("_", "")
            class_name = mapped_class_name or schema_classes.get(class_key)
            if class_name is None and mapping:
                class_name = mapping.get(key.rstrip("s"))
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        effective_class_name = mapped_class_name or schema_classes.get(key.lower().rstrip("s").replace("_", ""))
                        if effective_class_name:
                            class_instances.setdefault(effective_class_name, []).append(item)
                        collect_instances_by_class(item, class_instances, schema_classes, mapping, parent_class=effective_class_name)
            elif isinstance(value, dict):
                if class_name:
                    class_instances.setdefault(class_name, []).append(value)
                collect_instances_by_class(value, class_instances, schema_classes, mapping, parent_class=class_name)
    elif isinstance(data, list):
        for item in data:
            collect_instances_by_class(item, class_instances, schema_classes, mapping, parent_class=parent_class)

def remove_nested_class_fields(instances, class_name, sv: SchemaView):
    """Remove fields in each instance that are themselves other class blocks."""
    known_classes = {cls.name for cls in sv.all_classes().values()}
    result = []
    for inst in instances:
        cleaned = {}
        for k, v in inst.items():
            k_clean = k.lower().replace("_", "")
            if isinstance(v, list) and all(isinstance(i, dict) for i in v):
                if k_clean.rstrip("s") in (name.lower().replace("_", "") for name in known_classes):
                    continue
            if isinstance(v, dict):
                if k_clean in (name.lower().replace("_", "") for name in known_classes):
                    continue
            cleaned[k] = v
        result.append(cleaned)
    return result

def main():
    """Run the TSV flattener."""
    parser = argparse.ArgumentParser(description="Flatten LinkML YAML data to TSV")
    parser.add_argument("schema", help="Path to LinkML schema (YAML)")
    parser.add_argument("input", help="Input YAML instance file")
    parser.add_argument("output_dir", help="Output directory for TSV files")
    parser.add_argument(
        "--mapping-file", help="Optional YAML file mapping keys to class names"
    )
    parser.add_argument(
        "--list-style",
        choices=["join", "explode"],
        default="join",
        help="How to handle list values (default: join with ',')",
    )
    parser.add_argument(
        "--mode",
        choices=["per-class", "wide"],
        default="per-class",
        help="Whether to generate a TSV per class or one wide table (default: per-class)",
    )
    args = parser.parse_args()

    sv = SchemaView(args.schema)
    schema_classes = {cls.name.lower().replace("_", ""): cls.name for cls in sv.all_classes().values()}

    mapping = {}
    if args.mapping_file:
        with open(args.mapping_file) as mf:
            raw_map = yaml.safe_load(mf)
            mapping = extract_mapping_class_derivations(raw_map)

    with open(args.input) as f:
        data = yaml.safe_load(f)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    if args.mode == "wide":
        all_records = []
        for top_key, records in data.items():
            if not isinstance(records, list):
                continue
            for inst in records:
                raw = inst.dict(exclude_unset=True) if isinstance(inst, YAMLRoot) else inst
                flat = flatten_dict(raw, parent_key=top_key)
                all_records.append(flat)

        df = pd.DataFrame(all_records)
        df.to_csv(Path(args.output_dir) / "wide_output.tsv", sep="\t", index=False)
        print("Wrote: wide_output.tsv")
        return

    class_instances = {}
    collect_instances_by_class(data, class_instances, schema_classes, mapping)

    for class_name, instances in class_instances.items():
        slot_order = get_slot_order(sv, class_name)
        instances = remove_nested_class_fields(instances, class_name, sv)

        flat_records = []
        list_fields = set()

        for inst in instances:
            raw = inst.dict(exclude_unset=True) if isinstance(inst, YAMLRoot) else inst
            flat = flatten_dict(raw)
            for k, v in flat.items():
                if isinstance(v, list):
                    list_fields.add(k)
            flat_records.append(flat)

        if args.list_style == "explode":
            flat_records = explode_rows(flat_records, list_fields)
        else:
            flat_records = join_lists(flat_records, list_fields)

        df = pd.DataFrame(flat_records)
        slot_cols = list(slot_order)
        extra_cols = [c for c in df.columns if c not in slot_cols]
        df = df[[c for c in slot_cols if c in df.columns] + extra_cols]

        out_path = Path(args.output_dir) / f"{class_name}.tsv"
        df.to_csv(out_path, sep="\t", index=False)
        print(f"Wrote: {out_path}")

if __name__ == "__main__":
    main()
