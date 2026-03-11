# Pipeline Steps — Developer Reference

<!--
  INSTRUCTIONS FOR COMPLETING THIS DOCUMENT (after /clear):

  This is a skeleton. To finish it:

  1. Read these files for pipeline flow details:
     - pipeline.Makefile (the full pipeline orchestration)
     - toy_data/from_raw/config.mk and toy_data/pre_cleaned/config.mk
     - toy_data/enum_test/config.mk (the new enum derivations test)
     - src/dm_bip/cleaners/prepare_input.py (step 0)
     - src/dm_bip/map_data/map_data.py (step 3)

  2. For real data paths, check:
     - The Dockerfile clones NHLBI-BDC-DMC-HM and NHLBI-BDC-DMC-HV repos
     - RTIInternational/NHLBI-BDC-DMC-HV on GitHub has production trans-specs
       (e.g., priority_variables_transform/CHS-ingest/afib.yaml)
     - docs/pipeline_user_docs.md describes the user-facing workflow

  3. For issue links, search: gh issue list --repo linkml/dm-bip --limit 50
     Key issues: #211 (enum derivations), plus search for schema-automator,
     validation, mapping issues.

  4. Fill in the TODO markers below with actual file paths, descriptions, and links.

  5. The "Future Pipeline" table should show what changes when enum derivations
     are integrated — mainly steps 1 and 3 change, plus new curation steps for
     writing enum_derivations in specs.
-->

## Current Pipeline

| Step | Script/Tool | Description | Toy Raw Files | Toy Pre-cleaned Files | Real Data Files | Notes / Issues |
|------|-------------|-------------|---------------|----------------------|-----------------|----------------|
| **0. Prepare** (from_raw only) | [`prepare_input.py`](../src/dm_bip/cleaners/prepare_input.py) | Unzip raw dbGaP `.txt.gz`, strip junk headers, filter to required phts using mapping specs, output clean TSVs | **In:** [`toy_data/data/raw/*.txt.gz`](../toy_data/data/raw/) + [`from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) **Out:** `output/ToyFromRaw/prepared/*.tsv` | N/A (data already clean) | **In:** raw dbGaP downloads **Out:** prepared TSVs | Only runs when `DM_RAW_SOURCE` is set |
| **1. Schema creation** | `schemauto generalize-tsvs` ([pipeline.Makefile L263-269](../pipeline.Makefile)) | Scan input TSVs, infer one class per file, one slot per column, infer types (string/int/float/date). Enum inference **disabled** by default (`--enum-threshold 1.0 --max-enum-size 0`) | **In:** `output/ToyFromRaw/prepared/*.tsv` **Out:** `output/ToyFromRaw/ToyFromRaw.yaml` | **In:** [`toy_data/data/pre_cleaned/*.tsv`](../toy_data/data/pre_cleaned/) **Out:** `output/ToyPreCleaned/ToyPreCleaned.yaml` | **In:** prepared study TSVs **Out:** `output/<study>/<study>.yaml` | Enums disabled → all categorical cols become `range: string`. See [#211](https://github.com/linkml/dm-bip/issues/211) |
| **1a. Schema lint** | `linkml-lint` ([pipeline.Makefile L286-294](../pipeline.Makefile)) | Lint the generated schema | Same as step 1 output | Same | Same | Log: `validation-logs/<name>-schema-lint.log` |
| **2. Validation** | `linkml validate` ([pipeline.Makefile L358-380](../pipeline.Makefile)) | Validate each input TSV against generated schema. Per-file logs with success/failure symlinks. Parallel-safe (`make -j N`) | **In:** prepared TSVs + schema **Out:** `validation-logs/data-validation/<file>/` | **In:** pre_cleaned TSVs + schema **Out:** same structure | Same | Continues on failure unless `DM_VALIDATE_STRICT` set. Known issues with enum validation |
| **MANUAL: Write target schema** | Human | Define target classes and slots representing the harmonized data model | [`toy_data/target-schema.yaml`](../toy_data/target-schema.yaml) | Same file | TODO: BDC Harmonized Model — find repo/tag | |
| **MANUAL: Write transformation specs** | Human (curators) | One YAML per target class. Define `class_derivations` with `slot_derivations`. Currently use `value_mappings` for categorical values | [`toy_data/from_raw/specs/*.yaml`](../toy_data/from_raw/specs/) | [`toy_data/pre_cleaned/specs/*.yaml`](../toy_data/pre_cleaned/specs/) | TODO: specs in [NHLBI-BDC-DMC-HV](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV) `priority_variables_transform/` | |
| **MANUAL: Preprocess files** | Human (any tool) | Combine columns across files so each target class has one input file with all needed slots | Done in [`generate_toy_data.py`](../toy_data/create/generate_toy_data.py) | Already structured | pandas, R, dbt, etc. | See [pipeline_user_docs.md](pipeline_user_docs.md) "File Transformations" |
| **3. Mapping** | [`map_data.py`](../src/dm_bip/map_data/map_data.py) ([pipeline.Makefile L445-463](../pipeline.Makefile)) | For each spec: load source+target schemas, apply transformation via LinkML-Map `ObjectTransformer`, write output. Processes in chunks (`DM_MAP_CHUNK_SIZE`) | **In:** prepared TSVs + schemas + specs **Out:** `output/ToyFromRaw/mapped-data/TOY-<Class>--data.yaml` | **In:** pre_cleaned TSVs + schemas + specs **Out:** `output/ToyPreCleaned/mapped-data/TOY-<Class>--data.yaml` | **In/Out:** same pattern | Output format configurable: yaml, jsonl, json, tsv |

## Future Pipeline (with enum derivations)

<!--
  Changes from current:
  - Step 1: enum inference ENABLED (--enum-threshold 0.1 --max-enum-size 50)
  - New manual step: define target schema enums
  - Manual spec writing: include enum_derivations section alongside class_derivations
  - Step 2: may have validation issues with enums (known problem)
  - Step 3: LinkML-Map processes enum_derivations — VERIFIED WORKING in toy_data/enum_test/

  Key finding: every source enum needs a derivation or mirror_source: true passthrough.
  See toy_data/enum_test/ for working example.
-->

| Step | Script/Tool | Description | Toy Enum Test Files | Notes / Issues |
|------|-------------|-------------|---------------------|----------------|
| **0. Prepare** | Same as current | No change | N/A (uses pre_cleaned) | |
| **1. Schema creation** | `schemauto generalize-tsvs` | **Enum inference enabled**: `--enum-threshold 0.1 --max-enum-size 50`. Produces `sex_enum`, `ethnicity_enum`, `pain_severity_enum`, etc. | **Out:** `output/EnumTest/EnumTest.yaml` (auto-generated with enums) | TODO: schema-automator doesn't always reuse enums appropriately — [#211](https://github.com/linkml/dm-bip/issues/211) |
| **2. Validation** | `linkml validate` | **Known issues**: demographics.tsv fails validation against enum-enabled schema even though schema-automator inferred the enums from that same data | Fails on `demographics.tsv` | TODO: investigate why. File issue? |
| **MANUAL: Write target schema with enums** | Human | Add enum definitions to target schema (e.g., `target_sex_enum` with OMOP codes as permissible values). Slots must reference these enums via `range:` | [`toy_data/enum_test/target-schema.yaml`](../toy_data/enum_test/target-schema.yaml) | Required — LinkML-Map needs formal target enums |
| **MANUAL: Write specs with enum_derivations** | Human (curators) | Add `enum_derivations:` alongside `class_derivations:`. Map source enum values to target enum values. **Must include a derivation for every source enum** — use `mirror_source: true` for passthrough | [`toy_data/enum_test/specs/person-spec.yaml`](../toy_data/enum_test/specs/person-spec.yaml) | Curators need template/docs for this |
| **3. Mapping** | Same `map_data.py` | **No code changes needed.** LinkML-Map processes `enum_derivations` transparently. Verified: `Male` → `OMOP:8507`, `Female` → `OMOP:8532` | **Out:** `output/EnumTest/mapped-data/TEST-Person--data.yaml` | Working — see [test results](../issue-211-planning.md#test-results) |

## Remaining work

- [ ] Investigate validation failure with enum-enabled schemas
- [ ] Test edge cases: many-to-one (`sources`), coexistence with `value_mappings`
- [ ] Decide on pipeline defaults for enum inference
- [ ] Create curator-facing documentation/template for writing `enum_derivations`
- [ ] TODO: search issues for related work items and link them above
