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
#   ./bdc-workflow.sh --schema <SCHEMA_NAME> --source <RAW_DATA_PATH> [--workdir <PATH>] [--jobs <N>]
#
# Required Parameters:
#   --schema    Name of the schema configuration (e.g., "FHS", "COPDGene")
#   --source    Path to the raw data source directory
#
# Optional Parameters:
#   --workdir   Working directory for pipeline execution (default: /app)
#   --jobs      Number of parallel make jobs (default: 8)
#
# Examples:
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study --workdir /custom/path
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study --jobs 4
#
# Environment:
#   - Designed to run within the dm-bip Docker container
#   - Expects /app as the default working directory
#   - Requires access to NHLBI-BDC-DMC-HV and NHLBI-BDC-DMC-HM repos
#   - Set BDC_PULL_LATEST=true to git-pull cloned repos at startup (for dev/testing)
#
# Output:
#   - Cleaned source data in ${HOME}/<source>_CleanedSource/
#   - Harmonized BDCHM data in ${HOME}/<source>_BDCHM/
################################################################################

# Exit immediately if a command exits with a non-zero status
# -e: exit on error, -u: exit on undefined variable, -o pipefail: catch pipe errors
set -euo pipefail

# Capture stderr to a log file while still passing it through to the original stderr
exec 2> >(tee -a "${HOME}/stderr_internal_copy.log" >&2)

#------------------------------------------------------------------------------
# Pull latest cloned repos if BDC_PULL_LATEST is set (for dev/testing)
#------------------------------------------------------------------------------
if [[ "${BDC_PULL_LATEST:-false}" == "true" ]]; then
  echo "BDC_PULL_LATEST=true — pulling latest from cloned repos..."
  for repo in /app/bdc-harmonized-variables /app/NHLBI-BDC-DMC-HM; do
    if [[ -d "$repo/.git" ]]; then
      echo "  Updating $(basename "$repo")..."
      if ! git -C "$repo" pull --ff-only 2>&1; then
        echo "  WARNING: Failed to pull $(basename "$repo"), continuing with build-time version"
      fi
    fi
  done
  echo "✓ Repo update check complete"
fi

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
  --workdir   Working directory for pipeline execution (default: /app)
  --jobs      Number of parallel make jobs (default: 8)

Examples:
  $0 --schema FHS --source /data/raw/fhs_study
  $0 --schema FHS --source /data/raw/fhs_study --workdir /custom/path
  $0 --schema FHS --source /data/raw/fhs_study --jobs 4

EOF
  exit "${1:-1}"
}

#------------------------------------------------------------------------------
# Initialize variables
#------------------------------------------------------------------------------
DM_SCHEMA_NAME=""
DM_RAW_SOURCE=""
WORKING_DIR="/app"  # Default working directory
MAKE_JOBS=8         # Default parallel jobs

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
      [[ -z "${2:-}" || "$2" == --* ]] && { echo "Error: --schema requires a value"; exit 1; }
      DM_SCHEMA_NAME="$2"
      shift 2
      ;;
    --source)
      [[ -z "${2:-}" || "$2" == --* ]] && { echo "Error: --source requires a value"; exit 1; }
      DM_RAW_SOURCE="$2"
      shift 2
      ;;
    --workdir)
      [[ -z "${2:-}" || "$2" == --* ]] && { echo "Error: --workdir requires a value"; exit 1; }
      WORKING_DIR="$2"
      shift 2
      ;;
    --jobs)
      [[ -z "${2:-}" || "$2" == --* ]] && { echo "Error: --jobs requires a positive integer value"; exit 1; }
      if ! [[ "$2" =~ ^[1-9][0-9]*$ ]]; then
        echo "Error: --jobs value must be a positive integer (got '$2')"
        exit 1
      fi
      MAKE_JOBS="$2"
      shift 2
      ;;
    -h|--help)
      usage 0
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
echo "Parallel Jobs: $MAKE_JOBS"
echo "================================================================"

# Extract the base name from the raw source path
RAW_DIR_NAME=$(basename "$DM_RAW_SOURCE")
OUTPUT_NAME="${RAW_DIR_NAME}_BDCHM"

# Define the top-level processed output directory (created before the pipeline runs)
PROCESSED_DATETIME=$(date +"%Y%m%d_%H%M%S")
PROCESSED_DIR="${HOME}/DMC_${RAW_DIR_NAME}_${DM_SCHEMA_NAME}_Processed_${PROCESSED_DATETIME}"

# Define output directories inside the processed directory
DM_OUTPUT_DIR="${PROCESSED_DIR}/${OUTPUT_NAME}"
DM_INPUT_DIR="${PROCESSED_DIR}/${RAW_DIR_NAME}_CleanedSource"

# Define paths to external dependencies (within container)
# Find the latest version directory for this study's trans-specs
TRANS_SPEC_BASE="/app/bdc-harmonized-variables/trans_specs/${DM_SCHEMA_NAME}"
DM_TRANS_SPEC_DIR=$(find "$TRANS_SPEC_BASE" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | sort | tail -1)
if [[ -z "$DM_TRANS_SPEC_DIR" ]]; then
  echo "ERROR: No trans-spec version directory found under $TRANS_SPEC_BASE"
  exit 1
fi
echo "  Trans-spec version:   $(basename "$DM_TRANS_SPEC_DIR")"
DM_MAP_TARGET_SCHEMA="/app/NHLBI-BDC-DMC-HM/src/bdchm/schema/bdchm.yaml"

echo ""
echo "Configuration:"
echo "  Processed Directory:  $PROCESSED_DIR"
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
mkdir -p "$PROCESSED_DIR"
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
# -j allows up to $MAKE_JOBS parallel validation processes
make -j "$MAKE_JOBS" pipeline \
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
echo "Output Location: $PROCESSED_DIR"
echo "================================================================"

#------------------------------------------------------------------------------
# 7. Copy Log Files and Build Artifacts to Processed Directory
#    NOTE: Must remain last — any echoes after this won't appear in the log
#------------------------------------------------------------------------------
cp /Dockerfile.archived "$PROCESSED_DIR/"
find "${HOME}" -maxdepth 1 -name "*.log" -exec cp {} "$PROCESSED_DIR/" \;
