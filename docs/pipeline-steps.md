# Pipeline Steps — Developer Reference

## Running the pipeline

All pipeline steps are orchestrated by `pipeline.Makefile`. The typical invocation is:

```bash
make pipeline CONFIG=<config-file>
```

### Config files

- [`toy_data_w_enums/config.mk`](../toy_data_w_enums/config.mk) — original pipeline (no enum inference, uses `value_mappings`)
- After adding enum flags to config.mk — enum-focused pipeline (enum inference enabled, uses `enum_derivations`)

Both configs use the same raw data in [`toy_data_w_enums/data/raw/`](../toy_data_w_enums/data/raw/) — gzipped dbGaP-format TSV files with `phv` column names.

The original config:
```makefile
DM_RAW_SOURCE        := toy_data_w_enums/data/raw
DM_SCHEMA_NAME       := ToyEnums
DM_OUTPUT_DIR        := output/ToyEnums
DM_INPUT_DIR         := $(DM_OUTPUT_DIR)/prepared
DM_TRANS_SPEC_DIR    := toy_data_w_enums/specs
DM_MAP_TARGET_SCHEMA := toy_data_w_enums/target-schema.yaml
```

The enum-focused config adds:
```makefile
DM_ENUM_THRESHOLD           := 0.1
DM_MAX_ENUM_SIZE            := 50
DM_INFER_ENUM_FROM_INTEGERS := true
DM_ENUM_DERIVATIONS         := true
# After generate-enum-specs runs, mapping uses generated files:
# DM_TRANS_SPEC_DIR    → $(DM_OUTPUT_DIR)/enum-specs/
# DM_MAP_TARGET_SCHEMA → $(DM_OUTPUT_DIR)/enum-target-schema.yaml
```

---

## Pipeline steps

Each step is shown with the original (value_mappings) command and the enum-focused variant where they differ.

- **Step 0. Prepare raw data**

  Strip dbGaP headers, filter to required phts, output clean TSVs with `phv` column names. Only runs when `DM_RAW_SOURCE` is set.

  - Original and enum: identical
    ```bash
    make prepare-input CONFIG=toy_data_w_enums/config.mk
    ```
    Or directly:
    ```bash
    uv run python src/dm_bip/cleaners/prepare_input.py \
      --source toy_data_w_enums/data/raw \
      --mapping toy_data_w_enums/specs \
      --output output/ToyEnums/prepared \
      --verbose
    ```

- **Step 1. Create source schema**

  Infer one class per file, one slot per column, infer types. Optionally infer enums from low-cardinality columns.

  - Original (no enum inference):
    ```bash
    make schema-create CONFIG=toy_data_w_enums/config.mk
    ```
    Uses `--enum-threshold 1.0 --max-enum-size 0` (defaults) — no enums created.

  - Enum-focused:
    ```bash
    make schema-create CONFIG=toy_data_w_enums/config.mk
    ```
    With enum flags in config, uses `--enum-threshold 0.1 --max-enum-size 50 --infer-enum-from-integers`. Produces enums like `phv00000002_enum` with permissible values `'1'`, `'2'`.

    **Local fork note:** `--infer-enum-from-integers` requires our local schema-automator change (`86afe6d`). Without it, integer columns like `phv00000002` get `range: integer` and can't participate in enum derivations.

- **Step 1a. Lint schema**

  - Original and enum: identical
    ```bash
    make schema-lint CONFIG=toy_data_w_enums/config.mk
    ```

- **Step 2. Validate data**

  Validate each input TSV against the generated source schema. Parallel-safe (`make -j N`). Continues on failure unless `DM_VALIDATE_STRICT` is set.

  - Original and enum: identical command
    ```bash
    make validate-data CONFIG=toy_data_w_enums/config.mk
    ```

    **Local fork note:** With enum-enabled schemas, validation requires our linkml change (`6c2f10e4`, `7daf8db8` on branch `schema-aware-delimited-loader`) — the schema-aware delimited file loader that preserves string/enum values instead of coercing them to integers.

- **Step 2a. Generate enum specs** *(enum-focused only)*

  Read the source schema (with inferred enums) and existing specs (with `value_mappings`), generate new specs with `enum_derivations` and a new target schema with enum definitions.

  - Enum-focused only (runs when `DM_ENUM_DERIVATIONS` is set):
    ```bash
    make generate-enum-specs CONFIG=toy_data_w_enums/config.mk
    ```
    Or directly:
    ```bash
    uv run python src/dm_bip/generate_enum_specs.py \
      --source-schema output/ToyEnums/ToyEnums.yaml \
      --spec-dir toy_data_w_enums/specs \
      --target-schema toy_data_w_enums/target-schema.yaml \
      --output-spec-dir output/ToyEnums/enum-specs \
      --output-target-schema output/ToyEnums/enum-target-schema.yaml
    ```
    Outputs:
    - `output/ToyEnums/enum-specs/*.yaml` — specs with `enum_derivations` replacing `value_mappings`
    - `output/ToyEnums/enum-target-schema.yaml` — target schema with enum definitions added

  - Original: **Manual.** Curator writes/edits [`toy_data_w_enums/target-schema.yaml`](../toy_data_w_enums/target-schema.yaml) and [`toy_data_w_enums/specs/*.yaml`](../toy_data_w_enums/specs/) by hand, using inline `value_mappings` for categoricals.

- **Step 3. Map data**

  Transform data via LinkML-Map `ObjectTransformer`. Processes in chunks.

  - Original (uses hand-written specs with `value_mappings`):
    ```bash
    make map-data CONFIG=toy_data_w_enums/config.mk
    ```

  - Enum-focused (uses generated specs with `enum_derivations`):
    ```bash
    make map-data CONFIG=toy_data_w_enums/config.mk
    ```
    With `DM_ENUM_DERIVATIONS` set, the Makefile points `DM_TRANS_SPEC_DIR` and `DM_MAP_TARGET_SCHEMA` at the generated files from step 2a.

    **Local fork note:** Schema-aware data loading during mapping requires our linkml-map change (`53ad099`) which forwards `schema_path`/`target_class` to linkml's delimited file loader.

---

## Full pipeline commands

Original:
```bash
make pipeline CONFIG=toy_data_w_enums/config.mk
```

Enum-focused (after adding enum flags to config):
```bash
make pipeline CONFIG=toy_data_w_enums/config.mk
```

The `DM_ENUM_DERIVATIONS` flag triggers the generate-enum-specs step and routes mapping through the generated files.

---

## Local fork changes (not yet released)

These changes fix the int/string type mismatch where numeric TSV values were parsed as integers, breaking string enum matching. They are installed as editable local forks via `pyproject.toml` `[tool.uv.sources]`.

| Package | Commit | Branch | Change |
|---------|--------|--------|--------|
| schema-automator | `86afe6d` | (on main) | `--infer-enum-from-integers` flag |
| linkml | `6c2f10e4`, `7daf8db8` | `schema-aware-delimited-loader` | Schema-aware TSV loader preserves string/enum values |
| linkml-map | `53ad099` | (on main) | Forwards schema_path/target_class to linkml's loader |

**When upstream releases incorporate these changes:** Remove the `[tool.uv.sources]` overrides in `pyproject.toml` and pin to the release versions. The same editable-install setup can be used in the Seven Bridges protected data enclave for running on real data before upstream releases happen.
