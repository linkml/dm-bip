#!/bin/bash
################################################################################
# HV-DataQC Cohort Fan-in Wrapper
################################################################################
# Description:
#   Runs the hv_dataqc source-vs-harmonized comparison for a whole cohort:
#     1. extract_source_summaries.py  → aggregate JSON from raw dbGaP TSVs
#     2. extract_harmonized_summaries.py → aggregate JSON from dm-bip mapped-data
#     3. compare (source vs. harmonized) → markdown + JSON report
#
#   Always exits 0. Internal command failures are logged to hv-dataqc.log
#   and recorded as {"status":"FAIL"} in compare/manifest.json.
#
#   Compare requires --dbgap-cache. When the cache is missing or the cohort
#   subdir is not present, the extracts still run but compare is skipped with
#   a WARN and the report is not generated.
#
# Usage:
#   ./hv-dataqc-cohort.sh \
#       --schema <COHORT> \
#       --source-root <cohort-raw-root> \
#       --mapped-data-dir <dir> [--mapped-data-dir <dir> ...] \
#       --yaml-dir <transform-yaml-dir> \
#       --hv-dataqc-root <hv-clone-for-hv_dataqc-code> \
#       [--dbgap-cache <dir>] \
#       --output-dir <dir>
#
# Design notes:
#   --yaml-dir and --hv-dataqc-root are independent so the cohort driver can
#   point at two different HV clones (release YAMLs vs. WIP hv_dataqc code).
#
#   Output subdir layout inside <output-dir> matches what run_extracts.sh
#   produces today:
#       source_<ts>/<cohort>_source_<ts>.json
#       harmonized_<ts>/<cohort>_harmonized_<ts>.json
#       latest_source -> source_<ts>
#       latest_harmonized -> harmonized_<ts>
#       compare/<cohort>_comparison_report.md
#       compare/<cohort>_comparison_results.json
#       compare/manifest.json
#       hv-dataqc.log
#
# Tracked in linkml/dm-bip#350.
################################################################################

set -uo pipefail

#------------------------------------------------------------------------------
# Args
#------------------------------------------------------------------------------
SCHEMA=""
SOURCE_ROOT=""
YAML_DIR=""
HV_DATAQC_ROOT=""
DBGAP_CACHE=""
OUTPUT_DIR=""
MAPPED_DATA_DIRS=()

usage() {
  cat << 'EOF'
Usage: hv-dataqc-cohort.sh
  --schema <COHORT>                Cohort name (e.g. SPIROMICS)
  --source-root <DIR>              Raw dbGaP root for the cohort
  --mapped-data-dir <DIR>          Repeatable. One per consent group.
  --yaml-dir <DIR>                 HV transform YAML dir for the cohort
  --hv-dataqc-root <DIR>           cwd for `python -m hv_dataqc.…`
  [--dbgap-cache <DIR>]            Cohort-specific dbGaP cache dir
                                   (contains pheno_variable_summaries/*.data_dict.xml).
                                   Passed directly — no cohort subdir is appended.
  --output-dir <DIR>               Where JSONs + compare report go
EOF
  exit "${1:-1}"
}
  --hv-dataqc-root <DIR>           HV clone whose hv_dataqc module to run
  [--dbgap-cache <DIR>]            Cache root containing <cohort>/pheno_variable_summaries/
  --output-dir <DIR>               Where JSONs + compare report go
EOF
  exit "${1:-1}"
}

[[ $# -eq 0 ]] && usage

while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema)          SCHEMA="${2:?}"; shift 2 ;;
    --source-root)     SOURCE_ROOT="${2:?}"; shift 2 ;;
    --mapped-data-dir) MAPPED_DATA_DIRS+=("${2:?}"); shift 2 ;;
    --yaml-dir)        YAML_DIR="${2:?}"; shift 2 ;;
    --hv-dataqc-root)  HV_DATAQC_ROOT="${2:?}"; shift 2 ;;
    --dbgap-cache)     DBGAP_CACHE="${2:?}"; shift 2 ;;
    --output-dir)      OUTPUT_DIR="${2:?}"; shift 2 ;;
    -h|--help)         usage 0 ;;
    *)                 echo "Unknown arg: $1" >&2; usage ;;
  esac
done

for var in SCHEMA SOURCE_ROOT YAML_DIR HV_DATAQC_ROOT OUTPUT_DIR; do
  if [[ -z "${!var}" ]]; then
    echo "ERROR: --${var,,} is required" >&2
    usage
  fi
done
if [[ ${#MAPPED_DATA_DIRS[@]} -eq 0 ]]; then
  echo "ERROR: at least one --mapped-data-dir is required" >&2
  usage
fi

mkdir -p "${OUTPUT_DIR}/compare"
LOG="${OUTPUT_DIR}/hv-dataqc.log"
: > "$LOG"

# All console output also goes into the log.
exec > >(tee -a "$LOG") 2>&1

#------------------------------------------------------------------------------
# Helpers
#------------------------------------------------------------------------------
SCHEMA_LOWER=$(echo "$SCHEMA" | tr '[:upper:]' '[:lower:]')

# --dbgap-cache is the cohort-specific directory, not the cache root.
# No cohort subdir is appended — the caller already provides the right path.
CACHE_DIR=""
if [[ -n "$DBGAP_CACHE" ]]; then
  if [[ -d "$DBGAP_CACHE" ]]; then
    CACHE_DIR="$DBGAP_CACHE"
  else
    echo "WARN: dbGaP cache dir not found: $DBGAP_CACHE (compare will be skipped)"
  fi
fi

# Capture HV clone commits so every artifact is self-describing.
YAML_COMMIT=$(git -C "$(dirname "$YAML_DIR")" rev-parse HEAD 2>/dev/null || echo "unknown")
YAML_BRANCH=$(git -C "$(dirname "$YAML_DIR")" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
DATAQC_COMMIT=$(git -C "$HV_DATAQC_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
DATAQC_BRANCH=$(git -C "$HV_DATAQC_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo "================================================================"
echo "HV-DataQC Cohort Fan-in"
echo "================================================================"
echo "Cohort:           $SCHEMA"
echo "Source root:      $SOURCE_ROOT"
echo "Mapped-data dirs: ${MAPPED_DATA_DIRS[*]}"
echo "YAML dir:         $YAML_DIR  (commit ${YAML_COMMIT:0:12}, branch $YAML_BRANCH)"
echo "hv_dataqc root:   $HV_DATAQC_ROOT  (commit ${DATAQC_COMMIT:0:12}, branch $DATAQC_BRANCH)"
echo "dbGaP cache:      ${CACHE_DIR:-<none — compare will be skipped>}"
echo "Output dir:       $OUTPUT_DIR"
echo "================================================================"

SOURCE_STATUS="SKIPPED"
HARMONIZED_STATUS="SKIPPED"
COMPARE_STATUS="SKIPPED"
OVERALL_STATUS="PASS"

# Wraps an internal command so its failure records but does not exit the script.
run_step() {
  local name="$1"; shift
  echo
  echo "--- $name ---"
  if "$@"; then
    echo "--- $name: OK ---"
    return 0
  else
    local rc=$?
    echo "--- $name: FAIL (exit $rc) ---" >&2
    OVERALL_STATUS="FAIL"
    return $rc
  fi
}

#------------------------------------------------------------------------------
# 1. extract_source
#------------------------------------------------------------------------------
extract_source_cmd=(
  uv run python -m hv_dataqc.extract_source.extract_source_summaries
    --cohort "$SCHEMA"
    --source-root "$SOURCE_ROOT"
    --yaml-dir "$YAML_DIR"
    --output-dir "$OUTPUT_DIR"
)
if [[ -n "$CACHE_DIR" ]]; then
  extract_source_cmd+=(--cache-dir "$CACHE_DIR")
fi

if (cd "$HV_DATAQC_ROOT" && run_step "extract_source" "${extract_source_cmd[@]}"); then
  SOURCE_STATUS="PASS"
else
  SOURCE_STATUS="FAIL"
fi

#------------------------------------------------------------------------------
# 2. extract_harmonized
#------------------------------------------------------------------------------
extract_harmonized_cmd=(
  uv run python -m hv_dataqc.extract_harmonized.extract_harmonized_summaries
    --cohort "$SCHEMA"
    --mapped-data-dirs "${MAPPED_DATA_DIRS[@]}"
    --output-dir "$OUTPUT_DIR"
)

if (cd "$HV_DATAQC_ROOT" && run_step "extract_harmonized" "${extract_harmonized_cmd[@]}"); then
  HARMONIZED_STATUS="PASS"
else
  HARMONIZED_STATUS="FAIL"
fi

#------------------------------------------------------------------------------
# 3. compare (requires --cache-dir; skip cleanly if missing)
#------------------------------------------------------------------------------
COMPARE_REPORT="${OUTPUT_DIR}/compare/${SCHEMA_LOWER}_comparison_report.md"
COMPARE_JSON="${OUTPUT_DIR}/compare/${SCHEMA_LOWER}_comparison_results.json"

# extract_source/extract_harmonized create timestamped subdirs and
# `latest_source` / `latest_harmonized` symlinks pointing at the newest run.
SOURCE_JSON=""
HARMONIZED_JSON=""
if [[ -L "${OUTPUT_DIR}/latest_source" ]]; then
  SOURCE_JSON=$(ls -t "${OUTPUT_DIR}/latest_source/${SCHEMA_LOWER}_source_"*.json 2>/dev/null | head -1 || true)
fi
if [[ -L "${OUTPUT_DIR}/latest_harmonized" ]]; then
  HARMONIZED_JSON=$(ls -t "${OUTPUT_DIR}/latest_harmonized/${SCHEMA_LOWER}_harmonized_"*.json 2>/dev/null | head -1 || true)
fi

if [[ -z "$CACHE_DIR" ]]; then
  echo
  echo "SKIP compare: no dbGaP cache available."
  COMPARE_STATUS="SKIPPED"
elif [[ -z "$SOURCE_JSON" || -z "$HARMONIZED_JSON" ]]; then
  echo
  echo "SKIP compare: missing extract JSON (source='${SOURCE_JSON:-<none>}', harmonized='${HARMONIZED_JSON:-<none>}')."
  COMPARE_STATUS="SKIPPED"
  OVERALL_STATUS="FAIL"
else
  compare_cmd=(
    uv run python -m hv_dataqc.compare
      --source "$SOURCE_JSON"
      --harmonized "$HARMONIZED_JSON"
      --cohort "$SCHEMA"
      --yaml-dir "$YAML_DIR"
      --cache-dir "$CACHE_DIR"
      --report "$COMPARE_REPORT"
      --json-report "$COMPARE_JSON"
  )
  if (cd "$HV_DATAQC_ROOT" && run_step "compare" "${compare_cmd[@]}"); then
    COMPARE_STATUS="PASS"
  else
    COMPARE_STATUS="FAIL"
  fi
fi

#------------------------------------------------------------------------------
# 4. manifest.json — self-describing artifact
#------------------------------------------------------------------------------
GENERATED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
mapped_json_array=$(printf '%s\n' "${MAPPED_DATA_DIRS[@]}" | awk 'BEGIN{p=""} {printf "%s\"%s\"", p, $0; p=","}')

cat > "${OUTPUT_DIR}/compare/manifest.json" << EOF
{
  "cohort": "${SCHEMA}",
  "generated_at": "${GENERATED_AT}",
  "hv_yaml_commit": "${YAML_COMMIT}",
  "hv_yaml_branch": "${YAML_BRANCH}",
  "hv_dataqc_commit": "${DATAQC_COMMIT}",
  "hv_dataqc_branch": "${DATAQC_BRANCH}",
  "yaml_dir": "${YAML_DIR}",
  "hv_dataqc_root": "${HV_DATAQC_ROOT}",
  "dbgap_cache_dir": "${CACHE_DIR}",
  "source_root": "${SOURCE_ROOT}",
  "mapped_data_dirs": [${mapped_json_array}],
  "source_json": "${SOURCE_JSON}",
  "harmonized_json": "${HARMONIZED_JSON}",
  "report": "${COMPARE_REPORT}",
  "results_json": "${COMPARE_JSON}",
  "status": {
    "extract_source": "${SOURCE_STATUS}",
    "extract_harmonized": "${HARMONIZED_STATUS}",
    "compare": "${COMPARE_STATUS}",
    "overall": "${OVERALL_STATUS}"
  }
}
EOF

echo
echo "================================================================"
echo "HV-DataQC status: overall=${OVERALL_STATUS}"
echo "  extract_source:     ${SOURCE_STATUS}"
echo "  extract_harmonized: ${HARMONIZED_STATUS}"
echo "  compare:            ${COMPARE_STATUS}"
echo "Manifest: ${OUTPUT_DIR}/compare/manifest.json"
echo "================================================================"

# Always exit 0 — status carried by manifest.json and (in cohort mode) the driver.
exit 0
