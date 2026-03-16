# Issue #211: Enum Derivations — Planning

## Issue text

> We need to verify that Enum derivations work properly and give the curation team
> a transformation spec model to start adding enum derivations to the transform
> specifications.

## Our understanding of the task

There are two parts to "enum derivations":

1. **Schema-automator infers enums from data.** When it scans a column like
   `pain_severity` with values `None`, `Mild`, `Moderate`, `Severe`, it can create an
   enum type with those as permissible values in the source schema. The pipeline
   currently disables this inference.

2. **LinkML-Map `enum_derivations`** are a feature in transformation specs that map
   source schema enums to target schema enums — a top-level `enum_derivations:` section
   alongside `class_derivations:`. Currently **no specs in dm-bip use
   `enum_derivations`**; all categorical value mapping uses inline `value_mappings`
   inside `slot_derivations`.

Per conversation with Corey (2026-03-11): the first step is exploratory — **test
whether LinkML-Map can actually handle enum derivations at all**. Corey suspects it
may not work. If it doesn't, the work shifts to wherever the gap is (could be
linkml-map, schema-automator, dm-bip, or the trans-specs). Eventually, `enum_derivations`
would replace the inline `value_mappings` approach, but that's future work.

(Note: Anne's interpretation — validating/reporting unmapped values in existing
`value_mappings` — is a different issue.)

## What exists today

### Inline value_mappings (current approach)

The [`from_raw` specs](toy_data/from_raw/specs/) embed categorical mappings directly in slot derivations:

```yaml
# from_raw/specs/demography.yaml
- class_derivations:
    Demography:
      populated_from: pht000001
      slot_derivations:
        sex:
          populated_from: phv00000002
          value_mappings:        # <-- ad hoc, not tied to schema enums
            '1': OMOP:8507
            '2': OMOP:8532
```

This works but the mappings are:
- Not connected to enum definitions in either source or target schemas
- Not reusable across specs (e.g., sex mapping repeated if multiple tables have sex)
- Not invertible or introspectable as formal enum-to-enum transformations

### Source enums (auto-generated)

Schema-automator can infer enums from input data when `--enum-threshold` and
`--max-enum-size` are set. The pipeline defaults disable inference
(`--enum-threshold 1.0 --max-enum-size 0`). The enum test config enables it
(`--enum-threshold 0.1 --max-enum-size 50`).

### Target schema

[`toy_data/target-schema.yaml`](toy_data/target-schema.yaml) defines target classes (`Person`, `Demography`,
`Observation`, etc.). Now includes `target_sex_enum` with OMOP:8507/OMOP:8532 as
permissible values, and `Person.gender` has `range: target_sex_enum`.

## What `enum_derivations` look like in LinkML-Map

```yaml
enum_derivations:
  target_sex_enum:                      # target enum name
    populated_from: sex_enum            # source enum name
    mirror_source: false                # drop unmapped values
    permissible_value_derivations:
      OMOP:8507:
        populated_from: Male            # one-to-one
      OMOP:8532:
        populated_from: Female

  target_race_enum:
    populated_from: race_enum
    mirror_source: false
    permissible_value_derivations:
      OMOP:8527:
        populated_from: white
      OMOP:8516:
        populated_from: black or african american
      OMOP:8515:
        populated_from: asian
      OMOP:8557:
        sources:                         # many-to-one
          - hispanic
```

Key features:

- **`populated_from`** (on a permissible value) — One source value becomes one target
  value. `OMOP:8507: populated_from: Male` means source `Male` becomes `OMOP:8507` in
  the output. Since the mapping is one-to-one, it's reversible: seeing `OMOP:8507` in
  the output, you know it came from `Male`.

- **`sources`** — Multiple source values all map to the same target value. For example,
  `SMOKER: sources: [Current smoker, Former smoker]` collapses two source values into
  one. This is *not* reversible — seeing `SMOKER` in the output, you can't tell which
  source value produced it.

- **`mirror_source: true`** — Source values that aren't explicitly mapped pass through
  unchanged. If the source has a value `Other` and there's no mapping for it, `Other`
  appears in the output as-is.

- **`mirror_source: false`** (the default) — Source values without an explicit mapping
  are dropped. Only mapped values appear in the output.

## Work completed

### 1. Enum derivations work end-to-end (text-valued enums)

We built a test case in [`toy_data/enum_test/`](toy_data/enum_test/) and ran it through
the pipeline. **Enum derivations work** for text-valued source enums.

Test setup:
- **Source data:** Raw toy data through `prepare_input.py` → phv column names
- **Source schema:** Auto-generated with `--enum-threshold 0.1 --max-enum-size 50 --infer-enum-from-integers`
- **Target schema:** [`toy_data/target-schema.yaml`](toy_data/target-schema.yaml) with `target_sex_enum` (OMOP:8507/OMOP:8532) on `Person.gender`
- **Spec:** [`toy_data/enum_test/specs/person-spec.yaml`](toy_data/enum_test/specs/person-spec.yaml)
- **Config:** [`toy_data/enum_test/config.mk`](toy_data/enum_test/config.mk)
- **Command:** `make pipeline CONFIG=toy_data/enum_test/config.mk`

### 2. `--infer-enum-from-integers` added to schema-automator

By default, schema-automator treats integer columns as `range: integer` regardless of
cardinality. We added `--infer-enum-from-integers` to the local schema-automator
(commit `86afe6d`). This is required for the raw data path where columns like
`phv00000002` (gender) have coded integer values `1`, `2`.

The flag is wired into `pipeline.Makefile` via `DM_INFER_ENUM_FROM_INTEGERS` and
enabled in `toy_data/enum_test/config.mk`.

**Status:** Local change only, not yet released to PyPI.

### 3. Pipeline wiring

- `pipeline.Makefile`: Added `DM_INFER_ENUM_FROM_INTEGERS` variable and conditional `--infer-enum-from-integers` flag
- `toy_data/enum_test/config.mk`: Uses raw data path, enum inference enabled, integer enum inference enabled
- `toy_data/enum_test/specs/person-spec.yaml`: Uses phv column names, `enum_derivations` with `target_sex_enum` mapping and `mirror_source: true` passthroughs

### Key findings

1. **Enum derivations work end-to-end** through the dm-bip pipeline. LinkML-Map
   processes them correctly. No changes needed to `src/dm_bip/map_data/`.

2. **Both source and target schemas need formal enum definitions.** The source schema
   must have the enum (e.g., `phv00000002_enum` with `range: phv00000002_enum` on the slot),
   and the target schema must have the target enum (e.g., `target_sex_enum`).

3. **Every source enum requires a derivation.** If a source slot has an enum range,
   LinkML-Map expects a corresponding `enum_derivation`. Without one, it throws:
   `ValueError: Could not find what to derive from a source <enum_name>`.
   For enums you want to pass through unchanged, use `mirror_source: true`.

## Open blocker: int/string type mismatch

Both `linkml validate` **and** `linkml-map` parse bare numeric TSV values as integers.
When schema-automator creates string enum permissible values `'1'`, `'2'`, the tools
see integer `1`, `2` in the data — which don't match.

**Impact on validation (step 2):**
```
[ERROR] 2 is not of type 'string' in /phv00000002
[ERROR] 2 is not one of ['2', '1'] in /phv00000002
```

**Impact on mapping (step 3):**
The enum derivation `populated_from: '1'` doesn't match data value `1` (integer), so
mapped output shows `gender: null` instead of the expected `OMOP:8507`.

**This means:** Enum derivations are verified working for text-valued enums (e.g.,
`Male` → `OMOP:8507`), but **do not work for integer-coded enums** — which is the
common case in raw dbGaP data.

### Question for Corey

Where should the fix for the int/string mismatch live?

Options:
1. **schema-automator**: Generate integer-typed PVs instead of string PVs?
2. **linkml-validate / linkml-map**: Coerce values to string before enum matching?
3. **dm-bip**: Pre-process data to ensure string typing? (seems wrong)
4. **Something else?**

This is the primary blocker for using enum derivations with real dbGaP data.

### Mixed-type columns (`smoking_status`)

The toy data intentionally has `smoking_status` with mixed int/string values
(`1`, `2`, `Former`, `Never`, `Unknown`) matching real dbGaP patterns.
Schema-automator `--infer-mixed-types` (v0.5.4-rc2) uses `any_of` for these,
which removes the enum entirely. This is a separate issue from the int/string blocker.

## Remaining questions

1. **Int/string blocker** — see above. Primary blocker for real data.

2. **Coexistence with value_mappings:** Can `enum_derivations` and inline
   `value_mappings` coexist in the same spec? The from_raw path may still need
   `value_mappings` for some cases.

3. **Enum inference defaults:** Should the pipeline enable enum inference by default
   now that we know enum derivations work? Or should it remain opt-in?

4. **Curator workflow:** What does the curation team need beyond the example spec? A
   template? Documentation?

5. **Test folder structure:** Should `toy_data/enum_test/` remain separate or be
   consolidated? It currently shares `toy_data/data/raw/` and
   `toy_data/target-schema.yaml` with the main pipeline.

6. **DRY source enums:** Can schema-automator help generate the `enum_derivations`
   boilerplate (e.g., auto-generate `mirror_source: true` stubs for all source enums)?

## See also

- [Pipeline steps reference](docs/pipeline-steps.md) — copy-pasteable commands for each step
- [`toy_data/enum_test/`](toy_data/enum_test/) — working test case
- [Issue #211](https://github.com/linkml/dm-bip/issues/211) on GitHub
