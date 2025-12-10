# Cleaners

Data cleaning utilities for preprocessing files before pipeline ingestion.

## Scripts

### extract_conditions.sh

Extracts condition column headers from a TSV file starting at a specified column.

**Usage:**
```bash
./extract_conditions.sh path/to/input.tsv <start_column>
```

**Example:**
```bash
./extract_conditions.sh data/study/conditions.tsv 3
```

This creates a file named `<base_name>-conditions.tsv` in the same directory, where `<base_name>` is the input filename without its extension. For example, if the input is `conditions.tsv`, the output will be `conditions-conditions.tsv`; if the input is `study.tsv`, the output will be `study-conditions.tsv`. The output file contains unique condition names.

---

### fix_dbgap_header.sh

Cleans dbGaP TSV file headers by:
1. Removing metadata lines up to the first blank line
2. Replacing `##` with `dbGaP_Subject_ID`
3. Cleaning up phv identifiers (removing version suffixes)

**Usage:**
```bash
# From a gzipped file
zcat input.tsv.gz | ./fix_dbgap_header.sh > output.tsv

# From a regular file
./fix_dbgap_header.sh input.tsv > output.tsv
```

---

### remove_empty_columns.py

Removes columns where all values are NaN/empty from a TSV file.

**Usage:**
```bash
# With file arguments
python remove_empty_columns.py input.tsv -o output.tsv

# With stdin/stdout
cat input.tsv | python remove_empty_columns.py > output.tsv
```

**Options:**
- `input_file` - Path to input TSV (optional, uses stdin if absent)
- `-o, --output` - Path to output TSV (optional, uses stdout if absent)

---

### replace_values.py

Replaces specific values in a CSV/TSV file based on a replacement mapping file.

**Usage:**
```bash
python replace_values.py replacements.csv input.tsv -o output.tsv
```

**Replacement file format** (CSV or TSV with these columns):
| Column | Description |
|--------|-------------|
| `filename` | Target filename (basename only, no path) |
| `column_name` | Column to target for replacement |
| `original_value` | Value to find |
| `replacement_value` | Value to substitute |

**Example replacement file:**
```
filename,column_name,original_value,replacement_value
study.tsv,sex,1,male
study.tsv,sex,2,female
study.tsv,race,9,unknown
```
