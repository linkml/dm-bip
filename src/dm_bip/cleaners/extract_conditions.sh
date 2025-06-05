#!/bin/bash

# Usage: ./extract_conditions.sh path/to/input.tsv 3

input_file="$1"
start_col="$2"

# Get the directory and base name of the input file
input_dir=$(dirname "$input_file")
base_name=$(basename "$input_file" .tsv)

# Construct the full output path in the same directory
output_file="${input_dir}/${base_name}-conditions.tsv"

# Add column header and extract headers from the specified starting column to the end
{
  echo -e "conditions"
  head -n 1 "$input_file" | awk -v start="$start_col" -F'\t' '{
    for (i = start; i <= NF; i++) print $i
  }'
} > "$output_file"

echo "Wrote condition headers to: $output_file"
