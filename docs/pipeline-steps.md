# Pipeline Steps — Developer Reference

> **Note:** This file is a developer reference for the enum pipeline work (issue #211). It documents both pipeline variants so contributors can understand the differences and run either one.

All pipeline steps are orchestrated by [`pipeline.Makefile`](../pipeline.Makefile). Both pipelines use the same raw data in [`toy_data_w_enums/data/raw/`](../toy_data_w_enums/data/raw/) — gzipped dbGaP-format TSV files.

**Original pipeline** — uses hand-written specs with inline `value_mappings` for categorical slot transformations:
```bash
make pipeline CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**Enum-focused pipeline** — enables [enum inference](#2-schema-create) and uses committed specs with `enum_derivations`:
```bash
make pipeline CONFIG=toy_data_w_enums/config-enums.mk
```

The enum config ([`config-enums.mk`](../toy_data_w_enums/config-enums.mk)) adds these flags to the original ([`config-orig-valmaps.mk`](../toy_data_w_enums/config-orig-valmaps.mk)):

```makefile
DM_ENUM_THRESHOLD           := 0.1
DM_MAX_ENUM_SIZE            := 50
DM_INFER_ENUM_FROM_INTEGERS := true     # unreleased: schema-automator PR #188
```

And points at committed enum specs and target schema:
```makefile
DM_TRANS_SPEC_DIR    := toy_data_w_enums/specs/with_enum_derivations
DM_MAP_TARGET_SCHEMA := toy_data_w_enums/target-schema-enums.yaml
```

See [`pipeline.Makefile` L59–73](../pipeline.Makefile) for all enum inference variables and their defaults.

---

## Steps overview

| Step                                                                                              | value_mappings pipeline                                                                                                                                        | enum_derivations pipeline                                                                                       |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| 1\. [`prepare-input`](#1-prepare-input)<br/>Strip dbGaP headers, filter tables, output clean TSVs | Same                                                                                                                                                           | Same                                                                                                            |
| 2\. [`schema-create`](#2-schema-create)<br/>Infer source schema from TSV data                     | No enums inferred. Output: `$(DM_OUTPUT_DIR)/ToyEnums.yaml`                                                                                                   | Enums inferred from low-cardinality columns. [Unreleased: schema-automator](#unreleased-upstream-changes)                |
| 2a. [`schema-lint`](#2a-schema-lint)<br/>Lint the generated source schema                         | Same                                                                                                                                                           | Same                                                                                                            |
| 3\. Target schema and transform specs                                                             | Curator hand-writes [target schema](../toy_data_w_enums/target-schema-orig-valmaps.yaml) and [transform specs](../toy_data_w_enums/specs/with_value_mappings) with `value_mappings` | Committed [target schema](../toy_data_w_enums/target-schema-enums.yaml) and [transform specs](../toy_data_w_enums/specs/with_enum_derivations) with `enum_derivations` |
| 4\. [`validate-data`](#4-validate-data)<br/>Validate each TSV against the source schema           | Same                                                                                                                                                           | Same. [Unreleased: linkml](#unreleased-upstream-changes) for integer-coded enums                                         |
| 5\. [`map-data`](#5-map-data)<br/>Transform data using LinkML-Map                                 | Uses `value_mappings` in hand-written specs                                                                                                                    | Uses `enum_derivations` in committed specs. [Unreleased: linkml-map](#unreleased-upstream-changes)                       |

---

## Step details

### 1. `prepare-input`

Unzips raw `.txt.gz` dbGaP archives, strips metadata comment headers, filters to tables referenced in specs (by `pht` ID), and outputs clean TSVs with `phv` column names. Only runs when `DM_RAW_SOURCE` is set. Raw files not referenced in any spec are intentionally skipped (e.g., `pht000099` in the toy data has no spec and produces no output).

**Make:**
```bash
make prepare-input CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**CLI** ([`prepare_input.py`](../src/dm_bip/cleaners/prepare_input.py)):
```bash
uv run python src/dm_bip/cleaners/prepare_input.py \
  --source toy_data_w_enums/data/raw \
  --mapping toy_data_w_enums/specs/with_value_mappings \
  --output output/ToyEnums/prepared \
  --verbose
```

| Parameter | Config variable | Description |
|-----------|----------------|-------------|
| `--source` | `DM_RAW_SOURCE` | Directory of raw `.txt.gz` files |
| `--mapping` | `DM_MAPPING_SPEC` | Spec directory — scanned for `pht` IDs to determine which tables to extract |
| `--output` | `DM_INPUT_DIR` | Output directory for clean TSV files (one per table, e.g., `pht000001.tsv`) |

**How it works:**
1. Scans spec YAML files as raw text for `pht` IDs to build a filter set
2. For each `.txt.gz` file whose filename contains a matching `pht` ID:
   - Reads the gzipped content line by line
   - Strips `#`-prefixed metadata lines
   - Extracts `phv` column names from the `##` header line
   - Writes a clean TSV with `phv` column headers

---

### 2. `schema-create`

Runs [`schemauto generalize-tsvs`](https://linkml.io/schema-automator/) on the prepared TSV files to infer a LinkML source schema: one class per file, one slot per column, with types inferred from data values.

**Make:**
```bash
make schema-create CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**CLI:**
```bash
uv run schemauto generalize-tsvs \
  -n ToyEnums \
  --enum-threshold 1.0 \
  --max-enum-size 0 \
  output/ToyEnums/prepared/*.tsv \
  -o output/ToyEnums/ToyEnums.yaml
```

| Parameter | Config variable | Default | Description |
|-----------|----------------|---------|-------------|
| `-n` | `DM_SCHEMA_NAME` | `Schema` | Name for the generated schema |
| `--enum-threshold` | `DM_ENUM_THRESHOLD` | `1.0` (disabled) | Ratio of distinct values to total rows below which a column becomes an enum. Set to `0.1` to enable |
| `--max-enum-size` | `DM_MAX_ENUM_SIZE` | `0` (disabled) | Max distinct values for enum consideration. Set to `50` to enable |
| `--infer-enum-from-integers` | `DM_INFER_ENUM_FROM_INTEGERS` | *(empty, disabled)* | Treat low-cardinality integer columns as enum candidates instead of `range: integer` |
| input files | `DM_INPUT_DIR` | | TSV files from [step 1](#1-prepare-input) |
| `-o` | derived from `DM_OUTPUT_DIR`/`DM_SCHEMA_NAME` | | Output schema path |

**Enum inference (enum-focused pipeline):** With `DM_ENUM_THRESHOLD=0.1`, `DM_MAX_ENUM_SIZE=50`, and `DM_INFER_ENUM_FROM_INTEGERS=true`, schema-automator creates enum definitions for low-cardinality columns. For example, `phv00000002` (with values `1`, `2`) gets `range: phv00000002_enum` and an enum `phv00000002_enum` with permissible values `'1'`, `'2'`.

**Note:** `--infer-enum-from-integers` requires an unreleased schema-automator change ([PR #188](https://github.com/linkml/schema-automator/pull/188)). Without it, integer columns get `range: integer` regardless of cardinality.

---

### 2a. `schema-lint`

Lints the generated source schema with `linkml-lint`.

**Make:**
```bash
make schema-lint CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**CLI:**
```bash
uv run linkml-lint output/ToyEnums/ToyEnums.yaml
```

Log written to `output/ToyEnums/validation-logs/ToyEnums-schema-lint.log`.

---

### 3. Target schema and transform specs

Both pipelines use hand-written target schemas and transform specs committed to the repository. No generation step is required.

**value_mappings pipeline:**
- Target schema: [`toy_data_w_enums/target-schema-orig-valmaps.yaml`](../toy_data_w_enums/target-schema-orig-valmaps.yaml)
- Transform specs: [`toy_data_w_enums/specs/with_value_mappings/`](../toy_data_w_enums/specs/with_value_mappings/)

**enum_derivations pipeline:**
- Target schema: [`toy_data_w_enums/target-schema-enums.yaml`](../toy_data_w_enums/target-schema-enums.yaml) — includes enum definitions for target permissible values
- Transform specs: [`toy_data_w_enums/specs/with_enum_derivations/`](../toy_data_w_enums/specs/with_enum_derivations/) — uses `enum_derivations` to map source enum permissible values to target enum permissible values

---

### 4. `validate-data`

Validates each prepared TSV file against the source schema using `linkml validate`. Each file is validated as its own target class (derived from filename: `pht000001.tsv` → class `pht000001`). Parallel-safe with `make -j N`.

**Make:**
```bash
make validate-data CONFIG=toy_data_w_enums/config-orig-valmaps.mk
# or in parallel:
make -j 4 validate-data CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**CLI** (per file):
```bash
uv run linkml validate \
  --schema output/ToyEnums/ToyEnums.yaml \
  --target-class pht000001 \
  output/ToyEnums/prepared/pht000001.tsv
```

| Parameter | Config variable | Description |
|-----------|----------------|-------------|
| `--schema` | derived from `DM_OUTPUT_DIR`/`DM_SCHEMA_NAME` | Source schema from [step 2](#2-schema-create) |
| `--target-class` | derived from input filename | Class name in the source schema |
| `DM_VALIDATE_STRICT` | `DM_VALIDATE_STRICT` | If set, pipeline fails on validation errors. Otherwise logs and continues |

**Output:** Per-file logs in `output/ToyEnums/validation-logs/data-validation/`. Error symlinks in `output/ToyEnums/validation-logs/data-validation-errors/`. Summary in `output/ToyEnums/validation-logs/ToyEnums-data-validate.log`.

**Note:** With enum-enabled schemas, validation requires an unreleased linkml change — the schema-aware TSV loader that identifies numeric-ranged slots and only coerces those to int/float, preserving string and enum values as strings.

---

### 5. `map-data`

Transforms data from source schema to target schema using [LinkML-Map](https://linkml.io/linkml-map/)'s `ObjectTransformer`. This is the core transformation step.

**Make:**
```bash
make map-data CONFIG=toy_data_w_enums/config-orig-valmaps.mk
```

**CLI** ([`map_data.py`](../src/dm_bip/map_data/map_data.py)):
```bash
uv run python src/dm_bip/map_data/map_data.py \
  --source-schema output/ToyEnums/ToyEnums.yaml \
  --target-schema toy_data_w_enums/target-schema-orig-valmaps.yaml \
  --data-dir output/ToyEnums/prepared \
  --var-dir toy_data_w_enums/specs/with_value_mappings \
  --output-dir output/ToyEnums/mapped-data \
  --output-prefix TOY \
  --output-postfix "-data" \
  --output-type yaml \
  --chunk-size 10000 \
  --no-strict
```

| Parameter | Config variable | Default | Description |
|-----------|----------------|---------|-------------|
| `--source-schema` | derived from `DM_OUTPUT_DIR`/`DM_SCHEMA_NAME` | | Source schema from [step 2](#2-schema-create) |
| `--target-schema` | `DM_MAP_TARGET_SCHEMA` | | Target schema |
| `--data-dir` | `DM_INPUT_DIR` | | Directory of prepared TSVs from [step 1](#1-prepare-input) |
| `--var-dir` | `DM_TRANS_SPEC_DIR` | | Directory of transformation spec YAML files |
| `--output-dir` | `MAPPING_OUTPUT_DIR` | `$(DM_OUTPUT_DIR)/mapped-data` | Output directory |
| `--output-prefix` | `DM_MAPPING_PREFIX` | *(empty)* | Prefix for output filenames |
| `--output-postfix` | `DM_MAPPING_POSTFIX` | *(empty)* | Postfix for output filenames |
| `--output-type` | `DM_MAP_OUTPUT_TYPE` | `yaml` | Output format: `yaml`, `jsonl`, `json`, or `tsv` |
| `--chunk-size` | `DM_MAP_CHUNK_SIZE` | `10000` | Rows per processing batch |
| `--no-strict` | `DM_MAP_STRICT=false` | strict | Log errors and continue instead of failing on missing data or transform errors |

**Output:** One file per target entity, e.g., `output/ToyEnums/mapped-data/TOY-Demography-data.yaml`. Log at `output/ToyEnums/mapped-data/mapping.log`.

**Note:** Schema-aware data loading during mapping requires an unreleased linkml-map change which forwards `schema_path`/`target_class` to linkml's delimited file loader.

#### How `map_data.py` works

[`map_data.py`](../src/dm_bip/map_data/map_data.py) is dm-bip's glue between LinkML-Map and the pipeline. It is **not** the same as the `linkml-map` CLI — it handles multiple spec files, chunked TSV input, and multiple output formats.

**1. Load schemas.**
Both source and target schemas are loaded via LinkML's [`SchemaView`](https://linkml.io/linkml/developers/schemaview.html), which provides an API for querying schema structure (classes, slots, enums, ranges, inheritance).

```python
source_schemaview = SchemaView(source_schema)  # e.g., output/ToyEnums/ToyEnums.yaml
target_schemaview = SchemaView(target_schema)  # e.g., toy_data_w_enums/target-schema-orig-valmaps.yaml
```

**2. Discover entities.**
Scans all YAML files in `--var-dir` (the spec directory, e.g., [`toy_data_w_enums/specs/with_value_mappings/`](../toy_data_w_enums/specs/with_value_mappings/)) to collect unique target class names from top-level `class_derivations` keys. Nested `class_derivations` inside `object_derivations` are ignored — those represent sub-components (like `Quantity` inside `MeasurementObservation`), not standalone output entities.

For the toy data specs, this discovers: `Condition`, `Demography`, `MeasurementObservation`, `Observation`, `Participant`.

**3. For each entity, find matching spec files.**
Uses `grep` to find spec files in `--var-dir` containing `^    {Entity}:` (the indented class name under `class_derivations`). For example, `Demography` matches [`demography.yaml`](../toy_data_w_enums/specs/with_value_mappings/demography.yaml).

**4. For each spec file, process each block.**
A spec file is a YAML list of **blocks**. Each block has a `class_derivations` key (and optionally `enum_derivations`). A single file can have multiple blocks — for example, [`observations.yaml`](../toy_data_w_enums/specs/with_value_mappings/observations.yaml) has two blocks, one for visit 1 and one for visit 2:

```yaml
# Block 1: Smoking status visit 1
- class_derivations:
    Observation:
      populated_from: pht000005
      slot_derivations:
        value_enum:
          populated_from: phv00000049
          value_mappings:
            '0': None
            '1': OMOP:40766945
# Block 2: Smoking status visit 2
- class_derivations:
    Observation:
      populated_from: pht000005
      slot_derivations:
        value_enum:
          populated_from: phv00000050
          ...
```

**5. Load data and create transformer.**
For each block, the `populated_from` value (e.g., `pht000005`) identifies which TSV to load. [`DataLoader`](../src/dm_bip/map_data/map_data.py) finds `{data_dir}/{pht_id}.tsv` and reads it via LinkML's `TsvLoader`, which yields an iterator of row dicts.

The block is passed to LinkML-Map's [`ObjectTransformer`](https://linkml.io/linkml-map/), which parses `class_derivations`, `slot_derivations`, `enum_derivations`, `object_derivations`, expressions, and value_mappings into an internal transformation specification.

```python
transformer = ObjectTransformer(
    source_schemaview=source_schemaview,
    target_schemaview=target_schemaview,
)
transformer.create_transformer_specification(block)
```

**6. Transform rows.**
Each source row dict is passed through `transformer.map_object()`, which applies:
- **`populated_from`** on slots: copies the value from the named source column
- **`value`**: sets a constant
- **`expr`**: evaluates a Python expression (e.g., `'{phv00000005} * 365'`)
- **`value_mappings`**: inline dict lookup for categorical values
- **`object_derivations`**: recursively transforms nested objects (e.g., `Quantity` inside `MeasurementObservation.value_quantity`)
- **`enum_derivations`**: matches source enum permissible values to target enum permissible values via `permissible_value_derivations`

**7. Write output.**
Transformed dicts are chunked and written via a format-specific stream ([`streams.py`](../src/dm_bip/map_data/streams.py)): YAML, JSONL, JSON, or TSV. Output filename pattern: `{prefix}-{Entity}-{postfix}.{format}`.

For TSV output, if new columns appear mid-stream (a row has keys not in the initial header), the file is rewritten with updated headers.

---

## Unreleased upstream changes

The enum pipeline requires changes to three LinkML packages that have been merged upstream but not yet released. They are pinned to upstream commit hashes via PEP 440 direct references in [`pyproject.toml`](../pyproject.toml):

| Package | Change | Upstream PR | Used in step |
|---------|--------|-------------|-------------|
| schema-automator | `--infer-enum-from-integers` flag | [linkml/schema-automator#188](https://github.com/linkml/schema-automator/pull/188) | [2. schema-create](#2-schema-create) |
| linkml | Schema-aware TSV loader preserves string/enum values | merged to main | [4. validate-data](#4-validate-data) |
| linkml-map | Forwards schema_path/target_class to linkml's loader | merged to main | [5. map-data](#5-map-data) |

Install with `uv sync` — no manual setup required. The original pipeline (`config-orig-valmaps.mk`) also works with these versions — the changes are backward-compatible.

### Cleanup (when upstream releases are available)

When the upstream packages release versions that include these changes:

1. Replace the git direct references in `[project.dependencies]` with version pins (e.g., `schema-automator>=X.Y.Z`)
2. Run `uv sync` to switch from commit pins to released packages
