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
#   ./bdc-workflow.sh --schema <SCHEMA_NAME> --source <RAW_DATA_PATH> [OPTIONS]
#
# Required Parameters:
#   --schema      Name of the schema configuration (e.g., "FHS", "COPDGene")
#   --source      Path to the raw data source directory
#
# Optional Parameters:
#   --trans-spec  Alternate trans-spec source (OWNER/REPO[@REF][:PATH])
#   --workdir     Working directory for pipeline execution (default: /app)
#   --jobs        Number of parallel make jobs (default: 8)
#
# Examples:
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study --workdir /custom/path
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study --jobs 4
#   ./bdc-workflow.sh --schema FHS --source /data/raw/fhs_study \
#     --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main
#
# Environment:
#   - Designed to run within the dm-bip Docker container
#   - Expects /app as the default working directory
#   - Requires access to bdc-harmonized-variables and NHLBI-BDC-DMC-HM repos (cloned at /app/)
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
# Function: Display usage information
#------------------------------------------------------------------------------
usage() {
  cat << EOF
Usage: $0 --schema <SCHEMA_NAME> --source <RAW_DATA_PATH> [OPTIONS]

Required Parameters:
  --schema      Name of the schema configuration for the study
  --source      Path to the raw data source directory

Optional Parameters:
  --trans-spec  Alternate trans-spec source (OWNER/REPO[@REF][:PATH])
  --workdir     Working directory for pipeline execution (default: /app)
  --jobs        Number of parallel make jobs (default: 8)

Examples:
  $0 --schema FHS --source /data/raw/fhs_study
  $0 --schema FHS --source /data/raw/fhs_study \
     --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main
  $0 --schema FHS --source /data/raw/fhs_study --jobs 4

EOF
  exit "${1:-1}"
}

#------------------------------------------------------------------------------
# Initialize variables
#------------------------------------------------------------------------------
DM_SCHEMA_NAME=""
DM_RAW_SOURCE=""
TRANS_SPEC_SLUG=""
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
    --trans-spec)
      [[ -z "${2:-}" || "$2" == --* ]] && { echo "Error: --trans-spec requires a value (OWNER/REPO[@REF][:PATH])"; exit 1; }
      TRANS_SPEC_SLUG="$2"
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
# 3. Pull Repos and Resolve Trans-Spec
#------------------------------------------------------------------------------
TRANS_SPEC_REPO_DIR=""
TRANS_SPEC_EXPLICIT_PATH=""

if [[ "${BDC_PULL_LATEST:-false}" == "true" ]]; then
  echo "BDC_PULL_LATEST=true — checking network connectivity..."
  if timeout 10 curl -sf --max-time 5 https://github.com > /dev/null 2>&1; then
    NETWORK_AVAILABLE=true
    echo "  Network available — pulling latest from cloned repos..."
    # Always pull the target schema repo
    if [[ -d /app/NHLBI-BDC-DMC-HM/.git ]]; then
      echo "  Updating NHLBI-BDC-DMC-HM..."
      if ! timeout 30 git -C /app/NHLBI-BDC-DMC-HM pull --ff-only 2>&1; then
        echo "  WARNING: Failed to pull NHLBI-BDC-DMC-HM, continuing with build-time version"
      fi
    fi
    # Pull the default trans-spec repo unless overridden by --trans-spec
    if [[ -z "$TRANS_SPEC_SLUG" ]] && [[ -d /app/bdc-harmonized-variables/.git ]]; then
      echo "  Updating bdc-harmonized-variables..."
      if ! timeout 30 git -C /app/bdc-harmonized-variables pull --ff-only 2>&1; then
        echo "  WARNING: Failed to pull bdc-harmonized-variables, continuing with build-time version"
      fi
    fi
    echo "✓ Repos updated"
  else
    NETWORK_AVAILABLE=false
    echo "  WARNING: No network access (github.com unreachable), using build-time versions"
  fi
fi

# Handle --trans-spec slug: clone alternate trans-spec repo (dev mode only)
if [[ -n "$TRANS_SPEC_SLUG" ]]; then
  if [[ "${BDC_PULL_LATEST:-false}" != "true" ]]; then
    echo "ERROR: --trans-spec is only supported when BDC_PULL_LATEST=true (dev mode)"
    exit 1
  fi
  if [[ "${NETWORK_AVAILABLE:-false}" != "true" ]]; then
    echo "ERROR: --trans-spec requires network access but github.com is unreachable"
    exit 1
  fi

  # Parse slug: OWNER/REPO[@REF][:PATH]
  slug_remainder="$TRANS_SPEC_SLUG"

  # Extract :PATH (if present)
  if [[ "$slug_remainder" == *:* ]]; then
    TRANS_SPEC_EXPLICIT_PATH="${slug_remainder##*:}"
    slug_remainder="${slug_remainder%:*}"
  fi

  # Extract @REF (if present)
  TRANS_SPEC_REF=""
  if [[ "$slug_remainder" == *@* ]]; then
    TRANS_SPEC_REF="${slug_remainder##*@}"
    slug_remainder="${slug_remainder%@*}"
  fi

  # Validate OWNER/REPO format
  if [[ ! "$slug_remainder" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: Invalid --trans-spec slug '${TRANS_SPEC_SLUG}'" >&2
    echo "       Expected OWNER/REPO[@REF][:PATH]" >&2
    exit 1
  fi

  TRANS_SPEC_OWNER_REPO="$slug_remainder"
  TRANS_SPEC_REPO_NAME="${TRANS_SPEC_OWNER_REPO##*/}"
  TRANS_SPEC_REPO_DIR="/app/${TRANS_SPEC_REPO_NAME}"

  # Validate explicit path (no traversal or absolute paths)
  if [[ -n "$TRANS_SPEC_EXPLICIT_PATH" ]]; then
    if [[ "$TRANS_SPEC_EXPLICIT_PATH" == /* || "$TRANS_SPEC_EXPLICIT_PATH" == *".."* ]]; then
      echo "ERROR: Explicit trans-spec path must be relative and not contain '..': $TRANS_SPEC_EXPLICIT_PATH" >&2
      exit 1
    fi
  fi

  echo "Trans-spec override: ${TRANS_SPEC_OWNER_REPO}"
  [[ -n "$TRANS_SPEC_REF" ]] && echo "  Ref: ${TRANS_SPEC_REF}"
  [[ -n "$TRANS_SPEC_EXPLICIT_PATH" ]] && echo "  Path: ${TRANS_SPEC_EXPLICIT_PATH}"

  # Clone or update the repo
  EXPECTED_URL="https://github.com/${TRANS_SPEC_OWNER_REPO}.git"
  if [[ -d "${TRANS_SPEC_REPO_DIR}/.git" ]]; then
    # Verify the existing clone points to the requested repo
    CURRENT_URL=$(git -C "$TRANS_SPEC_REPO_DIR" remote get-url origin 2>/dev/null || true)
    if [[ "$CURRENT_URL" != "$EXPECTED_URL" ]]; then
      echo "  Updating origin URL: ${CURRENT_URL} → ${EXPECTED_URL}"
      git -C "$TRANS_SPEC_REPO_DIR" remote set-url origin "$EXPECTED_URL"
    fi
    echo "  Repo already present at ${TRANS_SPEC_REPO_DIR}, fetching..."
    timeout 30 git -C "$TRANS_SPEC_REPO_DIR" fetch origin 2>&1
  else
    echo "  Cloning ${TRANS_SPEC_OWNER_REPO}..."
    timeout 60 git clone "$EXPECTED_URL" "$TRANS_SPEC_REPO_DIR" 2>&1
  fi

  # Checkout the requested ref (or pull default branch)
  if [[ -n "$TRANS_SPEC_REF" ]]; then
    echo "  Checking out ${TRANS_SPEC_REF}..."
    git -C "$TRANS_SPEC_REPO_DIR" checkout "$TRANS_SPEC_REF" 2>&1 \
      || git -C "$TRANS_SPEC_REPO_DIR" checkout "origin/${TRANS_SPEC_REF}" 2>&1
  else
    git -C "$TRANS_SPEC_REPO_DIR" pull --ff-only 2>&1 || true
  fi

  echo "✓ Trans-spec repo ready: ${TRANS_SPEC_REPO_DIR} ($(git -C "$TRANS_SPEC_REPO_DIR" rev-parse --short HEAD))"
fi

#------------------------------------------------------------------------------
# 4. Configuration and Path Setup
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
# Resolve trans-spec directory based on --trans-spec slug or default
if [[ -n "$TRANS_SPEC_EXPLICIT_PATH" ]]; then
  # Explicit path from slug
  DM_TRANS_SPEC_DIR="${TRANS_SPEC_REPO_DIR}/${TRANS_SPEC_EXPLICIT_PATH}"
  if [[ ! -d "$DM_TRANS_SPEC_DIR" ]]; then
    echo "ERROR: Explicit trans-spec path not found: $DM_TRANS_SPEC_DIR"
    exit 1
  fi
elif [[ -n "$TRANS_SPEC_REPO_DIR" ]]; then
  # Auto-detect layout from repo contents
  if [[ -d "${TRANS_SPEC_REPO_DIR}/priority_variables_transform" ]]; then
    # NHLBI-BDC-DMC-HV layout
    DM_TRANS_SPEC_DIR="${TRANS_SPEC_REPO_DIR}/priority_variables_transform/${DM_SCHEMA_NAME}-ingest"
  elif [[ -d "${TRANS_SPEC_REPO_DIR}/trans_specs" ]]; then
    # bdc-harmonized-variables layout (versioned subdirectories)
    TRANS_SPEC_BASE="${TRANS_SPEC_REPO_DIR}/trans_specs/${DM_SCHEMA_NAME}"
    latest_version_dir=$(find "$TRANS_SPEC_BASE" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -1)
    if [[ -z "${latest_version_dir:-}" ]]; then
      echo "ERROR: No trans-spec version directory found under $TRANS_SPEC_BASE"
      exit 1
    fi
    DM_TRANS_SPEC_DIR="${TRANS_SPEC_BASE}/${latest_version_dir}"
  else
    echo "ERROR: Cannot auto-detect trans-spec layout in ${TRANS_SPEC_REPO_DIR}"
    echo "       Use OWNER/REPO@REF:PATH to specify the path explicitly"
    exit 1
  fi
  if [[ ! -d "$DM_TRANS_SPEC_DIR" ]]; then
    echo "ERROR: Auto-detected trans-spec directory not found: $DM_TRANS_SPEC_DIR"
    echo "       Use OWNER/REPO@REF:PATH to specify the path explicitly"
    exit 1
  fi
else
  # Default: bdc-harmonized-variables (build-time clone)
  TRANS_SPEC_BASE="/app/bdc-harmonized-variables/trans_specs/${DM_SCHEMA_NAME}"
  latest_version_dir=$(find "$TRANS_SPEC_BASE" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -1)
  if [[ -z "${latest_version_dir:-}" ]]; then
    echo "ERROR: No trans-spec version directory found under $TRANS_SPEC_BASE"
    exit 1
  fi
  DM_TRANS_SPEC_DIR="${TRANS_SPEC_BASE}/${latest_version_dir}"
fi
echo "  Trans-spec version:   ${DM_TRANS_SPEC_DIR}"
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
# 5. Create Workspace Directories
#------------------------------------------------------------------------------
echo ""
echo "Creating workspace directories..."
mkdir -p "$PROCESSED_DIR"
mkdir -p "$DM_OUTPUT_DIR"
mkdir -p "$DM_INPUT_DIR"
echo "✓ Workspace directories created"

#------------------------------------------------------------------------------
# 6. Execute Data Harmonization Pipeline
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
# BDC_PULL_LATEST=true means dev mode: pull latest specs from default branches
# and run mapping in non-strict mode so all errors are logged in one pass.
# In prod (BDC_PULL_LATEST=false/unset), strict mode is the default — mapping
# fails on the first error. (TODO: rename BDC_PULL_LATEST to BDC_DEV_MODE)
DM_MAP_STRICT_ARG=""
if [ "${BDC_PULL_LATEST:-false}" = "true" ]; then
  DM_MAP_STRICT_ARG="DM_MAP_STRICT=false"
fi

make -j "$MAKE_JOBS" pipeline \
  -C "$WORKING_DIR" \
  DM_SCHEMA_NAME="$DM_SCHEMA_NAME" \
  DM_RAW_SOURCE="$DM_RAW_SOURCE" \
  DM_OUTPUT_DIR="$DM_OUTPUT_DIR" \
  DM_INPUT_DIR="$DM_INPUT_DIR" \
  DM_TRANS_SPEC_DIR="$DM_TRANS_SPEC_DIR" \
  DM_MAP_TARGET_SCHEMA="$DM_MAP_TARGET_SCHEMA" \
  DM_EXTERNAL_REPOS="/app/NHLBI-BDC-DMC-HM /app/bdc-harmonized-variables" \
  $DM_MAP_STRICT_ARG

#------------------------------------------------------------------------------
# 7. Pipeline Completion
#------------------------------------------------------------------------------
echo ""
echo "================================================================"
echo "✓ Pipeline completed successfully!"
echo "================================================================"
echo "Output Location: $PROCESSED_DIR"
echo "================================================================"

#------------------------------------------------------------------------------
# 8. Copy Log Files and Build Artifacts to Processed Directory
#    NOTE: Must remain last — any echoes after this won't appear in the log
#------------------------------------------------------------------------------
cp /Dockerfile.archived "$PROCESSED_DIR/"
find "${HOME}" -maxdepth 1 -name "*.log" -exec cp {} "$PROCESSED_DIR/" \;
