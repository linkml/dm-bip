# Plan: Generate enum_derivations from value_mappings

## Context

Issue #211 requires moving from inline `value_mappings` to formal `enum_derivations` in transformation specs. The int/string blocker is fixed in local forks of schema-automator and linkml. Rather than hand-editing YAML, we need a script that reads the source schema (with inferred enums) and existing specs (with value_mappings), then generates:

1. A new target schema with enum definitions added
2. New spec files with `enum_derivations` replacing `value_mappings`

Both original and new files live in `toy_data_w_enums/` so either pipeline path works.

### Enum reuse findings from real specs

Analysis of 605 real spec files in `../NHLBI-BDC-DMC-HV/priority_variables_transform/*-ingest/` shows:
- 2617 total `value_mappings` occurrences across 14 target slot names
- Massive reuse: `condition_status` has 1794 occurrences but only 149 unique mappings
- `sex` has 58 occurrences, only 6 unique mappings
- Same target slot can have multiple distinct mappings (e.g., `condition_status`: `{0:ABSENT,1:PRESENT}` vs `{0:ABSENT,1:PRESENT,2:UNKNOWN}` vs `{0:ABSENT,1:HISTORICAL}`)
- `value_enum` has 135 occurrences, 35 unique mappings — this is the most collision-prone

**Implication:** The script must deduplicate enums by mapping content and reuse identical enums across specs.

## Script: `src/dm_bip/generate_enum_specs.py`

CLI tool using Click (consistent with project conventions).

### Inputs
- `--source-schema`: Source schema path (generated with enum inference)
- `--spec-dir`: Existing spec directory (with value_mappings)
- `--target-schema`: Existing target schema path
- `--output-spec-dir`: Output spec directory
- `--output-target-schema`: Output target schema path

### Algorithm

#### Step 1: Parse source schema
Build maps:
- `slot_to_enum`: slot_name → enum_name (e.g., `phv00000002` → `phv00000002_enum`)
- `enum_pvs`: enum_name → list of permissible values

#### Step 2: Collect all value_mappings from specs
Walk every spec block recursively (including inside `object_derivations`). For each `value_mappings`, record:
- source slot (`populated_from`)
- target slot name
- target class name
- the mapping `{source_val: target_val}`
- nesting path for comments (e.g., `Demography.sex` or `MeasurementObservation.value_quantity→Quantity.value_concept`)

#### Step 3: Deduplicate and name target enums

**Naming convention:**
1. If the target schema already defines an enum on this slot → reuse that name
2. Otherwise → `{target_slot}_enum`
3. If multiple distinct mappings share the same target slot name → disambiguate with a suffix. Use the source slot name: e.g., `value_concept_phv00000017_enum`, `value_concept_phv00000025_enum`

**Deduplication:** Group all value_mappings by their mapping content (the `{source: target}` dict). Identical mappings share a single target enum definition, even across different specs/blocks.

#### Step 4: Generate target enums
For each unique target enum:
- Create enum definition with target values as permissible values
- Add `range: {enum_name}` on the corresponding target schema slot/attribute
- Include YAML comment noting source slot(s) where not redundant with context

#### Step 5: Generate enum_derivations
For each spec block containing value_mappings:
- Create `enum_derivations` section at top level (alongside `class_derivations`)
- For each value_mapping → enum_derivation entry:
  - `populated_from: {source_enum_name}`
  - `permissible_value_derivations` converting each `{source_val: target_val}`
  - YAML comment documenting: slot usage path, source permissible values
- Remove `value_mappings` from the slot_derivation

#### Step 6: Handle passthrough enums
For source enums used in specs (slot appears in `populated_from`) but without `value_mappings`:
- Generate `mirror_source: true` derivation
- YAML comment listing permissible values: `# CURATOR: Source permissible values: '1', '2', '3'. Should these be mapped?`
- Log to stdout

#### Step 7: Handle edge cases
- `value_mappings` on a slot with no source enum → leave `value_mappings` in place, log warning
- Write new spec files and target schema; originals untouched

### Inventory of value_mappings in toy_data_w_enums/specs/

| File | Target Class | Target Slot | Source Slot | Nested? |
|------|-------------|-------------|-------------|---------|
| demography.yaml | Demography | sex | phv00000002 | no |
| demography.yaml | Demography | race | phv00000003 | no |
| demography.yaml | Demography | ethnicity | phv00000004 | no |
| demography.yaml | Demography | smoking_status | phv00000016 | no |
| measurements.yaml | Quantity | value_concept | phv00000017 | yes (object_derivations) |
| measurements.yaml | Quantity | value_concept | phv00000025 | yes (object_derivations) |
| observations.yaml | Observation | value_enum | phv00000049 | no |
| observations.yaml | Observation | value_enum | phv00000050 | no |
| conditions.yaml | Condition | condition_status | phv00000051 | no |

The two `value_concept` entries have different mappings → will get disambiguated names.
The two `value_enum` entries have identical mappings (`{0: None, 1: OMOP:40766945}`) → will share one enum.

### Pipeline integration

Add a `generate-enum-specs` Make target in `pipeline.Makefile`:
- Runs after `schema-create` (needs source schema with inferred enums)
- Runs before `map-data`
- Only runs when `DM_ENUM_DERIVATIONS` is set (opt-in)

Config for `toy_data_w_enums/config.mk`:
- Enable enum inference: `DM_ENUM_THRESHOLD := 0.1`, `DM_MAX_ENUM_SIZE := 50`, `DM_INFER_ENUM_FROM_INTEGERS := true`
- Enable enum derivation generation: `DM_ENUM_DERIVATIONS := true`
- Generated files go to `$(DM_OUTPUT_DIR)/enum-specs/` and `$(DM_OUTPUT_DIR)/enum-target-schema.yaml`
- `DM_MAPPING_SPEC` and `DM_MAP_TARGET_SCHEMA` point at generated files when enabled

### Files to create/modify

- **Create:** `src/dm_bip/generate_enum_specs.py`
- **Modify:** `pipeline.Makefile` — add `generate-enum-specs` target
- **Modify:** `toy_data_w_enums/config.mk` — add enum inference + derivation flags

### Verification

1. Baseline: `make pipeline CONFIG=toy_data_w_enums/config.mk` already works with value_mappings
2. Enable enum flags in config, run `make schema-create CONFIG=toy_data_w_enums/config.mk` to get source schema with enums
3. Run `generate_enum_specs.py` → produces `enum-specs/` and `enum-target-schema.yaml`
4. Inspect generated files for correctness (comments, enum names, derivations)
5. Run full pipeline with generated specs → compare mapped output to baseline
