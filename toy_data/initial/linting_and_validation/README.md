# LinkML Schema Linting and Validation

This project uses [LinkML](https://linkml.io/) to define schemas and validate tabular data files. Below are the commands used to lint and validate schemas and data using `linkml-lint` and `linkml-validate`.

---

## 🔍 Schema Linting

We use `linkml-lint` to check for syntax and structure issues in the schema.

### 1. Full Linting Check

```bash
linkml-lint toy_data/initial/schema-automator-data/toy_data-all.yml
```
- **More Info**: [linkml-lint CLI](https://linkml.io/linkml/cli/lint.html)

✅ Data Validation
-----------------

We use `linkml-validate` to check whether raw data files conform to their schema definitions.

### 1. Validate `study.tsv` against `study` class
```bash
linkml-validate -s toy_data/initial/schema-automator-data/toy_data-all.yml -C study toy_data/initial/raw_data/study.tsv
```
### 2. Validate `subject.tsv` against `subject` class
```bash
linkml-validate -s toy_data/initial/schema-automator-data/toy_data-all.yml -C subject toy_data/initial/raw_data/subject.tsv
```
### 3. Validate `demographics.tsv` against `demographics` class
```bash
linkml-validate -s toy_data/initial/schema-automator-data/toy_data-all.yml -C demographics toy_data/initial/raw_data/demographics.tsv
```
### 4. Validate `sample.tsv` against `sample` class
```bash
linkml-validate -s toy_data/initial/schema-automator-data/toy_data-all.yml -C sample toy_data/initial/raw_data/sample.tsv
```
### 5. Validate `lab_results.tsv` against `lab_result` class
```bash
linkml-validate -s toy_data/initial/schema-automator-data/toy_data-all.yml -C lab_results toy_data/initial/raw_data/lab_results.tsv
```

- **More Info**: [linkml-validate CLI](https://linkml.io/linkml/cli/validate.html) 

📌 Notes
    
- Ensure all required fields are present in your TSV files.
    
- Column names in TSV files must match the schema slot names.
    
- The schema file (toy\_data-all.yml) must define all referenced classes (demographics, study, etc.).