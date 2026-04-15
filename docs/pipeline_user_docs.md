# Pipeline User Guide

This guide walks through using the dm-bip pipeline to transform tabular data into a harmonized LinkML data model.

## Prerequisites

- dm-bip installed (see [Installation](installation.rst))
- `make` installed (pre-installed on most Mac/Linux systems)
- Input data as TSV or CSV files

## Quick Start with Toy Data

The fastest way to understand the pipeline is to run it on the included toy data:

```bash
# Simple run — clean TSVs with human-readable columns
make pipeline CONFIG=toy_data/pre_cleaned/config.mk

# Full run — starts from raw dbGaP-format files, exercises all stages
make pipeline CONFIG=toy_data/from_raw/config.mk
```

See `toy_data/README.md` for details on the toy dataset.

## Pipeline Overview

The pipeline has four stages, orchestrated by `make`:

1. **Prepare** (`make prepare-input`) — Clean raw input files: strip dbGaP metadata headers, filter tables by ID, output clean TSVs. Only runs when `DM_RAW_SOURCE` is set. *Skip this if your data is already clean TSV/CSV.*
2. **Schema** (`make schema-create`) — Infer a source [LinkML](https://linkml.io/linkml/) schema from the data using [schema-automator](https://linkml.io/schema-automator/). Produces one class per file, one slot per column.
3. **Validate** (`make validate-data`) — Validate each input file against the generated schema using `linkml validate`. Supports parallel execution (`make -j 4 validate-data`).
4. **Map** (`make map-data`) — Transform data to a target schema using [linkml-map](https://linkml.io/linkml-map/) transformation specifications.

Running `make pipeline` executes all applicable stages in order.

## Preparing Your Data

Input files must meet these requirements:
- **Format**: TSV (tab-separated) or CSV
- **Filenames**: lowercase, no spaces or special characters
- One file per source table

To convert a CSV to TSV:
```bash
python -c "import pandas as pd; pd.read_csv('file.csv').to_csv('file.tsv', sep='\t', index=False)"
```

### Raw dbGaP Data

If you're working with raw dbGaP `.txt.gz` archives, the prepare step handles extraction and cleaning automatically. Set `DM_RAW_SOURCE` to the directory containing the archives.

## Running the Pipeline

### Basic Usage

```bash
make pipeline DM_INPUT_DIR=path/to/your/tsvs DM_SCHEMA_NAME=MyStudy
```

This runs schema creation and validation. To also run data transformation, provide transformation specs and a target schema:

```bash
make pipeline \
  DM_INPUT_DIR=path/to/your/tsvs \
  DM_SCHEMA_NAME=MyStudy \
  DM_TRANS_SPEC_DIR=path/to/specs \
  DM_MAP_TARGET_SCHEMA=path/to/target-schema.yaml
```

### Using a Config File

For reproducibility, put your variables in a `.mk` file and pass it with `CONFIG=`:

```bash
make pipeline CONFIG=my-study/config.mk
```

See `toy_data/pre_cleaned/config.mk` for an example.

### Key Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DM_INPUT_DIR` | Directory containing TSV/CSV files | |
| `DM_SCHEMA_NAME` | Name for the generated schema | `Schema` |
| `DM_OUTPUT_DIR` | Output directory | `output/<schema_name>` |
| `DM_TRANS_SPEC_DIR` | Transformation specification directory | |
| `DM_MAP_TARGET_SCHEMA` | Target schema for transformation | |
| `DM_RAW_SOURCE` | Directory of raw `.txt.gz` files (enables prepare step) | |
| `DM_MAP_OUTPUT_TYPE` | Output format: `yaml`, `jsonl`, `json`, or `tsv` | `yaml` |
| `DM_MAP_CHUNK_SIZE` | Rows per processing batch | `10000` |

Run `make help` to see the full list of targets and variables.

### Output Structure

All output goes to `DM_OUTPUT_DIR` (default: `output/<schema_name>/`):

```
output/MyStudy/
├── MyStudy.yaml                    # Generated source schema
├── prepared/                       # Clean TSVs (if prepare step ran)
├── validation-logs/                # Schema and data validation logs
│   ├── data-validation/            # Per-file validation results
│   └── data-validation-errors/     # Symlinks to files with errors
└── mapped-data/                    # Transformed output files
```

## Writing Transformation Specifications

Transformation specs are YAML files that tell [linkml-map](https://linkml.io/linkml-map/) how to map source data to a target schema. Create one spec file per target class.

### Basic Structure

```yaml
- class_derivations:
    Participant:
      populated_from: subject        # source filename (without extension)
      slot_derivations:
        id:
          populated_from: subject_id  # source column name
        external_id:
          populated_from: participant_external_id
```

- `populated_from` under the class name identifies which input file provides the data
- Each `slot_derivation` maps a target slot to a source column

### Slot Value Options

Slots can be populated in several ways:

```yaml
slot_derivations:
    # Direct column mapping
    age:
      populated_from: age_at_enrollment

    # Constant value
    study_name:
      value: "My Study"

    # Value mappings (categorical recoding)
    sex:
      populated_from: gender
      value_mappings:
        '1': male
        '2': female

    # Expression (Python expression using column values)
    age_in_days:
      populated_from: age_years
      expr: "{age_years} * 365"
```

For the full specification format, including `enum_derivations` and `object_derivations`, see the [LinkML-Map documentation](https://linkml.io/linkml-map/).

### Data Requirements

For each target class, all source slots must exist in a single input file. If your data spans multiple files, preprocess them into combined files before running the pipeline. You can use any tool for this (pandas, R, dbt, etc.).
