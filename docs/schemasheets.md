# Schemasheets

## Overview
[Schemasheets](https://linkml.io/schemasheets/) is a framework within the [LinkML ecosystem](https://linkml.io/linkml/ecosystem.html) for managing your schema using spreadsheets (Google Sheets, Excel). It can be used to convert a Data Dictionary into LinkML.

## Installation
Schemasheets is included as a dependency in `pyproject.toml`. If you have already followed the [Getting Started](https://github.com/linkml/dm-bip#getting-started) instructions, it is already installed.

## Usage
Schemasheets can be used as a stand-alone tool with either a local TSV file or a Google Sheets file as input.

### TSV File
```bash
sheets2linkml my_filename.tsv --output my_schema.yaml
```

See the [Schemasheets CLI documentation](https://linkml.io/schemasheets/install/) for all command-line options. Details on formatting input files can be found in the [basics guide](https://linkml.io/schemasheets/intro/basics/#basics).

### Google Sheets
See the Schemasheets [Google Sheets guide](https://linkml.io/schemasheets/howto/google-sheets/).
