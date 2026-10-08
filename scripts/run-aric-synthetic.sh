#!/usr/bin/env bash
################################################################################
# Run the variable library chain at full scale over the synthetic ARIC corpus
################################################################################
# Description:
#   The three steps documented under "The ARIC run, at full scale" in
#   docs/variable-library-chain.md, with the cd already done:
#
#     1. generate.py    -> synthetic tables under ARIC's real accessions
#     2. schema-create  -> a real schema-automator product typing those accessions
#     3. variable-library -> entries enriched from the dbGaP digests
#
#   ARIC's participant data is in a protected cloud environment, so the corpus in
#   tis-lab/study-palette stands in for it: the specs decide which tables and columns
#   exist and dbGaP's own digests decide each column's type, unit, bounds and code
#   set. Only the cell values are invented.
#
#   Steps 2 and 3 pass nothing but CONFIG — aric/config.mk is self-locating and
#   settles every other path.
#
# Usage:
#   scripts/run-aric-synthetic.sh [OPTIONS]
#
# Options:
#   --aric-synth DIR  study-palette's aric corpus  (default: ../study-palette/aric)
#   --specs DIR       ARIC-ingest specs to model   (default: generate.py's own)
#   --n N             rows per synthetic table     (default: generate.py's own, 500)
#   --skip-generate   reuse the corpus already on disk, and run steps 2-3 only
#   --force           rebuild the schema and library even if make thinks they are
#                     current — both are ordinary file targets, so an unchanged
#                     corpus otherwise leaves step 2 and step 3 doing nothing
#   -h, --help        Show this help
#
# Runs from anywhere inside the checkout; it anchors itself at the repo root, which
# is what lets uv resolve dm-bip for generate.py's imports.
#
# Requires:
#   uv, a synced environment (uv sync), and a study-palette checkout
################################################################################

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Both checkouts normally sit side by side, so the default is relative to this one.
ARIC_SYNTH="${ARIC_SYNTH:-$REPO_ROOT/../study-palette/aric}"
SPECS=""
ROWS=""
SKIP_GENERATE=false
FORCE=false

# Prints the banner above, stopping at the rule that closes it.
usage() {
  awk 'NR == 1 { next }
       /^#{10,}/ { if (++bands == 3) exit; next }
       { sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --aric-synth) ARIC_SYNTH="$2"; shift 2 ;;
    --specs) SPECS="$2"; shift 2 ;;
    --n) ROWS="$2"; shift 2 ;;
    --skip-generate) SKIP_GENERATE=true; shift ;;
    --force) FORCE=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

ARIC_SYNTH="$(cd "$ARIC_SYNTH" 2>/dev/null && pwd)" || {
  echo "No such corpus directory: ${ARIC_SYNTH}" >&2
  echo "Pass --aric-synth /path/to/study-palette/aric" >&2
  exit 2
}
CONFIG="$ARIC_SYNTH/config.mk"
[[ -f "$CONFIG" ]] || { echo "No config.mk in $ARIC_SYNTH" >&2; exit 2; }

if $FORCE; then
  # config.mk owns these two names; read them back rather than keeping a second copy.
  SCHEMA_NAME="$(sed -n 's/^DM_SCHEMA_NAME[[:space:]]*:=[[:space:]]*//p' "$CONFIG")"
  OUT_DIR="${ARIC_SYNTH_OUTPUT_DIR:-$ARIC_SYNTH/output}"
  for stale in "$OUT_DIR/${SCHEMA_NAME:-AricSynthetic}.yaml" "$OUT_DIR/variable-library.yaml"; do
    [[ -e "$stale" ]] && { rm -f "$stale"; echo "removed $stale"; }
  done
  echo
fi

if $SKIP_GENERATE; then
  echo "==> 1/3 Reusing the corpus already in $ARIC_SYNTH/data/raw"
else
  echo "==> 1/3 Generating the synthetic corpus in $ARIC_SYNTH/data/raw"
  generate_args=()
  [[ -n "$SPECS" ]] && generate_args+=(--specs "$SPECS")
  [[ -n "$ROWS" ]] && generate_args+=(--n "$ROWS")
  uv run python "$ARIC_SYNTH/generate.py" "${generate_args[@]+"${generate_args[@]}"}"
fi

echo
echo "==> 2/3 schema-create: schema-automator over the prepared tables"
make schema-create CONFIG="$CONFIG"

echo
echo "==> 3/3 variable-library: entries enriched from the dbGaP digests"
make variable-library CONFIG="$CONFIG"
