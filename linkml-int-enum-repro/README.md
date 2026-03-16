# linkml-int-enum-repro

Minimal reproduction of a bug in LinkML's TSV loader where numeric-looking
string values are parsed as integers, causing false validation failures for
`range: string` and `range: <enum>` slots.

## Run it

```bash
bash repro.sh
```

## The setup

**schema.yaml** defines a `Survey` class with three slots:
- `id` — `range: integer` (should be parsed as int — this one is correct)
- `zipcode` — `range: string`
- `satisfaction` — `range: satisfaction_enum` (permissible values: `'1'`..`'5'`, `'foo'`)

**data.tsv** has five rows:

| id | zipcode   | satisfaction | expected result |
|----|-----------|-------------|-----------------|
| 1  | 90210     | 4           | valid (zipcode is a string, `'4'` is a permissible value) |
| 2  | 10001     | 2           | valid (same reasoning) |
| 3  | 30301-123 | 5           | valid (`30301-123` is not numeric, `'5'` is a permissible value) |
| 4  | 20001-123 | foo         | valid (`'foo'` is a permissible value) |
| 5  | 30001     | bar         | **invalid** (`'bar'` is not a permissible value) |

## Actual output

```
[ERROR] [data.tsv/0] 90210 is not of type 'string', 'null' in /zipcode
[ERROR] [data.tsv/0] 4 is not of type 'string' in /satisfaction
[ERROR] [data.tsv/0] 4 is not one of ['1', '2', '3', '4', '5', 'foo'] in /satisfaction
[ERROR] [data.tsv/1] 10001 is not of type 'string', 'null' in /zipcode
[ERROR] [data.tsv/1] 2 is not of type 'string' in /satisfaction
[ERROR] [data.tsv/1] 2 is not one of ['1', '2', '3', '4', '5', 'foo'] in /satisfaction
[ERROR] [data.tsv/2] 5 is not of type 'string' in /satisfaction
[ERROR] [data.tsv/2] 5 is not one of ['1', '2', '3', '4', '5', 'foo'] in /satisfaction
[ERROR] [data.tsv/4] 30001 is not of type 'string', 'null' in /zipcode
[ERROR] [data.tsv/4] 'bar' is not one of ['1', '2', '3', '4', '5', 'foo'] in /satisfaction
```

Only the last error (row 5, `'bar'`) is correct. Everything else is a false failure.

Note that row 3 (`30301-123`) and row 4 (`20001-123`) pass zipcode validation
because the hyphen prevents `_parse_numeric` from converting them to integers.

## Root cause

The TSV loader in `linkml.validator.loaders.delimited_file_loader` applies
`_parse_numeric()` to every cell unconditionally before the schema is consulted:

```python
# delimited_file_loader.py, line 42
yield {k: _parse_numeric(v) for k, v in row.items() ...}
```

`_parse_numeric` converts any numeric-looking string to `int` or `float`:
- TSV cell `"90210"` → Python `int(90210)`
- TSV cell `"4"` → Python `int(4)`

After this conversion:
- `int(90210)` fails `range: string` validation (expects a `str`)
- `int(4)` fails enum matching (permissible value `'4'` is a `str`, `4 != '4'`)

The same loader is used by `linkml-map` (via dm-bip's `map_data.py`), so
enum derivation matching also fails — `source_value == pv_deriv.populated_from`
is `int(4) == str('4')` → `False`, producing `null` in mapped output.

## Why integer-typed PVs can't fix this

LinkML's metamodel defines `PermissibleValue.text` as always a string. Whether
you write `1:` or `'1':` in YAML, LinkML normalizes both to `str('1')`. There
is no way to declare an integer-typed permissible value.

## Proposed fix

Make the TSV loader schema-aware: skip `_parse_numeric` for slots whose range
is `string` or an enum. The loader currently receives no schema context, so it
would need to accept slot-range information (e.g., a set of column names to
leave as strings).

This fixes both validation and mapping, since both consume rows from the same
loader.
