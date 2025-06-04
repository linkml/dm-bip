#!/bin/bash

# Description:
#   Cleans up dbGaP TSV file headers by:
#     1. Removing everything up to and including the first blank line.
#     2. Keeping the next line, replacing "##" with "dbGaP_Subject_ID" and all dots with underscores.
#     3. Removing the following line if it starts with "dbGaP_Subject_ID".
#   Output is written to stdout.
#   Typical use: zcat input.tsv.gz | fix_dbgap_header.sh > output.tsv

print_usage() {
  echo "Usage: $0 [input_file]"
  echo "  If no input_file is given, input must be piped via standard input."
  echo "  Output is written to standard output. Redirect it to a file."
  echo ""
  echo "Examples:"
  echo "  zcat input.tsv.gz | $0 > output.tsv"
  echo "  $0 input.tsv > output.tsv"
}

# Only valid use cases:
# 1. Exactly one argument (a file)
# 2. No arguments, but data piped into stdin
if [[ $# -eq 1 ]]; then
  INPUT_CMD="cat \"$1\""
elif [[ $# -eq 0 && ! -t 0 ]]; then
  INPUT_CMD="cat"
else
  print_usage
  exit 1
fi

# Process the input
eval "$INPUT_CMD" \
  | sed -e '1,/^$/d' \
  | sed -e '2{/^dbGaP_Subject_ID/d}' \
  | sed -e '1s/^##/dbGaP_Subject_ID/' -e '1s/\./_/g'

