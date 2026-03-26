#!/usr/bin/env bash
# Clone the forked repos needed for the enum pipeline (issue #211).
#
# These forks contain unreleased fixes for integer/string enum handling.
# They are installed as editable dependencies via [tool.uv.sources] in
# pyproject.toml, which expects them as sibling directories of dm-bip.
#
# After running this script, run `uv sync` to install the forks.
#
# When upstream releases incorporate these changes, see the cleanup
# instructions in docs/pipeline-steps.md under "Local fork changes".

set -euo pipefail

# Navigate to dm-bip's parent directory (where siblings should live)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DM_BIP_DIR="$(dirname "$SCRIPT_DIR")"
PARENT_DIR="$(dirname "$DM_BIP_DIR")"
cd "$PARENT_DIR"

echo "Cloning enum pipeline forks into $(pwd)/ ..."
echo

# schema-automator: --infer-enum-from-integers flag
if [ -d schema-automator ]; then
    echo "schema-automator/ already exists — skipping clone"
else
    git clone -b infer-enum-from-integers \
        https://github.com/Sigfried/schema-automator.git
    echo "Cloned schema-automator (branch: infer-enum-from-integers)"
fi

# linkml: schema-aware delimited file loader
# Needs upstream tags for dynamic versioning to resolve a valid version number.
if [ -d linkml ]; then
    echo "linkml/ already exists — skipping clone"
else
    git clone -b schema-aware-delimited-loader \
        https://github.com/Sigfried/linkml.git
    echo "Cloned linkml (branch: schema-aware-delimited-loader)"
fi
echo "Fetching upstream tags for linkml (needed for version resolution)..."
cd linkml
git remote add upstream https://github.com/linkml/linkml.git 2>/dev/null || true
git fetch upstream --tags --quiet
cd ..

# linkml-map: forwards schema_path/target_class to linkml's loader
if [ -d linkml-map ]; then
    echo "linkml-map/ already exists — skipping clone"
else
    git clone https://github.com/Sigfried/linkml-map.git
    echo "Cloned linkml-map (branch: main)"
fi

echo
echo "Done. Now run:"
echo "  cd dm-bip && uv sync"
echo
echo "Then run the enum pipeline:"
echo "  make pipeline CONFIG=toy_data_w_enums/config-enums.mk"
