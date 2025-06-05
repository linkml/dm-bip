## Conditions Data files

The data files in this directory represent examples of conditions, e.g. diseases, phenotypes, or medical actions, that describe the health status of the participants in a study. The conditions data has historically been provided as either a few words to describe the condition, e.g. cardiomegaly, or as questions and answers as responses to survey questions, e.g. What is the status and age at diagnosis for each of these heart conditions? (Select all that apply.)  - Elevated cholesterol levels - Age at diagnosis 21 - 30 years.


### File descriptions
1. `conditions_simple.tsv` - simple short description of the condition
    - `condition_source_text` - this column contains the extracted text of interest to annotate 
1. `conditions_complex-questions.tsv` - questions and answers to survey questions 
    - `condition_source_text` - this column contains the question and answer and relevant terms in this value should be annotated
    - `source_column` - this column contains the extracted text of interest to annotate as an example
1. `conditions_headers.tsv` - example where the conditions are found in the column headers. These can be pivoted to row values using the `extract-conditions` make goal. The output file of `extract-conditions` is saved in the same directory as the input file named as: `{INPUT_FILE}-conditions.tsv`
Example usage:  
`make extract-conditions input_file=toy_data/raw_data_conditions/conditions_headers.tsv COND_START_COL=9`
