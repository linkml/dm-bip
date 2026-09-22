---
artifact:
  url: https://claude.ai/code/artifact/b7230f16-43dd-4fb0-ba91-53e4b16f1c85
  favicon: "🧬"
  description: >-
    A left-to-right schematic of how dbGaP digests and LinkML-Map transformation specs
    converge into BDC variable library entries, with the script behind each stage annotated.
  build: /private/tmp/claude-501/-Users-ginniehench-Developer-dm-bip/07a552b5-4879-488a-8feb-7faf83a72885/scratchpad/variable-library-chain.html
palette:
  spec:   { light: "#0f6a60", dark: "#52bfb1" }   # the transformation-spec stream
  dbgap:  { light: "#8f5c0c", dark: "#d9a44e" }   # the dbGaP digest stream
  typing: { light: "#74406b", dark: "#c489b6" }   # the inferred-schema stream
  held:   { light: "#8d5a52", dark: "#c08d84" }   # variables not emitted
type:
  display: IBM Plex Sans Condensed
  body:    Source Serif 4
  mono:    IBM Plex Mono
---

<!--
  SOURCE FILE. The published artifact is a build output, not the original.

  To change the page: edit this file, then ask Claude to rebuild the chain artifact.
  It recompiles to the HTML at `artifact.build` and republishes to `artifact.url`,
  so the link stays the same.

  How the compiler reads this file:
    H1                          -> page title
    the *italic* line under it  -> eyebrow
    first paragraph             -> standfirst
    the `code · code` line      -> the run line under the standfirst
    ```chain fence              -> the SVG schematic (see the block's own notes)
    *italic* para after it      -> figcaption
    "### NN · Title" + comment  -> a numbered stage row; its trailing bullet list of
                                   backticked paths becomes the right-hand script column
    everything else             -> ordinary sections, in document order

  Module paths appear twice on purpose: once short, inside a diagram box, and once in
  full in the stage list. Change both, or say which one is right and I will reconcile.
-->

# Variable Library Chain

*dm-bip · variable library extractor*

Two provenance streams converge on one file. The transformation specs say *which* source
variables exist and what they feed; the dbGaP digests say what those variables *mean*.
Everything below happens in a single process — nothing is written between stages except the
digest cache.

`driver: dm-bip extract-variable-library` · `make: variable-library` · `out: $(DM_OUTPUT_DIR)/variable-library.yaml`

## The chain

```chain
# Diagram source. Geometry is derived, not written: the compiler places a node from its
# (lane, row) cell and routes edges between cell edges. Reorder lanes, move a node to a
# different row, retitle a box, or add an edge — nothing here is a coordinate.
#
#   kind:    source | stage | output | held   (controls the box treatment)
#   row:     names the stream, and therefore the colour, from `palette` in the front matter
#   body:    the short text inside the box; keep lines under ~26 characters
#   scripts: the mono annotation at the foot of the box, at most two lines. On a source
#            box this names the general handle — the variable, host, or target the input
#            comes from — so it is set larger than the ARIC RUN value beneath it.
#   example: an optional band under a hairline inside the box, carrying the concrete
#            arguments one real run passes in. Only lanes marked `width: wide` have room
#            for it. Two lines, ~43 characters each. Omit it where a run passes nothing
#            of its own — a box with no example is drawn short and centred in its row.
#
# Edge fields: from, to (node id, optionally `id:top|bottom|left|right`), label, note
# (a second, quieter line), style (solid | dashed | emphasis), stream (a palette key or
# `neutral`), offset (nudges the entry point along the shared edge, in diagram units).

# `width: wide` gives a lane room for an `example` band; the rest stay at the base width.
lanes:
  - { name: Inputs,  width: wide }
  - { name: Read,    width: wide }
  - { name: Resolve }
  - { name: Express }
  - { name: Output }

rows: [spec, dbgap, typing]

nodes:
  - id: specs
    kind: source
    lane: Inputs
    row: spec
    eyebrow: SOURCE A
    title: Transformation specs
    body: |
      LinkML-Map YAML in the study repo,
      plus its researchstudy.yaml
    scripts: [DM_TRANS_SPEC_DIR]
    example:
      label: ARIC RUN
      lines:
        - RTIInternational/NHLBI-BDC-DMC-HV@main
        - priority_variables_transform/ARIC-ingest

  - id: digests
    kind: source
    lane: Inputs
    row: dbgap
    eyebrow: SOURCE B
    title: dbGaP digest XML
    body: |
      data_dict declares the column;
      var_report measures it
    scripts: [ftp.ncbi.nlm.nih.gov/dbgap/studies]

  - id: schema
    kind: source
    lane: Inputs
    row: typing
    eyebrow: SOURCE C
    title: Inferred schema
    body: |
      schema-automator over the prepared
      TSVs — a pipeline product
    scripts: [make schema-create]
    example:
      label: ARIC RUN
      lines:
        - -s $(DM_OUTPUT_DIR)/AricSynthetic.yaml
        - a real schema-create product

  - id: extract
    kind: stage
    stage: 1
    lane: Read
    row: spec
    title: Index the variables
    body: |
      One record per phv, holding every
      target slot it feeds
    scripts: [variable_lib/extract.py, collect_variables()]
    example:
      label: ARIC RUN
      lines:
        - 101 specs under …/ARIC-ingest —
        - 1312 phvs across 164 datasets

  - id: fetch
    kind: stage
    stage: 2
    lane: Read
    row: dbgap
    title: Pin, filter, fetch
    body: |
      Match the study to a cohort, then
      pull only the named datasets
    scripts: [prepare_study/fetch_digests.py]
    example:
      label: ARIC RUN
      lines:
        - --cohort aric --dbgap-cache .dbgap-cache
        - 326 of 736 fetched, then read from cache

  - id: read
    kind: stage
    stage: 3
    lane: Resolve
    row: dbgap
    title: Read the digests
    body: |
      Merge what is declared
      with what is observed,
      one index per table
    scripts: [variable_lib/dbgap.py, load_tables()]

  - id: classify
    kind: stage
    stage: 4
    lane: Resolve
    row: typing
    title: Type each variable
    body: |
      Continuous or
      categorical, from the
      declared range alone
    scripts: [variable_lib/classify.py, classifier_for()]

  - id: map
    kind: stage
    stage: 5
    lane: Express
    row: dbgap
    title: Map onto BDC slots
    body: |
      dbGaP fields become the
      slots the chosen class
      actually accepts
    scripts: [dbgap_metadata.py, DbgapMetadata.lookup()]

  - id: emit
    kind: stage
    stage: 6
    lane: Express
    row: spec
    title: Emit the entries
    body: |
      Identity from the specs,
      description from dbGaP,
      grouped by class
    scripts: [variable_lib/emit.py, "to_entries() · to_yaml()"]

  - id: output
    kind: output
    lane: Output
    row: spec
    eyebrow: DELIVERABLE
    title: variable-library.yaml
    body: |
      Two keyed lists, always
      both present, unset
      slots omitted
    scripts: [single_continuous_…, single_categorical_…]

  - id: held
    kind: held
    lane: Output
    row: dbgap
    eyebrow: HELD BACK
    title: Untyped variables
    body: |
      Neither class defines a
      home for an untyped
      identity, so it is
      counted, not guessed
    scripts: [VariableEntries, .unclassified]

edges:
  - { from: specs,   to: extract,      stream: spec }
  - { from: digests, to: fetch,        stream: dbgap,  label: listing }
  - { from: schema,  to: classify,     stream: typing, style: dashed,
      label: "declared ranges, keyed (pht, phv)" }

  # The load-bearing edge: what stage 1 found is what stage 2 is allowed to download.
  - { from: extract:bottom, to: fetch:top, stream: spec, style: emphasis,
      label: "the pht set", note: "only these are fetched" }

  - { from: fetch,   to: read,         stream: dbgap,  label: cache }
  - { from: read,    to: map,          stream: dbgap,  label: index }

  # The classifier is built once in stage 4 and consulted twice.
  - { from: classify, to: map:bottom,  stream: typing, style: dashed, label: kind }
  - { from: classify, to: emit:left,   stream: typing, style: dashed, label: kind }

  - { from: extract, to: emit,         stream: spec,   offset: -20,
      label: "identity triple + every usage" }
  - { from: map:top, to: emit:bottom,  stream: dbgap,  label: "slot values" }

  - { from: emit,       to: output,    stream: neutral }
  - { from: emit:right, to: held:left, stream: held,   style: dashed, label: untyped }

footnote: >-
  One process. Stage 2 is the only one that writes to disk, yielding the .dbgap-cache, which
  can be reused. The ARIC RUN lines name the real inputs; the check below runs the same chain
  against a checked-in stand-in for SOURCE A.
```

*The two crossing edges are the ones worth reading. Stage 1's set of `pht` accessions becomes
the filter on stage 2's download, so a cohort's full published listing is never fetched; and
the classifier built in stage 4 is consulted twice — once to pick the entry class, once to
decide which slot set stage 5 is even allowed to return.*

## The six stages

In general terms, with the module and entry point that carries each one.

### 01 · Index the source variables
<!-- stream: spec -->

Walk every derivation block in the specs, including nested class derivations, and re-key what
they yield by `phv` accession. A mapping-provenance record is organized around the derived
thing; a variable library record is organized around the source thing, so each entry
accumulates *all* of its uses rather than keeping the first one seen. A slot populated straight
across is kept distinct from one referenced inside an expression.

- `variable_lib/extract.py` — `collect_variables()`
- `mapping_prov/extract.py` — `iter_spec_blocks()`, `read_study()`

### 02 · Pin the cohort, then fetch only what was named
<!-- stream: dbgap -->

The study accession found in the specs is matched against the upstream cohort manifests, which
pin the dbGaP version. The FTP directory listing is scraped, and because the `pht` accession
sits in every digest filename, the listing is filtered before anything is downloaded — at no
extra request cost.

- `prepare_study/fetch_digests.py` — `load_cohorts()`, `cohort_for_study()`
- `fetch_digests(datasets=…, kinds=…)`
- `cli.py` — `_dbgap_metadata()`

### 03 · Read the digests
<!-- stream: dbgap -->

Parse both XML kinds into one index per table, keyed on the `pht` the file declares rather than
the one in its name — a cohort's listing includes tables contributed by other studies. Only the
total-set row of a var_report contributes; the per-consent-group rows restate it. Parsing is
hardened: no entity resolution, no DTD, no network.

- `variable_lib/dbgap.py` — `read_data_dict()`
- `merge_var_report()`, `load_tables()`

### 04 · Type each variable
<!-- stream: typing -->

The BDC model splits single variables into a continuous class and a categorical one, and a
transformation spec never says which a variable is. The signal comes from the inferred schema,
where classes are named by `pht` and slots by `phv` — so the pair is an exact lookup, not a name
match. The rule reads the declared range and nothing else; no distinct-value threshold is
applied, because a threshold is a judgement rather than a fact.

- `variable_lib/classify.py` — `classifier_for()`
- `classify_from_source_schema()`

### 05 · Map dbGaP fields onto BDC slots
<!-- stream: dbgap -->

The only layer that knows target slot names. It is handed the same classifier stage 4 built, so
it returns exactly the slot set the chosen class accepts — bounds and unit for a continuous
variable, coded values for a categorical one. Returning the union instead would work, and would
emit one warning per dropped key per variable: thousands of lines on a real study.

- `variable_lib/dbgap_metadata.py` — `metadata_for()`
- `DbgapMetadata.lookup()`

### 06 · Emit the entries
<!-- stream: spec -->

Identity fields are laid down first and the metadata is merged over them — never the other way,
or a table contributed by another study would overwrite the study the spec belongs to. Entries
are grouped by the class they took, both keys always present even when empty, unset slots
omitted rather than written as nulls. Repeated runs over unchanged inputs are byte-identical.

- `variable_lib/emit.py` — `to_entries()`, `to_yaml()`
- `variable_lib/datamodel/` — gen-pydantic classes

## What fills each slot

The split is the whole reason there are two input streams: the specs can only ever supply the
join.

### From the transformation specs
<!-- stream: spec -->

| Slot | Value |
|---|---|
| `id` | `dbgap:phv10111300` |
| `source_id` | the `phv` accession |
| `file_id` | the `pht` it was seen under |
| `associated_study` | the `phs` — a placeholder until study identity is settled |
| `variable_description` | every target slot this variable feeds, rendered |

### From the dbGaP digests
<!-- stream: dbgap -->

| Slot | Value |
|---|---|
| `variable_name` | VARNAME |
| `source_variable_description` | VARDESC |
| `file_name` | the table name, which only var_report carries |
| `data_type` | calculated where available, declared otherwise |
| `comment` | as published |
| `minimum_value`, `maximum_value`, `unit` | continuous only; unit normalized to UCUM, unmapped units passed through unchanged |
| `coded_values` | categorical only, in document order — dbGaP orders values meaningfully |
| `missing_value` | a coded value on a numeric variable is a sentinel, not a domain |
| `resolution`, `alert_values` | always empty; dbGaP states neither, and deriving them would be inference |

## Why both digest files

They are not interchangeable, and the disagreement between them is the point. ARIC declares a
standing height in centimetres as `<type>string</type>`.

| Across 1,298 ARIC spec variables | data_dict.xml — declared | var_report.xml — observed |
|---|---|---|
| Bounds | `<logical_min>` present on **0** | `<stat min max>` present on **100%** of numeric variables |
| Type signal | free text, four spellings, all reading as string or encoded | a closed vocabulary: `integer`, `decimal`, `enum_integer`, `string` |

That is why `--no-var-report` is not the default. It halves the download and produces entries
with no bounds and a type derived from the declared one — which for ARIC-shaped studies means
`string` on real measurements.

<!-- facts -->

- **326 / 736** — ARIC digest files fetched, because the specs name 164 datasets
- **164** — datasets referenced, one of which dbGaP never published a dictionary for
- **~3 min** — a cold ARIC run, at the half-second courtesy delay between NCBI requests

## Running it

The `-s` schema is a **dm-bip** pipeline product, not something you write: `make
schema-create` runs schema-automator over the prepared TSVs and writes
`$(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml`. So it has to be built first — but it is the *only*
prerequisite. The variable library never touches validation output or mapped data.

### The general form

```sh
# 1 · build the inferred schema the typing step needs
make schema-create    CONFIG=path/to/config.mk

# 2 · then either through the pipeline …
make variable-library CONFIG=path/to/config.mk DM_COHORT=<cohort-key>

# … or directly, which always regenerates — the better loop while iterating
dm-bip extract-variable-library path/to/specs/<study> \
  -s path/to/output/<study>/<DM_SCHEMA_NAME>.yaml \
  --cohort <cohort-key> \
  -o path/to/output/<study>/variable-library.yaml
```

`--cohort` may be omitted: the command reads the study accession from the specs and reports
which cohort it picked. `dm-bip fetch-digests --list` prints the eleven keys the manifests
define. A study with no dbGaP presence is not an error — it says so and emits entries carrying
identity only. `--no-fetch` is a genuine offline path against whatever is already cached.

### The ARIC run, at full scale

ARIC's participant data lives in a protected cloud environment, so for a long time step 1 of
the general form could not run here at all — there was nothing local for schema-automator to
generalize over, and the dbGaP half had to be checked against a hand-written stand-in schema.

The `aric/` corpus in [tis-lab/study-palette](https://github.com/tis-lab/study-palette) closes
that. It generates synthetic records under ARIC's **real** accessions: the specs decide which
tables and columns exist, dbGaP's own `data_dict`/`var_report` pair decides each column's type,
unit, bounds and code set, and only the cell values are invented. That is enough for
schema-automator to produce a genuine inferred schema, so the whole chain runs — against the
real `ARIC-ingest` specs, unmodified.

```sh
ARIC_SYNTH=/path/to/study-palette/aric

cd /path/to/dm-bip
uv run python $ARIC_SYNTH/generate.py

make schema-create    CONFIG=$ARIC_SYNTH/config.mk
make variable-library CONFIG=$ARIC_SYNTH/config.mk
```

Verified on 2026-09-10, dbGaP `phs000280.v8.p2`:

```
1312 entries from 1312 source variables (677 continuous, 635 categorical)
```

Nothing unclassified. 1298 of the 1312 carry dbGaP metadata — 226 with units, 558 with bounds,
472 with coded values. The one dataset that contributes none is `pht015212`, which the specs
name but dbGaP has never published a dictionary for.

The corpus is never published: its tables carry real `phs`, `pht` and `phv` identifiers, so an
escaped file would look like an export of controlled-access data. It is generated locally,
gitignored, and each raw table is named `SYNTHETIC.phs000280.…`.

### The same chain from a bare checkout

When the other two checkouts are not to hand, a three-spec fixture in the repo exercises the
dbGaP half on its own. Both its inputs are committed, so it reproduces with nothing staged
first — at the cost of covering three datasets instead of 164, and typing against a
hand-written schema rather than a `schema-create` product.

```sh
# from the repo root, after `uv sync`
mkdir -p tmp
uv run dm-bip extract-variable-library tests/input/mapping_prov/ARIC-ingest \
  -s tests/input/variable_lib/source_schema.yaml \
  --cohort aric --dbgap-cache .dbgap-cache \
  -o tmp/variable-library-aric.yaml
```

Both `.dbgap-cache/` and `tmp/` are gitignored, so nothing here dirties the checkout.

The first run fetches six XML files — a `data_dict` and a `var_report` for each of the three
`pht` accessions the specs name — and every run after it reads them from `.dbgap-cache`. Add
`--no-fetch` to assert the offline path, or `--refresh` to re-download.

Verified on 2026-09-09, dbGaP `phs000280.v8.p2`:

```
2 entries from 8 source variables (1 continuous, 1 categorical)
6 variables could not be typed and were skipped
```

Six of the eight are skipped by design: `source_schema.yaml` types only `pht004063`, so the
variables the specs draw from `pht012502` and `pht012811` stay unclassified. The first entry
shows what dbGaP adds on top of identity — everything from `file_name` down:

```yaml
single_continuous_variables:
- id: dbgap:phv00204719
  associated_study: bdchm:Study/phs000280
  variable_description: Source for Quantity.value_decimal
  source_id: phv00204719
  file_id: pht004063
  file_name: DERIVE13
  variable_name: BMI01
  source_variable_description: Body Mass Index in Kg/(m2) [Cohort. Visit 1]
  data_type: decimal
  minimum_value: '14.2'
  maximum_value: '65.91'
  unit: Kg/(m2)
```

Those seven slots are the whole point of the dbGaP stream: the specs know the variable exists
and the inferred schema knows it is continuous, but only the digests know it is a BMI in
Kg/(m2) ranging 14.2 to 65.91.

### Checking the identity-only half

A study with no `phs` accession exercises the other path — entries carrying identity and
nothing else. The synthetic corpus in
[tis-lab/study-palette](https://github.com/tis-lab/study-palette) is the fixture for it:

```sh
SYNTH=path/to/study-palette/synthetic
rm -f "$SYNTH/output/study_one/variable-library.yaml"
make variable-library CONFIG="$SYNTH/pipeline/example_study_one.mk" \
                      SYNTH_DIR="$SYNTH" SYNTH_OUTPUT_DIR="$SYNTH/output/study_one"
```

Last observed on 2026-09-04 reporting `35 entries from 35 source variables (19 continuous,
16 categorical)`. Removing the library file rather than the output directory is deliberate —
the directory also holds the inferred schema this target reads.

<!-- footer -->

dm-bip · variable library extractor · [docs/variable-library.md](variable-library.md) ·
tis-lab/BDC-Add-On-Tracker#93 · linkml/dm-bip#352
