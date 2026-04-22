# Trans-Spec Generator

Generate LinkML-Map transformation specification YAML files from a metadata CSV.

## Background

Transformation specifications (trans-specs) define how source data maps to the
[BDCHM](https://github.com/biomedical-data-models/bdchm) harmonized model. Each
trans-spec is a YAML file that tells [linkml-map](https://github.com/linkml/linkml-map)
how to derive harmonized slots (participant, visit, age, observation type, quantity)
from dbGaP study tables.

This tool automates trans-spec generation from a metadata CSV that catalogs the
mapping between source variables (phv IDs) and harmonized variables. It was
originally developed as a Stata/Python workflow in
[RTIInternational/NHLBI-BDC-DMC-HV](https://github.com/RTIInternational/NHLBI-BDC-DMC-HV)
and has been refactored for use within dm-bip.

## Usage

```bash
uv run dm-bip generate-trans-specs \
  --input shortdata.csv \
  --output ./output \
  --cohort aric
```

### Options

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--input` | `-i` | Yes | | Path to the metadata CSV |
| `--output` | `-o` | Yes | | Directory for YAML output files |
| `--cohort` | `-c` | Yes | | Cohort to generate specs for (e.g. aric, jhs, whi, cardia, fhs) |
| `--entity` | `-e` | No | MeasurementObservation | Entity type to filter on |
| `--template` | `-t` | No | yaml_measobs.j2 | Jinja2 template filename |

### Output structure

```
output/
└── {cohort}/
    ├── good/          # Rows where row_good == 1 (ready for use)
    │   ├── albumin_bld.yaml
    │   ├── bdy_hgt.yaml
    │   └── ...
    └── bad/           # Rows where row_good != 1 (need curator review)
        └── ...
```

## Input CSV format

The metadata CSV must contain these columns:

| Column | Description |
|--------|-------------|
| `bdchm_entity` | Entity type (e.g. "MeasurementObservation") |
| `cohort` | Study cohort (e.g. "aric", "jhs") |
| `bdchm_varname` | Harmonized variable name |
| `row_good` | 1 = ready for use, 0 = needs review |
| `pht` | dbGaP study table ID |
| `participantidphv` | PHV for participant ID |
| `phv` | PHV for the measurement value |
| `onto_id` | Ontology ID (e.g. LOINC code) |
| `bdchm_unit` | Target unit |
| `has_visit` | 1 = has direct visit value |
| `has_visit_expr` | 1 = visit derived via expression |
| `associatedvisit` | Visit label (when has_visit=1) |
| `associatedvisit_expr` | Visit expression input (when has_visit_expr=1) |
| `has_age` | 1 = has age data |
| `ageinyearsphv` | PHV for age in years |
| `unit_match` | 1 = source unit matches target |
| `unit_convert` | 1 = needs unit conversion |
| `unit_expr` | 1 = needs expression-based conversion |
| `unit_casestmt` | 1 = needs case-statement conversion |
| `source_unit` | Source unit (when unit_convert=1) |
| `target_unit` | Target unit (when unit_convert=1) |
| `conversion_rule` | Math expression (when unit_expr=1) |
| `unit_casestmt_custom` | Case expression (when unit_casestmt=1) |

Exactly one of `unit_match`, `unit_convert`, `unit_expr`, `unit_casestmt` should
be 1 for each row.

## Jinja2 template

The template (`templates/yaml_measobs.j2`) defines the YAML structure for
MeasurementObservation trans-specs. It handles four unit-handling branches
and conditional visit/age fields. Custom templates can be provided via the
`--template` option.

## Testing

```bash
uv run pytest tests/unit/test_generate_trans_specs.py -v
```

Tests use a synthetic 8-row CSV (`tests/input/make_yaml/shortdata_sample.csv`)
that covers all template branches without requiring real study data.
