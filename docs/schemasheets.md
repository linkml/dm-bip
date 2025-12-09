# Schemasheets

## Overview
[Schemasheets](https://linkml.io/schemasheets/) is a framework within the `LinkML ecosystem <https://linkml.io/linkml/ecosystem.html>` for managing your schema using spreadsheets (Google Sheets, Excel). It can be used to convert a Data Dictionary into LinkML.

## Installation
The ``pyproject.toml`` file includes Schema Automator as a dependency, which requires Schemasheets. If you have already followed the "Getting Started" instructions in this project's README, you can run: ``uv sync --upgrade schemasheets schema-automator`` to ensure your environment includes the latest versions.

## Usage
Schemasheets can be used as a stand-alone tool and the input file can be either a local TSV file or a Google Sheets file.

### TSV File
A `.tsv` can be used as input to Schemasheets and converted to LinkML by running:
`sheets2linkml my_filename.tsv --output my_schema.yaml`

See [here](https://linkml.io/schemasheets/install/) for the full list of commandline options. Details on how to format the input source file can be found [here](https://linkml.io/schemasheets/intro/basics/#basics).

### Google Sheets
See Schemasheets [documentation](https://linkml.io/schemasheets/howto/google-sheets/).
