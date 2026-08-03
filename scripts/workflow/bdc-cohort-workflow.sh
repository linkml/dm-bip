#!/bin/bash
################################################################################
# BDC Cohort Harmonization Workflow — Parallel Multi-Consent Execution Mode
################################################################################
# Description:
#   Runs the dm-bip harmonization pipeline for every consent group in a
#   single cohort inside one container/task, then runs the hv_dataqc
#   source-vs-harmonized comparison across all consent groups.
#
#   This is the Parallel Multi-Consent Execution Mode entry point.
#   The Single Consent Execution Mode entry point (bdc-workflow.sh) is
#   unchanged and still runs one consent group at a time. This script invokes
#   bdc-workflow.sh once per consent group under GNU parallel.
#
#   Parallelism: per-consent workers run under GNU parallel, bounded by
#   --consent-parallelism (default: min(#consent-groups, max(1, floor(vCPU/4)))).
#   Each per-consent worker runs `bdc-workflow.sh` unchanged, with per-consent
#   HOME= and UV_CACHE_DIR= for filesystem isolation. --consent-parallelism 1
#   is exactly serial.
#
#   Always exits 0 (except for a pre-flight failure resolving --trans-spec or
#   --hv-dataqc-branch under strict mode — those are setup failures).
#
# Usage:
#   ./bdc-cohort-workflow.sh \
#       --schema <COHORT> \
#       --consent-group <dir> [--consent-group <dir> ...] \
#       [--dbgap-cache <dir>] \
#       [--allow-fail <cg-name> ...] \
#       [--strict-consent-groups true|false] \
#       [--strict-hv-dataqc true|false] \
#       [--consent-parallelism N] \
#       [--jobs 4] \
#       [--output-root <dir>] \
#       [--hv-dataqc-branch <name>] \
#       [--strict-hv-dataqc-branch true|false] \
#       [--trans-spec OWNER/REPO[@REF][:PATH]] \
#       [--profile]
#
# Tracked in linkml/dm-bip#350.
################################################################################

set -uo pipefail

#------------------------------------------------------------------------------
# Defaults
#------------------------------------------------------------------------------
SCHEMA=""
DBGAP_CACHE=""
STRICT_CONSENT_GROUPS="true"
STRICT_HV_DATAQC="true"
CONSENT_PARALLELISM=""
JOBS="8"
OUTPUT_ROOT="${HOME}"
HV_DATAQC_BRANCH=""
STRICT_HV_DATAQC_BRANCH="true"
TRANS_SPEC=""
DM_MAP_PROFILE="${DM_MAP_PROFILE:-false}"

CONSENT_GROUPS=()
ALLOW_FAIL=()

# HV clone that hosts hv_dataqc/ code. bdc-workflow.sh's own trans-spec
# discovery is untouched — YAML source is chosen via --trans-spec (forwarded
# to bdc-workflow.sh) or defaults to whatever the image bakes as its trans-spec
# repo (today: /app/bdc-harmonized-variables).
HV_DATAQC_CLONE="${HV_DATAQC_CLONE:-/app/NHLBI-BDC-DMC-HV-dataqc}"

usage() {
  cat << 'EOF'
Usage: bdc-cohort-workflow.sh
  --schema <COHORT>                 Cohort name (e.g. COPDGene)
  --consent-group <DIR>             Repeatable. One per consent group.
  [--dbgap-cache <DIR>]             Mounted dbGaP cache root
  [--allow-fail <CG_NAME> ...]      Repeatable. Consent groups tolerated to fail.
  [--strict-consent-groups <bool>]  Default true (fail-fast loop)
  [--strict-hv-dataqc <bool>]       Default true (skip hv_dataqc on unauth. failure)
  [--strict-hv-dataqc-branch <bool>] Default true (fail if hv_dataqc branch fetch fails)
  [--consent-parallelism <N>]       Default: computed from vCPU.
  [--jobs <N>]                      per-consent make -j; default 8
  [--output-root <DIR>]             Default $HOME
  [--hv-dataqc-branch <name>]       Override hv_dataqc clone branch (hv_dataqc code only)
  [--trans-spec OWNER/REPO[@REF][:PATH]]  Alternate YAML source. Resolved to a SHA at cohort-workflow
                                          startup and pre-checked-out once; workers see
                                          DM_TRANS_SPEC_DIR_PREBUILT and skip all git ops.
  [--profile]                       Forwarded to bdc-workflow.sh
EOF
  exit "${1:-1}"
}

[[ $# -eq 0 ]] && usage

while [[ $# -gt 0 ]]; do
  case "$1" in
    --schema)                     SCHEMA="${2:?}"; shift 2 ;;
    --consent-group)              CONSENT_GROUPS+=("${2:?}"); shift 2 ;;
    --dbgap-cache)                DBGAP_CACHE="${2:?}"; shift 2 ;;
    --allow-fail)                 ALLOW_FAIL+=("${2:?}"); shift 2 ;;
    --strict-consent-groups)      STRICT_CONSENT_GROUPS="${2:?}"; shift 2 ;;
    --strict-hv-dataqc)           STRICT_HV_DATAQC="${2:?}"; shift 2 ;;
    --strict-hv-dataqc-branch)    STRICT_HV_DATAQC_BRANCH="${2:?}"; shift 2 ;;
    --consent-parallelism)        CONSENT_PARALLELISM="${2:?}"; shift 2 ;;
    --jobs)                       JOBS="${2:?}"; shift 2 ;;
    --output-root)                OUTPUT_ROOT="${2:?}"; shift 2 ;;
    --hv-dataqc-branch)           HV_DATAQC_BRANCH="${2:?}"; shift 2 ;;
    --trans-spec)                 TRANS_SPEC="${2:?}"; shift 2 ;;
    --profile)                    DM_MAP_PROFILE="true"; shift ;;
    -h|--help)                    usage 0 ;;
    *)                            echo "Unknown arg: $1" >&2; usage ;;
  esac
done

if [[ -z "$SCHEMA" ]]; then
  echo "ERROR: --schema is required" >&2; usage
fi
if [[ ${#CONSENT_GROUPS[@]} -eq 0 ]]; then
  echo "ERROR: at least one --consent-group is required" >&2; usage
fi

#------------------------------------------------------------------------------
# Set up top-level output directory
#------------------------------------------------------------------------------
RUN_TS=$(date +"%Y%m%d_%H%M%S")
TOP="${OUTPUT_ROOT}/DMC_${SCHEMA}_${RUN_TS}"
mkdir -p "${TOP}/consent_groups" "${TOP}/hv_dataqc" "${TOP}/logs"

DRIVER_LOG="${TOP}/logs/cohort-workflow.log"
: > "$DRIVER_LOG"
exec > >(tee -a "$DRIVER_LOG") 2>&1

STATUS_TSV="${TOP}/consent_group_status.tsv"
MANIFEST="${TOP}/run_manifest.yaml"
printf 'consent_group\tstatus\tduration_sec\tsource_dir\toutput_dir\tnotes\n' > "$STATUS_TSV"

# Auto-compute consent parallelism if not provided.
if [[ -z "$CONSENT_PARALLELISM" ]]; then
  vcpu=$(nproc 2>/dev/null || echo 8)
  # Peak validate-step concurrency ~= CONSENT_PARALLELISM * JOBS. Keep ~= vCPU.
  by_cpu=$(( vcpu / JOBS ))
  (( by_cpu < 1 )) && by_cpu=1
  n_cg=${#CONSENT_GROUPS[@]}
  if (( by_cpu < n_cg )); then
    CONSENT_PARALLELISM=$by_cpu
  else
    CONSENT_PARALLELISM=$n_cg
  fi
fi

#------------------------------------------------------------------------------
# --trans-spec handling
#------------------------------------------------------------------------------
# This script accepts the same --trans-spec slug that bdc-workflow.sh accepts,
# but does the git dance ONCE at startup rather than N times inside each
# parallel worker. This avoids the .git/index.lock race that made concurrent
# --trans-spec workers unsafe. Workers see DM_TRANS_SPEC_DIR_PREBUILT and skip
# discovery/fetch/checkout entirely (see bdc-workflow.sh, linkml/dm-bip#350).
resolve_trans_spec_sha() {
  local slug="$1"
  local remainder="$slug"
  local explicit_path_suffix=""
  local ref=""
  if [[ "$remainder" == *:* ]]; then
    explicit_path_suffix=":${remainder##*:}"
    remainder="${remainder%:*}"
  fi
  if [[ "$remainder" == *@* ]]; then
    ref="${remainder##*@}"
    remainder="${remainder%@*}"
  fi
  local repo="$remainder"

  # If ref is already a full/short SHA, pass through.
  if [[ -n "$ref" ]] && [[ "$ref" =~ ^[0-9a-f]{7,40}$ ]]; then
    echo "${repo}|${ref}|${explicit_path_suffix#:}"
    return
  fi
  [[ -z "$ref" ]] && ref="HEAD"

  # Resolve branch/tag to a SHA via ls-remote (one call, no local clone required).
  local sha
  sha=$(git ls-remote "https://github.com/${repo}.git" "${ref}" 2>/dev/null | awk 'NR==1 {print $1}')
  if [[ -z "$sha" ]]; then
    # Annotated-tag dereference form.
    sha=$(git ls-remote "https://github.com/${repo}.git" "refs/tags/${ref}^{}" 2>/dev/null | awk 'NR==1 {print $1}')
  fi
  if [[ -z "$sha" ]]; then
    echo "ERROR: could not resolve ${repo}@${ref} via git ls-remote" >&2
    return 1
  fi
  echo "${repo}|${sha}|${explicit_path_suffix#:}"
}

# Given a checked-out trans-spec clone dir and (optionally) an explicit
# in-repo subpath, return the DM_TRANS_SPEC_DIR bdc-workflow.sh should use.
resolve_yaml_dir_in_clone() {
  local repo_dir="$1"
  local schema="$2"
  local explicit_path="$3"

  if [[ -n "$explicit_path" ]]; then
    echo "${repo_dir}/${explicit_path}"
    return
  fi
  if [[ -d "${repo_dir}/priority_variables_transform" ]]; then
    echo "${repo_dir}/priority_variables_transform/${schema}-ingest"
    return
  fi
  if [[ -d "${repo_dir}/trans_specs" ]]; then
    local base="${repo_dir}/trans_specs/${schema}"
    local latest
    latest=$(find "$base" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -1)
    if [[ -n "$latest" ]]; then
      echo "${base}/${latest}"
      return
    fi
  fi
  echo ""
}

# Same default resolution bdc-workflow.sh uses when --trans-spec is not set:
# /app/bdc-harmonized-variables/trans_specs/<SCHEMA>/<latest_version>.
default_baked_yaml_dir() {
  local schema="$1"
  local base="/app/bdc-harmonized-variables/trans_specs/${schema}"
  local latest
  latest=$(find "$base" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort -V | tail -1)
  [[ -n "$latest" ]] && echo "${base}/${latest}"
}

TRANS_SPEC_REPO=""
TRANS_SPEC_SHA=""
TRANS_SPEC_EXPLICIT_PATH=""
TRANS_SPEC_REPO_DIR=""
PREBUILT_YAML_DIR=""

if [[ -n "$TRANS_SPEC" ]]; then
  echo
  echo "--- Resolving --trans-spec ${TRANS_SPEC} ---"
  parsed=$(resolve_trans_spec_sha "$TRANS_SPEC") || {
    echo "ERROR: could not resolve --trans-spec '${TRANS_SPEC}'" >&2
    exit 1
  }
  IFS='|' read -r TRANS_SPEC_REPO TRANS_SPEC_SHA TRANS_SPEC_EXPLICIT_PATH <<< "$parsed"
  TRANS_SPEC_REPO_DIR="/app/${TRANS_SPEC_REPO##*/}"
  echo "  repo: ${TRANS_SPEC_REPO}"
  echo "  sha:  ${TRANS_SPEC_SHA}"
  [[ -n "$TRANS_SPEC_EXPLICIT_PATH" ]] && echo "  path: ${TRANS_SPEC_EXPLICIT_PATH}"

  # Pre-clone / pre-checkout ONCE. Workers never touch git.
  if [[ -d "${TRANS_SPEC_REPO_DIR}/.git" ]]; then
    current_url=$(git -C "$TRANS_SPEC_REPO_DIR" remote get-url origin 2>/dev/null || true)
    expected_url="https://github.com/${TRANS_SPEC_REPO}.git"
    if [[ "$current_url" != "$expected_url" ]]; then
      echo "  updating origin URL: ${current_url} -> ${expected_url}"
      git -C "$TRANS_SPEC_REPO_DIR" remote set-url origin "$expected_url"
    fi
    git -C "$TRANS_SPEC_REPO_DIR" fetch --depth 1 origin "$TRANS_SPEC_SHA" 2>&1 || \
      git -C "$TRANS_SPEC_REPO_DIR" fetch origin 2>&1
  else
    echo "  cloning ${TRANS_SPEC_REPO} -> ${TRANS_SPEC_REPO_DIR}"
    git clone --depth 1 "https://github.com/${TRANS_SPEC_REPO}.git" "$TRANS_SPEC_REPO_DIR"
    git -C "$TRANS_SPEC_REPO_DIR" fetch --depth 1 origin "$TRANS_SPEC_SHA" 2>&1 || \
      git -C "$TRANS_SPEC_REPO_DIR" fetch origin 2>&1
  fi
  git -C "$TRANS_SPEC_REPO_DIR" checkout "$TRANS_SPEC_SHA"
  echo "  checked out $(git -C "$TRANS_SPEC_REPO_DIR" rev-parse --short HEAD)"

  PREBUILT_YAML_DIR=$(resolve_yaml_dir_in_clone "$TRANS_SPEC_REPO_DIR" "$SCHEMA" "$TRANS_SPEC_EXPLICIT_PATH")
  if [[ -z "$PREBUILT_YAML_DIR" || ! -d "$PREBUILT_YAML_DIR" ]]; then
    echo "ERROR: could not resolve YAML dir under ${TRANS_SPEC_REPO_DIR} for schema ${SCHEMA}" >&2
    echo "       Consider supplying an explicit path: OWNER/REPO@REF:PATH" >&2
    exit 1
  fi
  echo "  YAML dir: ${PREBUILT_YAML_DIR}"
else
  PREBUILT_YAML_DIR=$(default_baked_yaml_dir "$SCHEMA")
fi

#------------------------------------------------------------------------------
# --hv-dataqc-branch (safe to check out at startup; hv_dataqc runs once)
#------------------------------------------------------------------------------
checkout_hv_dataqc_branch() {
  local branch="$1"
  echo
  echo "--- hv-dataqc-branch: checkout $branch in $HV_DATAQC_CLONE ---"
  if ! git -C "$HV_DATAQC_CLONE" fetch --depth 1 origin "$branch" 2>&1; then
    echo "ERROR: git fetch --depth 1 origin $branch failed in $HV_DATAQC_CLONE" >&2
    return 1
  fi
  # Create a local branch at FETCH_HEAD so the branch name is resolvable.
  # If the local branch already exists (re-run), just check it out directly.
  if ! git -C "$HV_DATAQC_CLONE" checkout -b "$branch" FETCH_HEAD 2>&1; then
    if ! git -C "$HV_DATAQC_CLONE" checkout "$branch" 2>&1; then
      echo "ERROR: git checkout $branch failed in $HV_DATAQC_CLONE" >&2
      return 1
    fi
    git -C "$HV_DATAQC_CLONE" reset --hard FETCH_HEAD 2>&1
  fi
  echo "hv-dataqc-branch now at $(git -C "$HV_DATAQC_CLONE" rev-parse --short HEAD)"
  return 0
}

if [[ -n "$HV_DATAQC_BRANCH" ]]; then
  if ! checkout_hv_dataqc_branch "$HV_DATAQC_BRANCH"; then
    if [[ "$STRICT_HV_DATAQC_BRANCH" == "true" ]]; then
      echo "FATAL: --hv-dataqc-branch fetch/checkout failed under --strict-hv-dataqc-branch true" >&2
      exit 1
    fi
    echo "WARN: continuing with baked hv-dataqc-branch"
  fi
fi

HV_DATAQC_COMMIT=$(git -C "$HV_DATAQC_CLONE" rev-parse HEAD 2>/dev/null || echo "unknown")
HV_DATAQC_BRANCH_RESOLVED=$(git -C "$HV_DATAQC_CLONE" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
HM_COMMIT=$(git -C /app/NHLBI-BDC-DMC-HM rev-parse HEAD 2>/dev/null || echo "unknown")
HM_BRANCH=$(git -C /app/NHLBI-BDC-DMC-HM rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

echo "================================================================"
echo "BDC Cohort Harmonization Workflow (Parallel Multi-Consent Execution Mode)"
echo "================================================================"
echo "Schema:              $SCHEMA"
echo "Consent groups (${#CONSENT_GROUPS[@]}):"
for cg in "${CONSENT_GROUPS[@]}"; do echo "    $cg"; done
if [[ ${#ALLOW_FAIL[@]} -gt 0 ]]; then
  echo "Allow-fail:          ${ALLOW_FAIL[*]}"
fi
echo "dbGaP cache:         ${DBGAP_CACHE:-<none>}"
echo "Strict consent grps: $STRICT_CONSENT_GROUPS"
echo "Strict hv-dataqc:    $STRICT_HV_DATAQC"
echo "Strict hv-dataqc-br: $STRICT_HV_DATAQC_BRANCH"
echo "Jobs (per consent):  $JOBS"
echo "Consent parallelism: $CONSENT_PARALLELISM"
echo "trans-spec (input):  ${TRANS_SPEC:-<none — using baked default>}"
echo "trans-spec (SHA):    ${TRANS_SPEC_SHA:-<none>}"
echo "hv_dataqc clone:     $HV_DATAQC_CLONE @ ${HV_DATAQC_COMMIT:0:12} (branch $HV_DATAQC_BRANCH_RESOLVED)"
echo "HM clone:            /app/NHLBI-BDC-DMC-HM @ ${HM_COMMIT:0:12} (branch $HM_BRANCH)"
echo "Output root:         $OUTPUT_ROOT"
echo "Top output dir:      $TOP"
echo "================================================================"

#------------------------------------------------------------------------------
# Initialize run_manifest.yaml
#------------------------------------------------------------------------------

# YAML list literal for the allow_fail array.
ALLOW_FAIL_YAML="[]"
if [[ ${#ALLOW_FAIL[@]} -gt 0 ]]; then
  quoted=$(printf '"%s", ' "${ALLOW_FAIL[@]}")
  ALLOW_FAIL_YAML="[${quoted%, }]"
fi

cat > "$MANIFEST" << EOF
schema: ${SCHEMA}
run_id: ${RUN_TS}
generated_at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
image_version: "${DM_BIP_VERSION:-unknown}"
image_git_ref: "${DM_BIP_GIT_REF:-unknown}"
hm_commit: "${HM_COMMIT}"
hm_branch: "${HM_BRANCH}"
hv_dataqc_commit: "${HV_DATAQC_COMMIT}"
hv_dataqc_branch: "${HV_DATAQC_BRANCH_RESOLVED}"
workflow_inputs:
  strict_consent_groups: ${STRICT_CONSENT_GROUPS}
  strict_hv_dataqc: ${STRICT_HV_DATAQC}
  strict_hv_dataqc_branch: ${STRICT_HV_DATAQC_BRANCH}
  jobs: ${JOBS}
  consent_parallelism: ${CONSENT_PARALLELISM:-1}
  allow_fail: ${ALLOW_FAIL_YAML}
  hv_dataqc_branch: "${HV_DATAQC_BRANCH:-<baked>}"
  trans_spec_input: "${TRANS_SPEC:-}"
  trans_spec_repo: "${TRANS_SPEC_REPO:-}"
  trans_spec_sha: "${TRANS_SPEC_SHA:-}"
  trans_spec_yaml_dir: "${PREBUILT_YAML_DIR}"
  dbgap_cache: "${DBGAP_CACHE:-}"
consent_groups:
EOF

#------------------------------------------------------------------------------
# Helpers
#------------------------------------------------------------------------------
# Joined-string form of ALLOW_FAIL is used so the check is exportable to
# GNU parallel workers (bash function exports don't reliably carry arrays).
ALLOW_FAIL_JOINED=""
if [[ ${#ALLOW_FAIL[@]} -gt 0 ]]; then
  ALLOW_FAIL_JOINED=$(printf '%s|' "${ALLOW_FAIL[@]}")
fi
export ALLOW_FAIL_JOINED

is_allowed_fail() {
  local name="$1"
  [[ -z "$ALLOW_FAIL_JOINED" ]] && return 1
  case "|${ALLOW_FAIL_JOINED}" in
    *"|${name}|"*) return 0 ;;
    *)             return 1 ;;
  esac
}
export -f is_allowed_fail

append_status() {
  # tsv columns: consent_group  status  duration_sec  source_dir  output_dir  notes
  local cg_name="$1" status="$2" dur="$3" src="$4" out="$5" notes="$6"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$cg_name" "$status" "$dur" "$src" "$out" "$notes" >> "$STATUS_TSV"
}

append_manifest_cg() {
  local cg_name="$1" status="$2" dur="$3" src="$4" out="$5" notes="$6"
  cat >> "$MANIFEST" << EOF
  - name: "${cg_name}"
    status: ${status}
    duration_sec: ${dur}
    source_dir: "${src}"
    output_dir: "${out}"
    notes: "${notes}"
EOF
}

#------------------------------------------------------------------------------
# Per-consent worker (invoked by GNU parallel; must be self-contained)
#------------------------------------------------------------------------------
# Writes status to $TOP/logs/<cg>/result.env. Exits 0 on PASS or FAIL_ALLOWED
# so `parallel --halt now,fail=1` only halts on a real (unauthorized) FAIL.
process_one_cg() {
  local cg_source="$1"
  local CG_NAME
  CG_NAME=$(basename "$cg_source")

  local CG_HOME="${TOP}/logs/${CG_NAME}/HOME"
  local CG_UV="${TOP}/logs/${CG_NAME}/uv-cache"
  local CG_OUTPUT="${TOP}/consent_groups/${CG_NAME}"
  local CG_LOG="${TOP}/logs/${CG_NAME}/pipeline.log"
  local RESULT_FILE="${TOP}/logs/${CG_NAME}/result.env"
  mkdir -p "$CG_HOME" "$CG_UV" "$CG_OUTPUT"

  {
    echo "================================================================"
    echo "Consent group: $CG_NAME"
    echo "Source:        $cg_source"
    echo "================================================================"
  } > "$CG_LOG"

  # Workers skip all trans-spec discovery: this script pre-built the YAML dir once.
  local -a worker_env
  worker_env=(env "HOME=$CG_HOME" "UV_CACHE_DIR=$CG_UV")
  [[ -n "$PREBUILT_YAML_DIR" ]] && worker_env+=("DM_TRANS_SPEC_DIR_PREBUILT=$PREBUILT_YAML_DIR")

  local -a workflow_cmd
  workflow_cmd=("${worker_env[@]}" /app/scripts/workflow/bdc-workflow.sh
    --schema "$SCHEMA"
    --source "$cg_source"
    --jobs "$JOBS"
  )
  [[ "$DM_MAP_PROFILE" == "true" ]] && workflow_cmd+=(--profile)

  local start end dur rc
  start=$(date +%s)
  "${workflow_cmd[@]}" >> "$CG_LOG" 2>&1
  rc=$?
  end=$(date +%s)
  dur=$((end - start))

  # bdc-workflow.sh writes to $HOME/DMC_<cg-basename>_<schema>_Processed_<ts>/.
  # Move its contents up under our stable consent-group dir.
  local processed_dir
  processed_dir=$(find "$CG_HOME" -mindepth 1 -maxdepth 1 -type d \
                  -name "DMC_${CG_NAME}_${SCHEMA}_Processed_*" 2>/dev/null | head -1)
  if [[ -n "$processed_dir" ]] && [[ -d "$processed_dir" ]]; then
    mv "$processed_dir"/* "$CG_OUTPUT"/ 2>/dev/null || true
    rmdir "$processed_dir" 2>/dev/null || true
  fi

  local cg_mapped
  cg_mapped=$(find "$CG_OUTPUT" -mindepth 1 -maxdepth 3 -type d -name "mapped-data" 2>/dev/null | head -1)

  local status notes worker_rc
  if [[ $rc -eq 0 ]]; then
    status="PASS"; notes=""; worker_rc=0
  else
    if is_allowed_fail "$CG_NAME"; then
      status="FAIL_ALLOWED"
      notes="bdc-workflow.sh exit $rc; allowed by --allow-fail"
      worker_rc=0
    else
      status="FAIL"
      notes="bdc-workflow.sh exit $rc"
      # In strict mode, non-zero here triggers parallel --halt now,fail=1.
      # In non-strict mode, we still return 0 so parallel drains all jobs;
      # the FAIL status is captured in the result file for later aggregation.
      if [[ "$STRICT_CONSENT_GROUPS" == "true" ]]; then
        worker_rc=1
      else
        worker_rc=0
      fi
    fi
  fi

  cat > "$RESULT_FILE" << EOF
CG_NAME=${CG_NAME}
CG_SOURCE=${cg_source}
CG_OUTPUT=${CG_OUTPUT}
CG_MAPPED=${cg_mapped}
STATUS=${status}
DURATION=${dur}
RC=${rc}
NOTES=${notes}
EOF

  echo "[cohort] $CG_NAME: $status (duration ${dur}s, rc=$rc)"
  return $worker_rc
}
export -f process_one_cg

# Exported for the parallel workers to see.
export TOP SCHEMA JOBS PREBUILT_YAML_DIR DM_MAP_PROFILE STRICT_CONSENT_GROUPS

#------------------------------------------------------------------------------
# Run all consent groups through GNU parallel
#------------------------------------------------------------------------------
echo
echo "================================================================"
echo "Launching ${#CONSENT_GROUPS[@]} consent-group tasks (parallelism=$CONSENT_PARALLELISM)"
echo "================================================================"

# parallel is required at runtime; verify early.
if ! command -v parallel > /dev/null 2>&1; then
  echo "FATAL: GNU parallel not found on PATH." >&2
  exit 1
fi

halt_flag=()
if [[ "$STRICT_CONSENT_GROUPS" == "true" ]]; then
  halt_flag=(--halt now,fail=1)
fi

# The whole script runs without errexit by design (see `set -uo pipefail` at the
# top): status is tracked explicitly and the script must reach its final `exit 0`
# so run_manifest.yaml / consent_group_status.tsv are always finalized. Do NOT
# re-enable `set -e` here — an errexit in the aggregation / hv_dataqc / manifest
# section (e.g. a grep with no match or a SIGPIPE from a `| head`) would abort
# before the manifest is written.
printf '%s\n' "${CONSENT_GROUPS[@]}" | \
  parallel --line-buffer --jobs "$CONSENT_PARALLELISM" "${halt_flag[@]}" \
           process_one_cg {}
PARALLEL_RC=$?

echo
echo "Parallel batch finished (rc=$PARALLEL_RC)."

#------------------------------------------------------------------------------
# Aggregate results in original consent-group order
#------------------------------------------------------------------------------
LOOP_ABORTED="false"
MAPPED_DATA_DIRS=()
CG_RESULTS=()   # <cg_name>|<status>

for cg_source in "${CONSENT_GROUPS[@]}"; do
  CG_NAME=$(basename "$cg_source")
  RESULT_FILE="${TOP}/logs/${CG_NAME}/result.env"
  CG_OUTPUT="${TOP}/consent_groups/${CG_NAME}"

  if [[ ! -f "$RESULT_FILE" ]]; then
    # Never ran (parallel halted before this cg's turn).
    append_status "$CG_NAME" "SKIPPED" "0" "$cg_source" "$CG_OUTPUT" "not started (strict halt)"
    append_manifest_cg "$CG_NAME" "SKIPPED" "0" "$cg_source" "$CG_OUTPUT" "not started (strict halt)"
    CG_RESULTS+=("${CG_NAME}|SKIPPED")
    LOOP_ABORTED="true"
    continue
  fi

  # Load result.env safely (KEY=VAL lines only).
  status="" ; dur="" ; notes="" ; cg_mapped=""
  while IFS='=' read -r k v; do
    case "$k" in
      STATUS)   status="$v" ;;
      DURATION) dur="$v" ;;
      NOTES)    notes="$v" ;;
      CG_MAPPED) cg_mapped="$v" ;;
    esac
  done < "$RESULT_FILE"

  # Consent groups with usable output (PASS or FAIL_ALLOWED that still produced
  # mapped-data) feed hv_dataqc.
  if [[ "$status" == "PASS" || "$status" == "FAIL_ALLOWED" ]]; then
    [[ -n "$cg_mapped" && -d "$cg_mapped" ]] && MAPPED_DATA_DIRS+=("$cg_mapped")
  fi

  append_status "$CG_NAME" "$status" "$dur" "$cg_source" "$CG_OUTPUT" "$notes"
  append_manifest_cg "$CG_NAME" "$status" "$dur" "$cg_source" "$CG_OUTPUT" "$notes"
  CG_RESULTS+=("${CG_NAME}|${status}")
done

#------------------------------------------------------------------------------
# hv_dataqc fan-in
#------------------------------------------------------------------------------
HAS_UNAUTH_FAIL="false"
for r in "${CG_RESULTS[@]}"; do
  st="${r##*|}"
  [[ "$st" == "FAIL" || "$st" == "SKIPPED" ]] && HAS_UNAUTH_FAIL="true"
done

HV_DATAQC_STATUS="SKIPPED"
HV_DATAQC_NOTE=""

if [[ ${#MAPPED_DATA_DIRS[@]} -eq 0 ]]; then
  HV_DATAQC_STATUS="SKIPPED"
  HV_DATAQC_NOTE="no successful consent-group mapped-data available"
  echo
  echo "SKIP hv_dataqc: no mapped-data directories produced."
elif [[ "$HAS_UNAUTH_FAIL" == "true" && "$STRICT_HV_DATAQC" == "true" ]]; then
  HV_DATAQC_STATUS="SKIPPED"
  HV_DATAQC_NOTE="unauthorized consent-group failure under --strict-hv-dataqc true"
  echo
  echo "SKIP hv_dataqc: unauthorized consent-group failure and --strict-hv-dataqc=true"
else
  # Source root is the parent dir of the consent groups (they all share a parent
  # under PilotParentStudies_NoDRS/<Cohort>/*). Derive from the first consent group.
  SOURCE_ROOT=$(dirname "${CONSENT_GROUPS[0]}")

  # Reuse the YAML dir this script pre-built for the workers so compare sees the
  # same trans-spec sources the pipeline consumed.
  if [[ -z "$PREBUILT_YAML_DIR" || ! -d "$PREBUILT_YAML_DIR" ]]; then
    echo "WARN: pre-built YAML dir not found: '${PREBUILT_YAML_DIR}'. hv_dataqc's compare step may fail."
  fi

  hv_dataqc_cmd=("$(dirname "$0")/hv-dataqc-cohort.sh"
    --schema "$SCHEMA"
    --source-root "$SOURCE_ROOT"
    --yaml-dir "$PREBUILT_YAML_DIR"
    --hv-dataqc-root "$HV_DATAQC_CLONE"
    --output-dir "${TOP}/hv_dataqc"
  )
  for md in "${MAPPED_DATA_DIRS[@]}"; do
    hv_dataqc_cmd+=(--mapped-data-dir "$md")
  done
  [[ -n "$DBGAP_CACHE" ]] && hv_dataqc_cmd+=(--dbgap-cache "$DBGAP_CACHE")

  echo
  echo "================================================================"
  echo "Running hv_dataqc across ${#MAPPED_DATA_DIRS[@]} consent-group mapped-data dirs"
  echo "================================================================"
  "${hv_dataqc_cmd[@]}"
  hv_rc=$?

  # hv-dataqc-cohort.sh always exits 0; check manifest.json for actual status.
  hv_manifest="${TOP}/hv_dataqc/compare/manifest.json"
  if [[ -f "$hv_manifest" ]]; then
    hv_overall=$(grep -Eo '"overall"[^,}]*' "$hv_manifest" | head -1 | grep -Eo '"[A-Z_]+"[[:space:]]*$' | tr -d '"' | tr -d '[:space:]')
    HV_DATAQC_STATUS="${hv_overall:-UNKNOWN}"
  else
    HV_DATAQC_STATUS="FAIL"
    HV_DATAQC_NOTE="hv_dataqc did not produce a manifest.json"
  fi
fi

#------------------------------------------------------------------------------
# Overall status + finalize manifest
#------------------------------------------------------------------------------
overall_status="PASS"
for r in "${CG_RESULTS[@]}"; do
  st="${r##*|}"
  case "$st" in
    FAIL|SKIPPED) overall_status="FAIL" ;;
    FAIL_ALLOWED) [[ "$overall_status" == "PASS" ]] && overall_status="PASS" ;;
  esac
done
if [[ "$HV_DATAQC_STATUS" == "FAIL" || "$HV_DATAQC_STATUS" == "SKIPPED" ]] && [[ "$overall_status" == "PASS" ]]; then
  [[ "$STRICT_HV_DATAQC" == "true" && "$HV_DATAQC_STATUS" == "SKIPPED" ]] || overall_status="PARTIAL"
fi

cat >> "$MANIFEST" << EOF
hv_dataqc:
  status: ${HV_DATAQC_STATUS}
  notes: "${HV_DATAQC_NOTE}"
  mapped_data_dirs_count: ${#MAPPED_DATA_DIRS[@]}
  report: "${TOP}/hv_dataqc/compare/${SCHEMA,,}_comparison_report.md"
  results_json: "${TOP}/hv_dataqc/compare/${SCHEMA,,}_comparison_results.json"
overall_status: ${overall_status}
EOF

echo
echo "================================================================"
echo "Cohort workflow complete. overall_status=${overall_status}"
echo "  Top output:  ${TOP}"
echo "  Status TSV:  ${STATUS_TSV}"
echo "  Manifest:    ${MANIFEST}"
echo "  hv_dataqc:   ${HV_DATAQC_STATUS}"
echo "================================================================"

# Always exit 0. Status carried by run_manifest.yaml + consent_group_status.tsv.
exit 0
