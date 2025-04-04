## Toy Data for Schema Automator

### Overview
Schema Automator takes in data files (TSV) and generates LinkML schemas. Therefore, the files in this directory will be the outputs of running Schema Automator on the files (currently) in `toy_data/initial/`.

### Usage

- Create a LinkML schema on a single data file:
`schemauto generalize-tsvs --schema-name Toy_Schema toy_data/initial/demographics.tsv -o toy_data/initial/schema-automator-data/Demographics.yml`

- Create a LinkML schema on a directory of files:
```
schemauto generalize-tsvs --schema-name Toy_Schema \
    toy_data/initial/raw_data/demographics.tsv \
    toy_data/initial/raw_data/lab_results.tsv \
    toy_data/initial/raw_data/sample.tsv \
    toy_data/initial/raw_data/study.tsv \
    toy_data/initial/raw_data/subject.tsv \
    -o toy_data/initial/schema-automator-data/toy_data-all.yml
```
