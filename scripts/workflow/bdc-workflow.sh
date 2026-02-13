#!/bin/bash
################################################################################
# BDC Data Harmonization Workflow Script
################################################################################
# Description:
#   This script orchestrates the BDC (BioData Catalyst) data harmonization
#   pipeline, transforming raw study data into BDCHM (BioData Catalyst
#   Harmonized Model) format.
#
# Usage:
#   ./bdc-workflow.sh --schema <SCHEMA_NAME> --source <RAW_DATA_PATH> [--workdir <PATH>]
#
# Required Parameters:
#   --schema    Name of the schema configuration (e.g., "FHS", "COPDGene")
#   --source    Path to the raw data source directory
#
# Optional Parameters:
#   --workdir   Working directory for pipeline execution (default: /app/dm-bip)
#
# Examples:
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study --workdir /custom/path
#
# Environment:
#   - Designed to run within the dm-bip Docker container
#   - Expects /app/dm-bip as the working directory
#   - Requires access to NHLBI-BDC-DMC-HV and NHLBI-BDC-DMC-HM repos
#
# Output:
#   - Cleaned source data in ${HOME}/<source>_CleanedSource/
#   - Harmonized BDCHM data in ${HOME}/<source>_BDCHM/
################################################################################

# Exit immediately if a command exits with a non-zero status
# -e: exit on error, -u: exit on undefined variable, -o pipefail: catch pipe errors
set -euo pipefail

#------------------------------------------------------------------------------
# Function: Display usage information
#------------------------------------------------------------------------------
usage() {
  cat << EOF
Usage: $0 --schema <SCHEMA_NAME> --source <RAW_DATA_PATH> [OPTIONS]

Required Parameters:
  --schema    Name of the schema configuration for the study
  --source    Path to the raw data source directory

Optional Parameters:
  --workdir   Working directory for pipeline execution (default: /app/dm-bip)

Examples:
  $0 --schema FHS --source /data/raw/fhs_study
  $0 --schema FHS --source /data/raw/fhs_study --workdir /custom/path

EOF
  exit 1
}

#------------------------------------------------------------------------------
# Initialize variables
#------------------------------------------------------------------------------
DM_SCHEMA_NAME=""
DM_RAW_SOURCE=""
WORKING_DIR="/app/dm-bip"  # Default working directory

#------------------------------------------------------------------------------
# 1. Parse Named Parameters
#------------------------------------------------------------------------------
# Check if no arguments provided
if [[ $# -eq 0 ]]; then
  usage
fi

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
    --workdir)
      WORKING_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Error: Unknown parameter '$1'"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

#------------------------------------------------------------------------------
# 2. Required Parameter Validation
#------------------------------------------------------------------------------
if [[ -z "$DM_SCHEMA_NAME" ]]; then
  echo "ERROR: --schema is a required parameter and cannot be empty."
  echo "Use --help for usage information"
  exit 1
fi

if [[ -z "$DM_RAW_SOURCE" ]]; then
  echo "ERROR: --source is a required parameter and cannot be empty."
  echo "Use --help for usage information"
  exit 1
fi

# Validate that the source directory exists
if [[ ! -d "$DM_RAW_SOURCE" ]]; then
  echo "ERROR: Source directory does not exist: $DM_RAW_SOURCE"
  exit 1
fi

#------------------------------------------------------------------------------
# 3. Configuration and Path Setup
#------------------------------------------------------------------------------
echo "================================================================"
echo "BDC Data Harmonization Workflow"
echo "================================================================"
echo "Schema:       $DM_SCHEMA_NAME"
echo "Raw Source:   $DM_RAW_SOURCE"
echo "Working Dir:  $WORKING_DIR"
echo "================================================================"

# Extract the base name from the raw source path
RAW_DIR_NAME=$(basename "$DM_RAW_SOURCE")
OUTPUT_NAME="${RAW_DIR_NAME}_BDCHM"

# Define output directories in user's home directory
DM_OUTPUT_DIR="${HOME}/${OUTPUT_NAME}"
DM_INPUT_DIR="${HOME}/${RAW_DIR_NAME}_CleanedSource"

# Define paths to external dependencies (within container)
DM_TRANS_SPEC_DIR="/app/NHLBI-BDC-DMC-HV/priority_variables_transform/${DM_SCHEMA_NAME}-ingest"
DM_MAP_TARGET_SCHEMA="/app/NHLBI-BDC-DMC-HM/src/bdchm/schema/bdchm.yaml"

echo ""
echo "Configuration:"
echo "  Input Directory:      $DM_INPUT_DIR"
echo "  Output Directory:     $DM_OUTPUT_DIR"
echo "  Transform Spec Dir:   $DM_TRANS_SPEC_DIR"
echo "  Target Schema:        $DM_MAP_TARGET_SCHEMA"
echo "================================================================"

# Validate that required external paths exist
if [[ ! -d "$DM_TRANS_SPEC_DIR" ]]; then
  echo "WARNING: Transform spec directory not found: $DM_TRANS_SPEC_DIR"
  echo "         Pipeline may fail if transformation specs are required."
fi

if [[ ! -f "$DM_MAP_TARGET_SCHEMA" ]]; then
  echo "WARNING: Target schema file not found: $DM_MAP_TARGET_SCHEMA"
  echo "         Pipeline may fail during mapping validation."
fi

#------------------------------------------------------------------------------
# 4. Create Workspace Directories
#------------------------------------------------------------------------------
echo ""
echo "Creating workspace directories..."
mkdir -p "$DM_OUTPUT_DIR"
mkdir -p "$DM_INPUT_DIR"
echo "✓ Workspace directories created"

#------------------------------------------------------------------------------
# 5. Execute Data Harmonization Pipeline
#------------------------------------------------------------------------------
echo ""
echo "Starting data harmonization pipeline..."
echo "================================================================"

# Validate working directory exists
if [[ ! -d "$WORKING_DIR" ]]; then
  echo "ERROR: Working directory does not exist: $WORKING_DIR"
  exit 1
fi

# Run make pipeline with all necessary parameters
# -C flag changes to the specified working directory before executing make
make pipeline \
  -C "$WORKING_DIR" \
  DM_SCHEMA_NAME="$DM_SCHEMA_NAME" \
  DM_RAW_SOURCE="$DM_RAW_SOURCE" \
  DM_OUTPUT_DIR="$DM_OUTPUT_DIR" \
  DM_INPUT_DIR="$DM_INPUT_DIR" \
  DM_TRANS_SPEC_DIR="$DM_TRANS_SPEC_DIR" \
  DM_MAP_TARGET_SCHEMA="$DM_MAP_TARGET_SCHEMA"

#------------------------------------------------------------------------------
# 6. Pipeline Completion
#------------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "✓ Pipeline completed successfully!"
echo "================================================================"
echo "Output Location: $DM_OUTPUT_DIR"
echo "================================================================"
