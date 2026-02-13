#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# Initialize variables
DM_SCHEMA_NAME=""
DM_RAW_SOURCE=""

# 1. Parse Named Parameters
while [[ $# -gt 0 ]]; do
  case $1 in
    --schema)
      DM_SCHEMA_NAME="$2"
      shift 2
      ;;
    --source)
      DM_RAW_SOURCE="$2"
      shift 2
      ;;
    *)
      echo "Error: Unknown parameter $1"
      exit 1
      ;;
  esac
done

# 2. Required Parameter Checks
if [[ -z "$DM_SCHEMA_NAME" ]]; then
  echo "ERROR: --schema is a required parameter and cannot be empty."
  exit 1
fi

if [[ -z "$DM_RAW_SOURCE" ]]; then
  echo "ERROR: --source is a required parameter and cannot be empty."
  exit 1
fi

# 3. Define derived paths (Internal Logic)
RAW_DIR_NAME=$(basename "$DM_RAW_SOURCE")
OUTPUT_NAME="${RAW_DIR_NAME}_BDCHM"

# Set specific paths based on your requirements
DM_OUTPUT_DIR="${HOME}/${OUTPUT_NAME}"
DM_INPUT_DIR="${HOME}/${RAW_DIR_NAME}_CleanedSource"
DM_TRANS_SPEC_DIR="/app/NHLBI-BDC-DMC-HV/priority_variables_transform/${DM_SCHEMA_NAME}-ingest"
DM_MAP_TARGET_SCHEMA="/app/NHLBI-BDC-DMC-HM/src/bdchm/schema/bdchm.yaml"

# 4. Create local workspace directories
mkdir -p "$DM_OUTPUT_DIR"
mkdir -p "$DM_INPUT_DIR"

# 5. Execute the make pipeline with explicit overrides
make pipeline \
  -C /app \
  DM_SCHEMA_NAME="$DM_SCHEMA_NAME" \
  DM_RAW_SOURCE="$DM_RAW_SOURCE" \
  DM_OUTPUT_DIR="$DM_OUTPUT_DIR" \
  DM_INPUT_DIR="$DM_INPUT_DIR" \
  DM_TRANS_SPEC_DIR="$DM_TRANS_SPEC_DIR" \
  DM_MAP_TARGET_SCHEMA="$DM_MAP_TARGET_SCHEMA"
