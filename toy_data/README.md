# Toy Data

Synthetic datasets for testing the dm-bip pipeline. One dataset with two presentations:

## Structure

```
toy_data/
├── create/                  # Generator script and design docs
│   └── generate_toy_data.py # Generates data/raw/ and data/pre_cleaned/ (3 files each)
├── data/
│   ├── raw/                 # dbGaP-style .txt.gz files (coded values, phv headers)
│   └── pre_cleaned/         # Human-readable TSVs (decoded values, plain column names)
├── target-schema.yaml       # Shared target schema (union of both pipelines)
├── from_raw/                # "From raw" presentation — exercises prepare step
│   ├── config.mk
│   └── specs/               # phv-based transformation specs
├── pre_cleaned/             # "Pre-cleaned" presentation — no prepare step
│   ├── config.mk
│   ├── source-schema.yaml   # Committed source schema (for unit tests)
│   └── specs/               # Human-readable column specs
├── data_dictionary/         # Example data dictionaries
├── raw_data_conditions/     # Condition data format examples
└── initial/                 # Legacy initial data and schemas
```

## Presentations

### from_raw

Starts from `.txt.gz` files with dbGaP formatting (comment lines, phv headers, junk rows). Exercises the full pipeline including the prepare step.

```bash
make pipeline CONFIG=toy_data/from_raw/config.mk
```

### pre_cleaned

Starts from clean TSVs with human-readable column names and decoded values. No prepare step needed — an accessible entry point for testing schema creation, validation, and mapping.

```bash
make pipeline CONFIG=toy_data/pre_cleaned/config.mk
```

## Regenerating data

```bash
python toy_data/create/generate_toy_data.py
```

This generates 5 `.txt.gz` files in `data/raw/` and 3 `.tsv` files in `data/pre_cleaned/`. Two files in `data/pre_cleaned/` are hand-maintained: `study.tsv` and `subject.tsv`.
