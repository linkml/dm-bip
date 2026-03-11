# Pipeline Steps — Developer Reference

## Current Pipeline

| Step | Script/Tool | Description | Toy Raw Files | Toy Pre-cleaned Files | Real Data Files | Notes / Issues |
|------|-------------|-------------|---------------|----------------------|-----------------|----------------|
| **0. Prepare** (from_raw only) | [`prepare_input.py`](../src/dm_bip/cleaners/prepare_input.py) | Unzip raw dbGaP `.txt.gz`, strip junk headers, filter to required phts using mapping specs, output clean TSVs | **In:** [`toy_data/data/raw/*.txt.gz`](../toy_data/data/raw/) + [`from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) | N/A (data already clean) | **In:** raw dbGaP downloads + [`priority_variables_transform/*-ingest/*.yaml`](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform) (we believe only the `*-ingest/` subdirs are used — needs confirmation) | Only runs when `DM_RAW_SOURCE` is set |
|  |  |  | **Out:** [`output/ToyFromRaw/prepared/*.tsv`](../output/ToyFromRaw/prepared/) |  | **Out:** prepared TSVs (location TBD — need to find out where real pipeline output goes) |  |
| **1. Schema creation** | `schemauto generalize-tsvs` ([pipeline.Makefile L263-L269](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L263-L269)) | Scan input TSVs, infer one class per file, one slot per column, infer types (string/int/float/date). Enum inference **disabled** by default (`--enum-threshold 1.0 --max-enum-size 0`) | **In:** [`output/ToyFromRaw/prepared/*.tsv`](../output/ToyFromRaw/prepared/) | **In:** [`toy_data/data/pre_cleaned/*.tsv`](../toy_data/data/pre_cleaned/) | **In:** prepared study TSVs | Enums disabled → all categorical cols become `range: string`. See [#211](https://github.com/linkml/dm-bip/issues/211) |
|  |  |  | **Out:** [`output/ToyFromRaw/ToyFromRaw.yaml`](../output/ToyFromRaw/ToyFromRaw.yaml) | **Out:** `output/ToyPreCleaned/ToyPreCleaned.yaml` | **Out:** `output/<study>/<study>.yaml` |  |
| **1a. Schema lint** | `linkml-lint` ([pipeline.Makefile L286-L294](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L286-L294)) | Lint the generated schema | Same as step 1 output | Same | Same | Log: `validation-logs/<name>-schema-lint.log` |
| **2. Validation** | `linkml validate` ([pipeline.Makefile L358-L380](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L358-L380)) | Validate each input TSV against generated schema. Per-file logs with success/failure symlinks. Parallel-safe (`make -j N`) | **In:** prepared TSVs + schema | **In:** pre_cleaned TSVs + schema | Same | Continues on failure unless `DM_VALIDATE_STRICT` set. Known issues with enum validation |
|  |  |  | **Out:** `validation-logs/data-validation/<file>/` | **Out:** same structure |  |  |
| **MANUAL: Write target schema** | Human | Define target classes and slots representing the harmonized data model | [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) | Same file | TODO: BDC Harmonized Model — find repo/tag |  |
| **MANUAL: Write transformation specs** | Human (curators) | One YAML per target class. Define `class_derivations` with `slot_derivations`. Currently use `value_mappings` for categorical values | [`toy_data/from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) | [`toy_data/pre_cleaned/specs/*.yaml`](../toy_data/pre_cleaned/specs/) | [`priority_variables_transform/*-ingest/*.yaml`](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform) (needs confirmation) |  |
| **MANUAL: Preprocess files** | Human (any tool) | Combine columns across files so each target class has one input file with all needed slots | Done in [`generate_toy_data.py`](../toy_data/create/generate_toy_data.py) | Already structured | pandas, R, dbt, etc. | See [pipeline_user_docs.md](pipeline_user_docs.md) "File Transformations" |
| **3. Mapping** | [`map_data.py`](../src/dm_bip/map_data/map_data.py) ([pipeline.Makefile L445-L463](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L445-L463)) | For each spec: load source+target schemas, apply transformation via LinkML-Map `ObjectTransformer`, write output. Processes in chunks (`DM_MAP_CHUNK_SIZE`) | **In:** prepared TSVs + schemas + specs | **In:** pre_cleaned TSVs + schemas + specs | **In/Out:** same pattern | Output format configurable: yaml, jsonl, json, tsv |
|  |  |  | **Out:** [`output/ToyFromRaw/mapped-data/TOY-<Class>--data.yaml`](../output/ToyFromRaw/mapped-data/) | **Out:** `output/ToyPreCleaned/mapped-data/TOY-<Class>--data.yaml` |  |  |

## Future Pipeline (with enum derivations)

Changes from current pipeline:
- Step 1: enum inference **enabled** (`--enum-threshold 0.1 --max-enum-size 50`)
- New manual step: define target schema enums
- Manual spec writing: include `enum_derivations` section alongside `class_derivations`
- Step 2: validation has issues with mixed-type enum columns (see note below)
- Step 3: LinkML-Map processes `enum_derivations` — **verified working** in `toy_data/enum_test/`

Key finding: every source enum needs a derivation or `mirror_source: true` passthrough.
See [`toy_data/enum_test/`](../toy_data/enum_test/) for working example.

| Step | Script/Tool | Description | Toy Enum Test Files | Toy Raw Files | Toy Pre-cleaned Files | Real Data Files | Notes / Issues |
|------|-------------|-------------|---------------------|---------------|----------------------|-----------------|----------------|
| **0. Prepare** | Same as current | No change | N/A (uses pre_cleaned data) | Same as current | N/A | Same as current |  |
| **1. Schema creation** | `schemauto generalize-tsvs` ([pipeline.Makefile L263-L269](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L263-L269)) | **Enum inference enabled**: `--enum-threshold 0.1 --max-enum-size 50`. Produces `sex_enum`, `ethnicity_enum`, `pain_severity_enum`, etc. | **In:** [`toy_data/data/pre_cleaned/*.tsv`](../toy_data/data/pre_cleaned/) | **In:** [`output/ToyFromRaw/prepared/*.tsv`](../output/ToyFromRaw/prepared/) | **In:** [`toy_data/data/pre_cleaned/*.tsv`](../toy_data/data/pre_cleaned/) | **In:** prepared study TSVs | schema-automator may not always reuse enums appropriately — [#211](https://github.com/linkml/dm-bip/issues/211) |
|  |  |  | **Out:** [`output/EnumTest/EnumTest.yaml`](../output/EnumTest/EnumTest.yaml) | **Out:** `output/ToyFromRaw/ToyFromRaw.yaml` | **Out:** `output/ToyPreCleaned/ToyPreCleaned.yaml` | **Out:** `output/<study>/<study>.yaml` |  |
| **2. Validation** | `linkml validate` ([pipeline.Makefile L358-L380](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L358-L380)) | Validate data against enum-enabled schema. All toy files pass after [smoking_status fix](#validation-error-smoking_status-resolved). **Caveat:** columns with numeric-looking enum values (e.g. `1`, `2`) will fail — see analysis below | All 5 files pass | Not yet tested with enums | Not yet tested with enums | Not yet tested | `linkml validate` parses bare numerics as integers, not strings |
| **MANUAL: Write target schema with enums** | Human | Add enum definitions to target schema (e.g., `target_sex_enum` with OMOP codes as permissible values). Slots must reference these enums via `range:` | [`toy_data/enum_test/target-schema.yaml`](../toy_data/enum_test/target-schema.yaml) | Same | Same | Same | Required — LinkML-Map needs formal target enums |
| **MANUAL: Write specs with enum_derivations** | Human (curators) | Add `enum_derivations:` alongside `class_derivations:`. Map source enum values to target enum values. **Must include a derivation for every source enum** — use `mirror_source: true` for passthrough | [`toy_data/enum_test/specs/person-spec.yaml`](../toy_data/enum_test/specs/person-spec.yaml) | N/A (from_raw uses `value_mappings` for coded values) | Would need new specs | Would need new specs | Curators need template/docs for this |
| **3. Mapping** | Same [`map_data.py`](../src/dm_bip/map_data/map_data.py) ([pipeline.Makefile L445-L463](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L445-L463)) | **No code changes needed.** LinkML-Map processes `enum_derivations` transparently. Verified: `Male` → `OMOP:8507`, `Female` → `OMOP:8532` | **In:** pre_cleaned TSVs + schemas + specs | Same as current | Same as current | Same as current | Working — see [test results](../issue-211-planning.md#test-results) |
|  |  |  | **Out:** [`output/EnumTest/mapped-data/TEST-Person--data.yaml`](../output/EnumTest/mapped-data/TEST-Person--data.yaml) | **Out:** `output/ToyFromRaw/mapped-data/TOY-<Class>--data.yaml` | **Out:** `output/ToyPreCleaned/mapped-data/TOY-<Class>--data.yaml` |  |  |

### Validation error: `smoking_status` (resolved)

The validation errors on `demographics.tsv` were caused by numeric-looking values in a mixed-type column.

The old `generate_toy_data.py` had:
```python
smoking = random.choice([1, 2, "Former", "Never", "Unknown"])
```

This produced a `smoking_status` column with values like `1`, `2`, `Former`, `Never`, `Unknown`. In TSV, bare `1` and `2` are indistinguishable from strings — but `linkml validate` parses them as integers. Schema-automator infers a `smoking_status_enum` with permissible values `'1'`, `'2'`, `Former`, `Never`, `Unknown` (all strings). Integer `2` doesn't match string `'2'`, so validation fails:

```
[ERROR] [demographics.tsv/0] 2 is not of type 'string' in /smoking_status
[ERROR] [demographics.tsv/0] 2 is not one of ['2', 'Former', '1', 'Never', 'Unknown'] in /smoking_status
```

This is the schema-automator/linkml-validate incompatibility Corey mentioned — schema-automator treats all enum values as strings, but `linkml validate` parses numeric-looking TSV values as integers.

**Fix applied:** Changed `generate_toy_data.py` to use all-text values:
```python
smoking = random.choice(["Current", "Former", "Never", "Unknown"])
```

All 5 files now pass validation with enum inference enabled. The mapping output is unchanged (enum derivations still work correctly).

**For real data:** columns with numeric-looking codes (`1`, `2`) mixed with text (`Unknown`) will hit this same issue. The workaround is to ensure enum columns contain only non-numeric text values, or to pre-process the data so numeric codes are decoded before schema inference.

## Remaining work

- [x] ~~Fix `generate_toy_data.py` smoking_status~~ — changed to all-text values (`Current`/`Former`/`Never`/`Unknown`)
- [x] ~~Regenerate toy data and re-run EnumTest pipeline~~ — all 5 files pass validation
- [ ] Test edge cases: many-to-one (`sources`), coexistence with `value_mappings`
- [ ] Decide on pipeline defaults for enum inference
- [ ] Create curator-facing documentation/template for writing `enum_derivations`
- [ ] Confirm real data spec location (`priority_variables_transform/*-ingest/*.yaml` in [NHLBI-BDC-DMC-HV](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV/tree/main/priority_variables_transform))
- [ ] Find where real pipeline output goes
- [ ] Search issues for related work items and link them above
