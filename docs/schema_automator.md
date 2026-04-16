# Schema Automator

## Overview
[Schema Automator](https://linkml.io/schema-automator/index.html) is a toolkit within the [LinkML ecosystem](https://linkml.io/linkml/ecosystem.html) that assists with generating LinkML schemas from structured and semi-structured sources.

## Installation
The `pyproject.toml` file includes Schema Automator as a dependency. If you have already followed the [Getting Started](https://github.com/linkml/dm-bip#getting-started) instructions, it is already installed.

## Usage
To test Schema Automator as a stand-alone tool on a file in the `toy_data` directory:

```bash
uv run schemauto generalize-tsv toy_data/initial/study.tsv -n StudyInfo -o study_toy_data_schema.yaml
```

## Help
To see a full list of commands:

```bash
uv run schemauto --help
```

To see arguments for the `generalize-tsv` command:

```bash
uv run schemauto generalize-tsv --help
```

Issues for Schema Automator can be submitted via the [GitHub issue tracker](https://github.com/linkml/schema-automator).
