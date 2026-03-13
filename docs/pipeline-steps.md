# Pipeline Steps — Developer Reference

## Current Pipeline (Toy Raw Data)

| Step | Script/Tool | Description | Toy Raw Files | Notes / Issues |
|------|-------------|-------------|---------------|----------------|
| **0. Prepare** | [`prepare_input.py`](../src/dm_bip/cleaners/prepare_input.py) | Unzip raw dbGaP `.txt.gz`, strip junk headers, filter to required phts using mapping specs, output clean TSVs | **In:** [`toy_data/data/raw/*.txt.gz`](../toy_data/data/raw/) + [`from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) | Only runs when `DM_RAW_SOURCE` is set |
|  |  |  | **Out:** [`output/ToyFromRaw/prepared/*.tsv`](../output/ToyFromRaw/prepared/) |  |
| **1. Schema creation** | `schemauto generalize-tsvs` ([pipeline.Makefile L263-L269](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L263-L269)) | Scan input TSVs, infer one class per file, one slot per column, infer types (string/int/float/date). Enum inference **disabled** by default (`--enum-threshold 1.0 --max-enum-size 0`) | **In:** [`output/ToyFromRaw/prepared/*.tsv`](../output/ToyFromRaw/prepared/) | Enums disabled → all categorical cols become `range: string`. See [#211](https://github.com/linkml/dm-bip/issues/211) |
|  |  |  | **Out:** [`output/ToyFromRaw/ToyFromRaw.yaml`](../output/ToyFromRaw/ToyFromRaw.yaml) |  |
| **1a. Schema lint** | `linkml-lint` ([pipeline.Makefile L286-L294](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L286-L294)) | Lint the generated schema | Same as step 1 output | Log: `validation-logs/<name>-schema-lint.log` |
| **2. Validation** | `linkml validate` ([pipeline.Makefile L358-L380](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L358-L380)) | Validate each input TSV against generated schema. Per-file logs with success/failure symlinks. Parallel-safe (`make -j N`) | **In:** prepared TSVs + schema | Continues on failure unless `DM_VALIDATE_STRICT` set |
|  |  |  | **Out:** `validation-logs/data-validation/<file>/` |  |
| **MANUAL: Write target schema** | Human | Define target classes and slots representing the harmonized data model | [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) |  |
| **MANUAL: Write transformation specs** | Human (curators) | One YAML per target class. Define `class_derivations` with `slot_derivations`. Currently use `value_mappings` for categorical values | [`toy_data/from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) |  |
| **MANUAL: Preprocess files** | Human (any tool) | Combine columns across files so each target class has one input file with all needed slots | Done in [`generate_toy_data.py`](../toy_data/create/generate_toy_data.py) | See [pipeline_user_docs.md](pipeline_user_docs.md) "File Transformations" |
| **3. Mapping** | [`map_data.py`](../src/dm_bip/map_data/map_data.py) ([pipeline.Makefile L445-L463](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L445-L463)) | For each spec: load source+target schemas, apply transformation via LinkML-Map `ObjectTransformer`, write output. Processes in chunks (`DM_MAP_CHUNK_SIZE`) | **In:** prepared TSVs + schemas + specs | Output format configurable: yaml, jsonl, json, tsv |
|  |  |  | **Out:** [`output/ToyFromRaw/mapped-data/TOY-<Class>--data.yaml`](../output/ToyFromRaw/mapped-data/) |  |

## Future Pipeline (with enum derivations)

Changes from current pipeline:
- Step 1: enum inference **enabled** (`--enum-threshold 0.1 --max-enum-size 50`)
- New manual step: define target schema enums
- Manual spec writing: include `enum_derivations` section alongside `class_derivations`
- Step 2: validation has issues with mixed-type enum columns (see note below)
- Step 3: LinkML-Map processes `enum_derivations` — **verified working** in `toy_data/enum_test/`

Key finding: every source enum needs a derivation or `mirror_source: true` passthrough.
See [`toy_data/enum_test/`](../toy_data/enum_test/) for working example.

| Step | Script/Tool | Description | Toy Enum Test Files | Notes / Issues |
|------|-------------|-------------|---------------------|----------------|
| **0. Prepare** | Same as current | No change | N/A (uses pre_cleaned data) |  |
| **1. Schema creation** | `schemauto generalize-tsvs` ([pipeline.Makefile L263-L269](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L263-L269)) | **Enum inference enabled**: `--enum-threshold 0.1 --max-enum-size 50`. Produces `sex_enum`, `ethnicity_enum`, `pain_severity_enum`, etc. | **In:** [`toy_data/data/pre_cleaned/*.tsv`](../toy_data/data/pre_cleaned/) | schema-automator may not always reuse enums appropriately — [#211](https://github.com/linkml/dm-bip/issues/211) |
|  |  |  | **Out:** [`output/EnumTest/EnumTest.yaml`](../output/EnumTest/EnumTest.yaml) |  |
| **2. Validation** | `linkml validate` ([pipeline.Makefile L358-L380](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L358-L380)) | Validate data against enum-enabled schema. `demographics.tsv` fails due to [mixed int/string enum values](#validation-error-smoking_status-known-intentional-test-case) | `demographics.tsv` fails (intentional) | `linkml validate` parses bare numerics as integers, not strings |
| **MANUAL: Write target schema with enums** | Human | Add enum definitions to target schema (e.g., `target_sex_enum` with OMOP codes as permissible values). Slots must reference these enums via `range:` | [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) | Required — LinkML-Map needs formal target enums |
| **MANUAL: Write specs with enum_derivations** | Human (curators) | Add `enum_derivations:` alongside `class_derivations:`. Map source enum values to target enum values. **Must include a derivation for every source enum** — use `mirror_source: true` for passthrough | [`toy_data/enum_test/specs/person-spec.yaml`](../toy_data/enum_test/specs/person-spec.yaml) | Curators need template/docs for this |
| **3. Mapping** | Same [`map_data.py`](../src/dm_bip/map_data/map_data.py) ([pipeline.Makefile L445-L463](https://github.com/linkml/dm-bip/blob/211-enum-derivations/pipeline.Makefile#L445-L463)) | **No code changes needed.** LinkML-Map processes `enum_derivations` transparently. Verified: `Male` → `OMOP:8507`, `Female` → `OMOP:8532` | **In:** pre_cleaned TSVs + schemas + specs | Working — see [test results](../issue-211-planning.md#test-results) |
|  |  |  | **Out:** [`output/EnumTest/mapped-data/TEST-Person--data.yaml`](../output/EnumTest/mapped-data/TEST-Person--data.yaml) |  |

### Validation error: `smoking_status` (known, intentional test case)

The `demographics.tsv` validation errors are caused by mixed int/string values in the `smoking_status` column — this is **intentional test data** representing a real-world pattern in dbGaP data.

[`generate_toy_data.py` line 110](../toy_data/create/generate_toy_data.py):
```python
smoking = random.choice([1, 2, "Former", "Never", "Unknown"])
```

Schema-automator infers a `smoking_status_enum` with permissible values `'1'`, `'2'`, `Former`, `Never`, `Unknown` (all as strings). But `linkml validate` parses bare `1` and `2` in the TSV as integers, which don't match the string enum values:

```
[ERROR] [demographics.tsv/0] 2 is not of type 'string' in /smoking_status
[ERROR] [demographics.tsv/0] 2 is not one of ['2', 'Former', '1', 'Never', 'Unknown'] in /smoking_status
```

**Status:** schema-automator v0.5.4-rc2 added `--infer-mixed-types` which uses `any_of` for mixed-type columns — but this removes the enum entirely rather than fixing enum validation. The underlying issue is `linkml validate` parsing numeric-looking TSV values as integers. This remains an open problem.

## Remaining work

- [ ] Explore using schema-automator to generate DRY source enums for transform specs
- [ ] Test edge cases: many-to-one (`sources`), coexistence with `value_mappings`
- [ ] Decide on pipeline defaults for enum inference
- [ ] Create curator-facing documentation/template for writing `enum_derivations`
- [ ] Search issues for related work items and link them above
