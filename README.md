# Data Model-Based Ingestion Pipeline (dm-bip)

[Documentation](https://linkml.io/dm-bip/) · [Issues](https://github.com/linkml/dm-bip/issues)

dm-bip is a data ingestion pipeline that uses [LinkML](https://linkml.io/linkml/) tools to transform tabular scientific data into a harmonized data model. It infers schemas from source data, validates against those schemas, and transforms data to a target model using declarative mapping specifications.

Currently used by the [BioData Catalyst](https://biodatacatalyst.nhlbi.nih.gov/) Data Management Core and the [INCLUDE](https://includedcc.org/) project. If you have a use case that might fit, please [open an issue](https://github.com/linkml/dm-bip/issues).

## Requirements
- Python >= 3.11, <= 3.13
- [uv](https://docs.astral.sh/uv/)

## Repository Structure
```
src/dm_bip/
├── cli.py                 # CLI entry point (Typer)
├── cleaners/              # Data cleaning and preparation utilities
├── make_yaml/             # Transformation spec generation utilities
└── map_data/              # LinkML-Map integration for data transformation

tests/                     # Unit and integration tests
toy_data/                  # Sample datasets for trying the pipeline
docs/                      # MkDocs documentation source
Makefile                   # Development and project targets
pipeline.Makefile          # Pipeline orchestration
```

## Getting Started

```bash
git clone https://github.com/linkml/dm-bip.git
cd dm-bip
uv sync
```

This requires [uv](https://docs.astral.sh/uv/getting-started/installation/) to be installed. `uv sync` handles the Python version, virtual environment, and all dependencies.

## How the Pipeline Works

dm-bip transforms tabular data (TSV/CSV) into a harmonized [LinkML](https://linkml.io/linkml/) data model through four stages:

1. **Prepare** — Clean raw input files (e.g., strip dbGaP metadata headers, filter tables)
2. **Schema** — Infer a source LinkML schema from the data using [schema-automator](https://linkml.io/schema-automator/)
3. **Validate** — Validate input data against the generated schema using [linkml validate](https://linkml.io/linkml/)
4. **Map** — Transform data to a target schema using [linkml-map](https://linkml.io/linkml-map/) transformation specifications

## Running the Pipeline

The pipeline is orchestrated through Make. A minimal run:
```bash
make pipeline DM_INPUT_DIR=path/to/data DM_SCHEMA_NAME=MyStudy
```

To try it with the included toy data:
```bash
make pipeline DM_INPUT_DIR=toy_data/pre_cleaned DM_SCHEMA_NAME=ToyData
```

Run `make help` to see all targets and configuration variables. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DM_INPUT_DIR` | Directory containing TSV/CSV files | |
| `DM_SCHEMA_NAME` | Name for the generated schema | `Schema` |
| `DM_OUTPUT_DIR` | Output directory | `output/<schema_name>` |
| `DM_TRANS_SPEC_DIR` | Transformation specification directory | |
| `DM_MAP_TARGET_SCHEMA` | Target schema for transformation | |
| `CONFIG` | Load variables from a `.mk` config file | |

## Pipeline Steps

Each stage can be run individually:

| Target | Description | Underlying tool |
|--------|-------------|-----------------|
| `make prepare-input` | Clean raw dbGaP files for pipeline input | `dm_bip.cleaners` |
| `make schema-create` | Infer a LinkML schema from data files | [schema-automator](https://linkml.io/schema-automator/) |
| `make schema-lint` | Lint the generated schema | [linkml-lint](https://linkml.io/linkml/) |
| `make validate-data` | Validate data against the schema | [linkml validate](https://linkml.io/linkml/) |
| `make map-data` | Transform data to target schema | [linkml-map](https://linkml.io/linkml-map/) |

Validation supports parallel execution: `make -j 4 validate-data`.

For detailed usage and writing transformation specifications, see the [pipeline user documentation](./docs/pipeline_user_docs.md) and the [hosted documentation](https://linkml.io/dm-bip/).

## Development

### Testing
```bash
make test
```
Or run specific tests directly:
```bash
uv run pytest tests/unit/test_something.py
```

### Linting and Formatting
```bash
make lint       # Check for issues
make format     # Auto-fix formatting
```

### Documentation
```bash
uv run mkdocs serve   # Live preview at http://localhost:8000
make docs             # Build static site
```
