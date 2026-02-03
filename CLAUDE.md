# CLAUDE.md

## Project Overview

**dm-bip** (Data Model-Based Ingestion Pipeline) coordinates efforts between BioData Catalyst and INCLUDE projects to create a unified data ingest pipeline. It uses LinkML tools to standardize and transform scientific data into a harmonized data model.

**Goals:**
- Use existing LinkML tools where possible
- Fill gaps with simple, maintainable scripts
- Enable data from multiple sources to be ingested and transformed to a common schema

---

## Tech Stack

- **Language**: Python 3.11-3.13
- **CLI**: Click
- **Data Processing**: Pandas
- **Schema Tools**: LinkML, schema-automator, linkml-map, schemasheets
- **Build**: uv
- **Task Automation**: Make
- **Testing**: pytest
- **Linting**: Ruff
- **Docs**: Sphinx

---

## Key Commands

```bash
# Setup
uv sync --group docs   # Install dependencies

# Development
make test              # Run pytest
make lint              # Check code quality
make format            # Auto-format code
make docs              # Generate documentation

# Pipeline (main workflow)
make pipeline \
  DM_INPUT_DIR=<input_dir> \
  DM_SCHEMA_NAME=<name> \
  DM_OUTPUT_DIR=<output_dir>

# Individual pipeline steps
make schema-create     # Generate schema from data
make schema-lint       # Lint schema
make validate-schema   # Validate schema structure
make validate-data     # Validate data against schema
make map-data          # Transform data using LinkML-Map

# CLI
uv run dm-bip run      # Basic CLI test
```

---

## Project Structure

```
src/dm_bip/
├── cli.py                 # Click CLI definitions
├── main.py                # Core entry point
├── cleaners/              # Data cleaning utilities
├── format_converter/      # Data format conversion (melt, merge, flatten)
└── map_data/              # LinkML-Map integration

tests/
├── unit/                  # Unit tests
├── integration/           # Integration tests
├── input/                 # Test data inputs
└── output/                # Test outputs

toy_data/                  # Small test datasets for validation
Makefile                   # Main build targets
pipeline.Makefile          # Pipeline orchestration
```

---

## Conventions

- **Formatter**: Ruff, 120 char line length
- **File naming**: lowercase with hyphens for data, underscores for Python
- **Input files**: TSV/CSV, lowercase filenames, no spaces
- **Tests**: pytest, organize by unit/integration
- **Docstrings**: Required, Google style preferred

### Pipeline Configuration Variables

Key Make variables for pipeline runs:
- `DM_INPUT_DIR` / `DM_INPUT_FILES` - Input data
- `DM_SCHEMA_NAME` - Schema identifier
- `DM_OUTPUT_DIR` - Output location
- `DM_TRANS_SPEC_DIR` - Mapping specifications
- `DM_MAP_TARGET_SCHEMA` - Target schema for transformation
- `DM_MAP_CHUNK_SIZE` - Batch size (default: 10000)

---

## GitHub Practices

### Issues
- **Never edit issue bodies after creation** - use comments for updates
- **Use native sub-issues** - link via GraphQL `addSubIssue` mutation, not task lists in body
- **Add labels when creating issues** - always include the appropriate tracking label
- **Link to tracking issues** - all work issues should be sub-issues of a tracking issue

### Pull Requests
- **Don't amend/force-push** unless explicitly requested - create new commits instead
- **Reply to review comments**, then resolve conversations
- **Check CI status** before requesting review

---

## Quick Reference

| Task | Command |
|------|---------|
| Run tests | `make test` |
| Fix lint | `make format` or `uv run ruff check --fix` |
| Debug pipeline | `make pipeline-debug` |
| Check validation errors | `output/<SCHEMA>/validation-logs/` |
