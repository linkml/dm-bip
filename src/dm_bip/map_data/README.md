# Map Data

LinkML-Map integration for transforming data between schemas using transformation specifications.

## Overview

The `map_data.py` module transforms source data to a target LinkML schema using LinkML-Map transformation specifications. It processes TSV files and outputs transformed data in multiple formats.

## Usage

```bash
python map_data.py \
    --source-schema path/to/source_schema.yaml \
    --target-schema path/to/target_schema.yaml \
    --data-dir path/to/input/tsv/files/ \
    --var-dir path/to/transformation/specs/ \
    --output-dir path/to/output/ \
    --output-prefix study_name \
    --output-postfix v1 \
    --output-type tsv \
    --chunk-size 1000
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--source-schema` | Yes | Path to the source LinkML schema YAML |
| `--target-schema` | Yes | Path to the target LinkML schema YAML |
| `--data-dir` | Yes | Directory containing input TSV files |
| `--var-dir` | Yes | Directory containing transformation specification YAML files |
| `--output-dir` | Yes | Directory for output files |
| `--output-prefix` | No | Prefix for output filenames |
| `--output-postfix` | No | Postfix for output filenames |
| `--output-type` | No | Output format: `json`, `jsonl`, `tsv`, or `yaml` (default: `jsonl`) |
| `--chunk-size` | No | Number of records to process per chunk (default: 1000) |

## Output

The script processes these entity types and creates one output file per entity:
- Condition
- Demography
- DrugExposure
- MeasurementObservation
- Observation
- Participant
- Person
- Procedure
- ResearchStudy
- SdohObservation

Output files are named: `{output_prefix}-{Entity}-{output_postfix}.{output_type}`

## Transformation Specifications

Transformation specs are YAML files in the `var_dir` that define how to map source data to target schema classes. See [LinkML-Map documentation](https://linkml.io/linkml-map/) for specification format.

## Example

```bash
python map_data.py \
    --source-schema data/study/implicit_schema.yaml \
    --target-schema data/bdc_model/bdc_model.yaml \
    --data-dir data/study/preprocessed/ \
    --var-dir data/study/transformation_specs/ \
    --output-dir output/study/ \
    --output-prefix STUDY \
    --output-postfix harmonized \
    --output-type tsv
```
