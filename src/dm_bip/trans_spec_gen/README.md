# Trans-Spec Generator

Generate LinkML-Map transformation specification YAML files from raw dbGaP
metadata exports.

## Pipeline shape

```
raw Excel exports ─┐
reference data    ─┤    prepare-metadata     apply-overrides     generate-trans-specs
cleanup_rules.csv ─┴──>  (mechanical)   ──>  (per-row fixes) ──> (Jinja2 → YAML)
                            │                      │
                            ▼                      ▼
                     curated_metadata.csv    corrected.csv
```

The pipeline is intentionally split so curator decisions live outside the
mechanical join/quality-flag computation:

- **Pre-pipeline** — `cleanup_rules.csv` defines label aliases, drops, and
  description-driven label/unit inference. The curator edits this CSV; the
  pipeline applies it deterministically.
- **Reference data** — label-keyed conversion/equivalency rules under
  `data/conversion_overrides.csv` and `data/equivalency_overrides.csv` extend
  the unit-pair lookups in `unit_key.xlsx` for cases that need a label condition.
- **Post-pipeline** — `apply-overrides` merges per-row curator fixes
  (visit/age overrides, `bad_map` drops, custom conversion rules) into the
  curated CSV and recomputes quality flags.

## Background

Transformation specifications (trans-specs) define how source data maps to the
[BDCHM](https://github.com/biomedical-data-models/bdchm) harmonized model. Each
trans-spec is a YAML file that tells [linkml-map](https://github.com/linkml/linkml-map)
how to derive harmonized slots (participant, visit, age, observation type, quantity)
from dbGaP study tables.

This tool was originally developed as a Stata/Python workflow in
[RTIInternational/NHLBI-BDC-DMC-HV](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV)
and has been refactored for use within dm-bip.

## Usage

### 1. Prepare metadata

```bash
uv run dm-bip prepare-metadata \
  --raw raw_metadata.xlsx \
  --bdchv-defs bdchv_defs.csv \
  --contextual-vars contextual_variables_key.csv \
  --unit-key unit_key.xlsx \
  --cleanup-rules cleanup_rules.csv \
  --output curated_metadata.csv
```

| Option | Required | Description |
|--------|----------|-------------|
| `--raw` | Yes | Raw metadata Excel file(s); repeatable |
| `--bdchv-defs` | Yes | BDC harmonized variable definitions CSV |
| `--contextual-vars` | Yes | Contextual variables key CSV |
| `--unit-key` | Yes | Unit key Excel file (conversions, ucum, equivalencies sheets) |
| `--cleanup-rules` | No | Curator cleanup rules CSV (see below) |
| `--output` | Yes | Output curated CSV path |

### 2. Apply curator overrides (optional)

```bash
uv run dm-bip apply-overrides \
  --input curated_metadata.csv \
  --fixes curator_fixes.csv \
  --output corrected_metadata.csv
```

### 3. Generate trans-spec YAMLs

```bash
uv run dm-bip generate-trans-specs \
  --input corrected_metadata.csv \
  --output ./output \
  --cohort aric
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | | Path to the metadata CSV |
| `--output` | `-o` | Yes | | Directory for YAML output files |
| `--cohort` | `-c` | Yes | | Cohort to filter on |
| `--entity` | `-e` | No | MeasurementObservation | Entity type to generate |

### Entities and templates

`--entity` selects both the Jinja2 template and the row-completeness rule from
the `ENTITY_REGISTRY` in `generate_trans_specs.py` — there is no separate
template flag. Registered entities:

| Entity | Template | "Good" when |
|--------|----------|-------------|
| `MeasurementObservation` | `templates/yaml_measobs.j2` | `row_good` flag set by prepare-metadata |
| `Condition` | `templates/yaml_condition.j2` | `pht`, `participantidphv`, `onto_id`, `phv`, `associatedvisit`, `value_mappings`, `condition_provenance` all present |

An unregistered entity exits with a parameter error.

#### Example: Condition

The input is one row per source-to-target mapping. A worked example lives in
[`tests/input/make_yaml/condition_sample.csv`](../../../tests/input/make_yaml/condition_sample.csv);
a single row like:

```csv
bdchm_entity,cohort,bdchm_varname,pht,participantidphv,onto_id,phv,associatedvisit,value_mappings,condition_provenance,associated_evidence,relationship_to_participant
Condition,chs,copd,pht001452,phv00100285,MONDO:0005002,phv00100497,CHS BASELINE BOTH,0=ABSENT;1=PRESENT,PATIENT_SELF-REPORTED_CONDITION,self-report questionnaire,
```

renders to:

```yaml
- class_derivations:
    Condition:
      populated_from: pht001452
      slot_derivations:
        associated_participant:
          expr: 'uuid5("https://w3id.org/bdchm/Participant", str({phv00100285}) + ":CHS")'
        associated_visit:
          expr: 'uuid5("https://w3id.org/bdchm/Visit", str({phv00100285}) + ":CHS BASELINE BOTH")'
        condition_concept:
          value: 'MONDO:0005002'
          range: string
        condition_status:
          populated_from: phv00100497
          value_mappings:
            '0': ABSENT
            '1': PRESENT
        condition_provenance:
          value: 'PATIENT_SELF-REPORTED_CONDITION'
          range: string
        relationship_to_participant:
          value: 'ONESELF'
          range: string
```

The Condition template targets the common `uuid5` participant/visit idiom. More
complex hand-authored cases — `case()`-based visits, class-level `joins`, age
bounds, dynamic concepts — are not yet templated; see the
[corpus coverage note on #329](https://github.com/linkml/dm-bip/issues/329#issuecomment-4650332503)
for the current boundary.

## Cleanup rules CSV

Curator-maintained rules applied before the mechanical pipeline runs.

Required columns: `rule_type`, `match_field`, `pattern`. Optional:
`is_regex`, `when_label`, `when_units`, `except_labels`, `target_value`.

Rule types:

| `rule_type` | Action |
|-------------|--------|
| `alias` | Exact rewrite of `match_field`: where `match_field == pattern`, set to `target_value` |
| `drop` | Drop rows where `match_field` matches `pattern` |
| `clear_label` | Set `bdchm_label = ""` where `match_field` matches `pattern` |
| `set_label` | Set `bdchm_label = target_value` where `match_field` matches `pattern` |
| `set_units` | Set `var_units = target_value` where `match_field` matches `pattern` |

By default `pattern` is matched exactly. Set `is_regex=1` for case-insensitive
regex matching.

**Rule order matters.** Rules apply in the order they appear in the CSV.
Aliases should generally come first so subsequent label-conditional rules
(`set_label`, `set_units` with `when_label`) see the canonical label, not the
pre-alias raw value.

Conditional columns (AND'd onto the match):

- `when_label` — semicolon list of values; `bdchm_label` must be in the list
- `when_units` — semicolon list; `var_units` must be in the list
  (a leading or trailing `;` includes `""`, e.g. `;` matches empty)
- `except_labels` — semicolon list; rows whose `bdchm_label` appears here are skipped

Example:

```csv
rule_type,match_field,pattern,is_regex,when_label,when_units,except_labels,target_value
alias,bdchm_label,stroke status,,,,,stroke
drop,bdchm_label,medication adherence,,,,,
set_label,var_desc,diastolic,1,blood pressure,,,diastolic blood pressure
set_units,var_desc,kg/m2,1,,;,,kg/m2
```

## Reference data overrides

`data/conversion_overrides.csv` — rows of `(bdchm_label, var_units, bdchm_unit, conversion_rule)`.
Used when a unit pair needs a label-conditional conversion (e.g. cholesterol
mmol/L → mg/dL).

`data/equivalency_overrides.csv` — rows of `(bdchm_label, var_units, bdchm_unit)`.
Presence forces `equivalent_units=1` for the matching triple.

These files are loaded automatically by `prepare-metadata`; supply alternative
paths as keyword arguments to `prepare_metadata()` if needed.

## Curator fixes CSV (apply-overrides input)

Required key columns: `phv`, `bdchm_label`. Recognized override columns
(any subset):

| Column | Effect |
|--------|--------|
| `var_units_fixed` | Override `var_units` |
| `bad_map` | If `1`, drop the row |
| `participantidphv` | Override `participantidphv` |
| `associatedvisit` | Override `associatedvisit` |
| `associatedvisit_expr` | Override `associatedvisit_expr` |
| `ageinyearsphv` | Override `ageinyearsphv` |
| `conversion_rule` | Override `conversion_rule` |
| `unit_expr_custom` | Alias for `conversion_rule`; setting both on the same row is an error |
| `unit_casestmt_custom` | Override `unit_casestmt_custom` |

`apply-overrides` recomputes quality flags after applying overrides. It does
**not** re-run unit conversion/equivalency lookups, so if you override
`var_units` you should also supply any conversion-related overrides the new
unit requires.

## Output structure

```
output/
└── {cohort}/
    ├── good/          # Rows where row_good == 1 (ready for use)
    │   ├── albumin_bld.yaml
    │   └── ...
    └── bad/           # Rows where row_good != 1 (need curator review)
        └── ...
```

The `{cohort}/{quality}/{varname}.yaml` layout is parameterizable via the
`layout` argument to `generate_yaml`.

## Curated metadata CSV

The curated CSV produced by `prepare-metadata` (and consumed by
`generate-trans-specs`) contains these columns:

| Column | Description |
|--------|-------------|
| `row_good` | 1 = ready for use, 0 = needs review |
| `cohort` | Study cohort |
| `bdchm_entity` | Entity type (e.g. "MeasurementObservation") |
| `bdchm_label` | Harmonized variable label |
| `bdchm_varname` | Harmonized variable name |
| `bdchm_unit` | Target unit |
| `phv`, `pht` | dbGaP variable / table accession (split) |
| `var_desc`, `var_units` | Source description and units |
| `has_pht`, `has_onto`, `has_visit`, `has_visit_expr`, `has_age` | Structural flags |
| `unit_match`, `unit_convert`, `unit_expr`, `unit_casestmt` | Unit-handling flags |
| `equivalent_units`, `both_valid_ucums` | Internal lookup state (used by `apply-overrides`) |
| `participantidphv`, `associatedvisit`, `associatedvisit_expr`, `ageinyearsphv` | Contextual joins |
| `onto_id`, `source_unit`, `target_unit`, `conversion_rule`, `unit_casestmt_custom` | Trans-spec inputs |

Exactly one of `unit_match`, `unit_convert`, `unit_expr`, `unit_casestmt` should
be 1 for each `row_good` row.

## Testing

```bash
uv run pytest tests/unit/test_prepare_metadata.py \
              tests/unit/test_cleanup_rules.py \
              tests/unit/test_apply_overrides.py \
              tests/unit/test_generate_trans_specs.py -v
```
