#!/bin/bash
# The TSV loader parses numeric-looking strings as integers before
# validation, so they fail to match string-ranged slots and string
# enum permissible values.
#
# All three rows should be valid:
#   - zipcode is range:string, values like "90210" are valid strings
#   - satisfaction is range:satisfaction_enum, PVs are '1'..'5'
#
# But linkml validate rejects them because the loader converts
# "90210" -> int 90210 and "4" -> int 4 before checking the schema.

cd "$(dirname "$0")"
echo "--- schema (zipcode: string, satisfaction: satisfaction_enum) ---"
echo "--- data.tsv ---"
cat data.tsv
echo
echo "--- linkml validate ---"
uv run linkml validate --schema schema.yaml --target-class Survey data.tsv
