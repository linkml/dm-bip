# Map Data

LinkML-Map integration for transforming data between schemas using transformation specifications.

## Overview

The `map_data.py` module transforms source data to a target LinkML schema using LinkML-Map transformation specifications. It processes TSV files and outputs transformed data in multiple formats.

## Usage

```bash
python map_data.py \
    --source_schema path/to/source_schema.yaml \
    --target_schema path/to/target_schema.yaml \
    --data_dir path/to/input/tsv/files/ \
    --var_dir path/to/transformation/specs/ \
    --output_dir path/to/output/ \
    --output_prefix study_name \
    --output_postfix v1 \
    --output_type tsv \
    --chunk_size 1000
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--source_schema` | Yes | Path to the source LinkML schema YAML |
| `--target_schema` | Yes | Path to the target LinkML schema YAML |
| `--data_dir` | Yes | Directory containing input TSV files |
| `--var_dir` | Yes | Directory containing transformation specification YAML files |
| `--output_dir` | Yes | Directory for output files |
| `--output_prefix` | Yes | Prefix for output filenames |
| `--output_postfix` | Yes | Postfix for output filenames |
| `--output_type` | No | Output format: `json`, `jsonl`, `tsv`, or `yaml` (default: `tsv`) |
| `--chunk_size` | No | Number of records to process per chunk (default: 1000) |

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
    --source_schema data/study/implicit_schema.yaml \
    --target_schema data/bdc_model/bdc_model.yaml \
    --data_dir data/study/preprocessed/ \
    --var_dir data/study/transformation_specs/ \
    --output_dir output/study/ \
    --output_prefix STUDY \
    --output_postfix harmonized \
    --output_type tsv
```
