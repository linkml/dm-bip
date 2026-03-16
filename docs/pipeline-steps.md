# Pipeline Steps — Developer Reference

## Running the pipeline

All pipeline steps are orchestrated by `pipeline.Makefile`. The typical invocation is:

```bash
make pipeline CONFIG=<config-file>
```

Individual steps can be run by copy-pasting the commands below.

**Config files:**
- `toy_data/from_raw/config.mk` — current pipeline (no enum inference)
- `toy_data/enum_test/config.mk` — enum derivations test (enum inference enabled)

---

## Current Pipeline (Toy Raw Data)

Config: [`toy_data/from_raw/config.mk`](../toy_data/from_raw/config.mk)

| Step | Description | Command | Notes / Issues |
|------|-------------|---------|----------------|
| **0. Prepare** | Unzip raw `.txt.gz`, strip dbGaP headers, filter to required phts, output clean TSVs with phv column names | `uv run python src/dm_bip/cleaners/prepare_input.py --source toy_data/data/raw --mapping toy_data/from_raw/specs --output output/ToyFromRaw/prepared --verbose` | Only runs when `DM_RAW_SOURCE` is set. Reads `##` header lines for phv identifiers |
| **1. Schema creation** | Infer one class per file, one slot per column, infer types. Enum inference **disabled** by default | `uv run schemauto generalize-tsvs -n ToyFromRaw --enum-threshold 1.0 --max-enum-size 0 output/ToyFromRaw/prepared/*.tsv -o output/ToyFromRaw/ToyFromRaw.yaml` | `--enum-threshold 1.0 --max-enum-size 0` → no enums. See [#211](https://github.com/linkml/dm-bip/issues/211) |
| **1a. Schema lint** | Lint the generated schema | `uv run linkml-lint output/ToyFromRaw/ToyFromRaw.yaml` | Log: `validation-logs/<name>-schema-lint.log` |
| **2. Validation** | Validate each input TSV against generated schema | `uv run linkml validate --schema output/ToyFromRaw/ToyFromRaw.yaml --target-class Pht000001 output/ToyFromRaw/prepared/pht000001.tsv` | Per-file logs, parallel-safe (`make -j N`). Continues on failure unless `DM_VALIDATE_STRICT` set |
| **MANUAL** | Write target schema | Edit [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) | Define target classes, slots, and enums |
| **MANUAL** | Write transformation specs (one per target class) | Edit [`toy_data/from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) | `class_derivations` with `slot_derivations`. Currently uses inline `value_mappings` for categoricals |
| **3. Mapping** | Transform data via LinkML-Map `ObjectTransformer`. Processes in chunks | `uv run python src/dm_bip/map_data/map_data.py --source-schema output/ToyFromRaw/ToyFromRaw.yaml --target-schema toy_data/target-schema.yaml --data-dir output/ToyFromRaw/prepared --var-dir toy_data/from_raw/specs --output-dir output/ToyFromRaw/mapped-data --output-prefix TOY --output-postfix "-data" --output-type yaml --chunk-size 10000 --no-strict` | Output format configurable: yaml, jsonl, json, tsv |

### Running the full current pipeline

```bash
make pipeline CONFIG=toy_data/from_raw/config.mk
```

Or step by step:
```bash
# Step 0: prepare raw data
make prepare-input CONFIG=toy_data/from_raw/config.mk

# Step 1: create schema
make schema-create CONFIG=toy_data/from_raw/config.mk

# Step 1a: lint schema
make schema-lint CONFIG=toy_data/from_raw/config.mk

# Step 2: validate data
make validate-data CONFIG=toy_data/from_raw/config.mk

# Step 3: map data
make map-data CONFIG=toy_data/from_raw/config.mk
```

---

## Enum Test Pipeline (with enum derivations)

Config: [`toy_data/enum_test/config.mk`](../toy_data/enum_test/config.mk)

This test pipeline uses the same raw data as the current pipeline but **enables enum inference** and uses **`enum_derivations`** in transformation specs instead of inline `value_mappings`.

### Changes from current pipeline

- Step 0: Same `prepare_input.py` from raw data (phv column names)
- Step 1: Enum inference **enabled** (`--enum-threshold 0.1 --max-enum-size 50 --infer-enum-from-integers`)
- Manual step: Target schema must define target enums (e.g., `target_sex_enum`)
- Manual step: Specs include `enum_derivations` alongside `class_derivations`
- Step 3: LinkML-Map processes `enum_derivations` — **no code changes** to `map_data.py`

### Key finding

Every source enum referenced by a mapped slot **must** have a corresponding `enum_derivation` — either an explicit mapping or `mirror_source: true` for passthrough. Without one, LinkML-Map throws: `ValueError: Could not find what to derive from a source <enum_name>`.

| Step | Description | Command | Notes / Issues |
|------|-------------|---------|----------------|
| **0. Prepare** | Same as current — unzip raw data, prepare TSVs with phv column names | `uv run python src/dm_bip/cleaners/prepare_input.py --source toy_data/data/raw --mapping toy_data/enum_test/specs --output output/EnumTest/prepared --verbose` | Same `prepare_input.py` as current pipeline |
| **1. Schema creation** | Enum inference **enabled** + integer enum inference | `uv run schemauto generalize-tsvs -n EnumTest --enum-threshold 0.1 --max-enum-size 50 --infer-enum-from-integers output/EnumTest/prepared/*.tsv -o output/EnumTest/EnumTest.yaml` | `--infer-enum-from-integers` is a **local schema-automator change** (not yet released). Produces `phv00000002_enum`, `phv00000003_enum`, etc. |
| **1a. Schema lint** | Lint the generated schema | `uv run linkml-lint output/EnumTest/EnumTest.yaml` | |
| **2. Validation** | Validate data against enum-enabled schema | `uv run linkml validate --schema output/EnumTest/EnumTest.yaml --target-class Pht000001 output/EnumTest/prepared/pht000001.tsv` | **BLOCKER**: Fails for integer-coded enums. See [int/string blocker](#intstring-type-mismatch-blocker) |
| **MANUAL** | Write target schema with enums | Edit [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) | Added `target_sex_enum` with `OMOP:8507`/`OMOP:8532`. Slot `Person.gender` has `range: target_sex_enum` |
| **MANUAL** | Write specs with `enum_derivations` | Edit [`toy_data/enum_test/specs/person-spec.yaml`](../toy_data/enum_test/specs/person-spec.yaml) | Must include derivation for **every** source enum — use `mirror_source: true` for passthrough |
| **3. Mapping** | Same `map_data.py`, processes `enum_derivations` transparently | `uv run python src/dm_bip/map_data/map_data.py --source-schema output/EnumTest/EnumTest.yaml --target-schema toy_data/target-schema.yaml --data-dir output/EnumTest/prepared --var-dir toy_data/enum_test/specs --output-dir output/EnumTest/mapped-data --output-prefix TEST --output-postfix "-data" --output-type yaml --chunk-size 10000 --no-strict` | **BLOCKER**: Integer-coded enum values map to `null`. See [int/string blocker](#intstring-type-mismatch-blocker) |

### Running the full enum test pipeline

```bash
make pipeline CONFIG=toy_data/enum_test/config.mk
```

Or step by step:
```bash
# Step 0: prepare raw data
make prepare-input CONFIG=toy_data/enum_test/config.mk

# Step 1: create schema (with enum inference)
make schema-create CONFIG=toy_data/enum_test/config.mk

# Step 1a: lint schema
make schema-lint CONFIG=toy_data/enum_test/config.mk

# Step 2: validate data
make validate-data CONFIG=toy_data/enum_test/config.mk

# Step 3: map data (with enum derivations)
make map-data CONFIG=toy_data/enum_test/config.mk
```

### Clean and re-run from scratch

```bash
make clean CONFIG=toy_data/enum_test/config.mk
make pipeline CONFIG=toy_data/enum_test/config.mk
```

---

## Int/string type mismatch blocker

Both `linkml validate` **and** `linkml-map` parse bare numeric values in TSV as integers. When schema-automator creates string enum permissible values `'1'`, `'2'`, the tools see integer `1`, `2` in the data — which don't match.

This affects **two** pipeline steps:

1. **Validation (step 2):** `linkml validate` reports errors like:
   ```
   [ERROR] 2 is not of type 'string' in /phv00000002
   [ERROR] 2 is not one of ['2', '1'] in /phv00000002
   ```

2. **Mapping (step 3):** `linkml-map` can't match data value `1` (integer) to enum derivation `populated_from: '1'` (string), so mapped output shows `gender: null`.

**Root cause:** TSV is untyped text, but LinkML tools parse numeric-looking values as integers before matching against string-typed enum values.

**Status:** Open blocker. Need to discuss with Corey whether the fix belongs in:
- schema-automator (generate integer PVs?)
- linkml-validate / linkml-map (coerce to string before enum matching?)
- dm-bip (pre-process data to quote numeric values?)

**Workaround for text-valued enums:** Enum derivations work correctly when source enum values are text strings (e.g., `Male` → `OMOP:8507`). The blocker only affects integer-coded enums.

### Mixed-type column note (`smoking_status`)

`smoking_status` in the toy data intentionally mixes integers and strings (`1`, `2`, `Former`, `Never`, `Unknown`) — matching real dbGaP patterns. Schema-automator `--infer-mixed-types` (v0.5.4-rc2) uses `any_of` for these columns, which removes the enum entirely rather than fixing enum validation. This remains an open problem.

---

## `--infer-enum-from-integers` (local schema-automator change)

By default, schema-automator treats integer columns as `range: integer`, even if they have low cardinality. The `--infer-enum-from-integers` flag (added locally, not yet released) makes it treat low-cardinality integer columns as enum candidates, subject to `--enum-threshold` and `--max-enum-size`.

This is needed for the raw data path where columns like `phv00000002` (gender) have values `1`, `2` — without this flag, they'd be `integer` and enum derivations couldn't apply.

Pipeline wiring in [`pipeline.Makefile` L71-73](../pipeline.Makefile):
```makefile
DM_INFER_ENUM_FROM_INTEGERS ?=    # empty = disabled
```

Enabled in [`toy_data/enum_test/config.mk`](../toy_data/enum_test/config.mk):
```makefile
DM_INFER_ENUM_FROM_INTEGERS := true
```

---

## Remaining work

- [ ] **Resolve int/string type mismatch blocker** — discuss with Corey
- [ ] Explore using schema-automator to generate DRY source enums for transform specs
- [ ] Test edge cases: many-to-one (`sources`), coexistence with `value_mappings`
- [ ] Decide on pipeline defaults for enum inference
- [ ] Create curator-facing documentation/template for writing `enum_derivations`
- [ ] Decide whether to keep separate `toy_data/enum_test/` folder or consolidate
