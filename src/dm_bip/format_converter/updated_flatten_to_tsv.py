import argparse
import yaml
import json
import itertools
import pandas as pd
from pathlib import Path
from linkml_runtime.utils.schemaview import SchemaView
from linkml_runtime.utils.yamlutils import YAMLRoot


def flatten_dict(d, parent_key='', sep='__'):
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
    exploded = []
    for record in flat_records:
        lists = {k: v for k, v in record.items() if k in list_keys and isinstance(v, list)}
        if not lists:
            exploded.append(record)
            continue
        keys, values = zip(*lists.items())
        for combo in itertools.product(*values):
            new_record = record.copy()
            for k, v in zip(keys, combo):
                if isinstance(v, dict):
                    new_record[k] = json.dumps(v, separators=(',', ':'))
                else:
                    new_record[k] = v
            exploded.append({k: v for k, v in new_record.items() if not isinstance(v, list)})
    return exploded


def join_lists(records, list_keys, join_str=","):
    for record in records:
        for k in list_keys:
            value = record.get(k)
            if isinstance(value, list):
                record[k] = join_str.join(
                    json.dumps(item, separators=(',', ':')) if isinstance(item, dict) else str(item)
                    for item in value
                )
    return records


def get_slot_order(schemaview: SchemaView, class_name: str):
    cls = schemaview.get_class(class_name)
    if not cls:
        raise ValueError(f"Class {class_name} not found in schema")
    return schemaview.class_slots(cls.name)


def main():
    parser = argparse.ArgumentParser(description="Flatten all top-level classes in LinkML data to TSV")
    parser.add_argument("schema", help="Path to LinkML schema (YAML)")
    parser.add_argument("input", help="Input YAML instance file")
    parser.add_argument("output_dir", help="Output directory for TSV files")
    parser.add_argument("--list-style", choices=["join", "explode"], default="join",
                        help="How to handle list values (default: join with ',')")
    args = parser.parse_args()

    sv = SchemaView(args.schema)

    # Build lowercase mapping for class name resolution
    schema_classes = {cls.name.lower().replace("_", ""): cls.name for cls in sv.all_classes().values()}


    # Load input YAML
    with open(args.input) as f:
        data = yaml.safe_load(f)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    for top_key, records in data.items():
        if not isinstance(records, list):
            continue

        class_key = top_key.lower().replace("_", "")
        class_name = schema_classes.get(class_key)
        if not class_name:
            print(f"Skipping unknown class for key: {top_key}")
            continue

        slot_order = get_slot_order(sv, class_name)

        flat_records = []
        list_fields = set()

        for inst in records:
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

        out_path = Path(args.output_dir) / f"{top_key}.tsv"
        df.to_csv(out_path, sep="\t", index=False)
        print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
