# Scripts - Format Converters

## Merge a column from one file to another
The `merge_add_column.py` script is designed to take two files and widen one file, i.e. add an additional column, with data from the second file. For example, biometric data, e.g. age, may be collected at various timepoints. However, in order to map this data using `linkml-map`, rather than having one `timepoint` column with various timepoints and one age column with values for each participant at the different timepoints as separate rows, this data should be converted from a long format to a wide format where there are columns for each timepoint and the metric of interest, e.g. age_at_visit_timepoint_1. For example, for the INCLUDE LinkML model the `Participant.ageAtFirstParticipantEngagement` values for the BrainPower study are sourced from a file where the `timepoint` value equals 1 for the column `age_at_visit`. The script will convert this long data into a new column, e.g. `age_at_visit_timepoint_1` and add the age values into the column.

### Usage
From the `scripts` directory run:
```
python merge_add_column.py \
  --left_path <PATH-TO-INPUT-FILE_1> \
  --right_path <PATH-TO-INPUT-FILE_2> \
  --output_file <PATH-TO-OUTPUT-FILE> \
  --new_column age_at_visit_timepoint_1 \
  --source_column age_at_visit \
  --left_id id \
  --right_id id \
  --filter_column timepoint \
  --filter_value 1
  ```

#### Working example
```
python merge_add_column.py \
  --left_path ../../../data/BrainPower-STUDY/raw_data/TSV/demographics.tsv \
  --right_path ../../../data/BrainPower-STUDY/raw_data/TSV/ageateventandlatency.tsv \
  --output_file demographics_with_age.tsv \
  --new_column age_at_visit_timepoint_1 \
  --source_column age_at_visit \
  --left_id id \
  --right_id id \
  --filter_column timepoint \
  --filter_value 1
  ```
  NOTE: If running the script in the linkml-map uv environment, run as `uv run python ...` after adding `pandas` to that environment (it is not included by default).


## Melt a file - convert from wide to long format
The `melt_conditions.py` script is designed to convert a file of conditions from a long format to a wide format. This is a pre-processing script to prepare data for annotation using Harmonica. The use case for this script is when the conditions to annotate with ontology terms are listed as column headers (see Wide format file example below). The result of the script is a long format file (see Long format file example below) where each row represents one condition that the participant has based on the presence of the value 1.
TODO: Generalize for additional values that indicates the participant was found to have the indicated condition, e.g. true, present, etc.

### Usage
```
python melt_conditions.py \
  --input_file <PATH-TO-INPUT-FILE> \
  --output_file <PATH-TO-OUTPUT-FILE> \
  --id_vars_str <comma separated list of ID variables # id,timepoint> \
  --var_name <name of new column header for the conditions>
```
NOTE: If running the script in the linkml-map uv environment, run as `uv run python ...` after adding `pandas` to that environment (it is not included by default).


#### Working example
```
uv run python melt_and_annotate_conditions.py \
  --input_file ../../../data/BrainPower-STUDY/raw_data/TSV/healthconditions.tsv  \
  --id_vars id,timepoint \
  --var_name condition_name
```

#### Example file formats for "wide" and "long" formats
Wide format
```
id  timepoint asd vsd pda
123 1 0 1 0
124 1 1 0 1
125 1 1 0 0
```

Long Format
```
id  timepoint condition_name  has_condition
123 1 vsd 1
124 1 asd 1
124 1 pda 1
125 1 pda 1
```
