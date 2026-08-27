# Variable Library Extractor

Design notes for `src/dm_bip/variable_lib/` — a deterministic command that reads
transformation specs, fetches the dbGaP data dictionaries those specs reference, and emits
variable library entries (`SingleContinuousVariable` and `SingleCategoricalVariable`
instances).

Deliverable.4.5.Task.2,
[tis-lab/BDC-Add-On-Tracker#93](https://github.com/tis-lab/BDC-Add-On-Tracker/issues/93).
Modeled on the dm-bip mapping-provenance tool, whose spec-reading layer it reuses.

The tool arrived in two iterations, and the split still shows in the code. The first read
specs alone and emitted the phv/pht/phs join plus a description — five slots, eleven nulls.
The second added dbGaP as a source for the rest. Sections below say which half a decision
belongs to where it matters.

## Why the study/dataset/variable join matters

dbGaP identifies phenotype data at three nested levels, each with its own accession prefix:
a **study** (`phs`) holds **datasets** (`pht`), which hold **variables** (`phv`).

```
phs000101              study      the study as registered in dbGaP
└── pht000113          dataset    one table within it
    └── phv10111300    variable   one column in that table
```

Only all three together identify a measurement. `phv10111300` on its own does not say which
table it came from, and equivalent variables recur across studies under different
accessions. **That three-level linkage is what this page calls the join**, and what the
`phv/pht/phs` triple below records.

[linkml/dm-bip#352](https://github.com/linkml/dm-bip/issues/352) is the governing
requirement: **the join must survive harmonization.** The BDC variable library's own
representation flattens contributing sources into parallel comma-delimited lists — 7
studies, 11 datasets, 33 variables for a single harmonized concept — which breaks it. You
can no longer say which variable came from which dataset in which study.

dm-bip is where that join still exists losslessly, because a transformation spec states it
directly: the dataset is a class-level `populated_from`, the variables are the slot-level
ones beneath it, and the study is the directory they sit in. Preserving that structure is
the point of this script, and it is why each entry carries the full phv/pht/phs triple
rather than a variable id alone.

The join is also what makes the dbGaP half possible. A spec names `phv00203151` and the
`pht` it sits in; that pair indexes straight into a data dictionary.

## Scope: what #93 settled, and what widened

#93 names one input: a transformation spec. That decided several things that would
otherwise have been judgement calls.

- **No values are read from data.** Nothing computes an observed minimum or maximum from
  the prepared tables, so there is no observed-versus-declared tension to resolve. Observed
  bounds now come from dbGaP's own published summaries instead — the study's numbers, not
  ours.
- **Deterministic.** No model runs in the extraction path — it is `SchemaView`, `lxml`, and
  dataclasses.

One item on that original list has since changed:

- **Descriptive slots were out of scope, not deferred.** `variable_name`,
  `source_variable_description`, `minimum_value`, `maximum_value`, `resolution`, `unit`,
  `comment`, `missing_value`, and `coded_values` each correspond to a dbGaP data dictionary
  field, and a data dictionary is a different input. `MetadataSource` existed as the seam if
  that ever widened.

  **It widened, and the seam held.** `DbgapMetadata` implements that protocol;
  `emit.py` was not modified. The entry now carries the join *and* what the study says the
  variable is.

## Open questions

Two remain.

- **Typing needs a second input.** "Single variable instances" are necessarily one of the
  two *typed* BDC classes, and a transformation spec does not say which a variable is. So
  the command takes `-s <schema-automator output>` — an input #93 does not mention.
  `source_id` and `file_id` are defined only on the typed classes, so emitting untyped is
  not available either. dbGaP now supplies a rival signal that could replace it; see
  [the classification question](#the-classification-question-made-concrete).
- **Study identity.** `associated_study` needs a real `phs` accession. It comes from each
  spec directory's `researchstudy.yaml`, which the release repos do not carry, so runs
  against them yield placeholder ids.

  There is a promising fallback: **raw dbGaP filenames encode both accessions.** The
  synthetic study's files are named
  `phs000101.v1.pht000111.v1.p1.c1.ex0_1s.HMB.txt.gz`, so the real study accession for that
  data is `phs000101` — exactly what the placeholder is standing in for.

  The catch is that it is discarded before the extractor could see it.
  `src/dm_bip/cleaners/prepare_input.py:154-164` regexes only the `pht` out of each raw
  filename and writes `<pht_id>.tsv`; the `phs` is never propagated. So using this means
  either reading `DM_RAW_SOURCE` filenames directly, or changing `prepare_input.py` to
  record the study accession alongside the prepared tables. The latter would serve
  mapping-provenance too, which has the same placeholder problem.

Lower priority: where this belongs in the pipeline, and whether the output is a separate
file or folded into `mapping-provenance.yaml`. #93 asks for a script, not a stage.

## Known limitation: multi-study inputs

`schemauto generalize-tsvs` merges every discovered input file into a **single** schema
named `DM_SCHEMA_NAME`. For an input tree holding more than one study — say
`synthetic/data/raw/{study_one,study_two}` — same-named tables across studies would collide,
and the study distinction is lost at exactly the point #352 says it must be preserved.

That schema is this command's typing input, so the limitation is inherited: a variable
library built from a merged multi-study schema cannot be trusted to have typed each study's
variables independently. Until it is resolved, run one pipeline per study — which is what
the synthetic config does. The open question is whether the ingest should become
study-aware instead.

---

## The chain

```
transformation specs
      │  collect_variables()          -> {phv: VariableRecord}, each knowing its pht
      ▼
{pht} the specs actually name
      │  fetch_digests(datasets=...)  -> only those data_dict + var_report files
      ▼
local dbGaP cache
      │  metadata_for()               -> MetadataSource over the fetched XML
      ▼
variable-library.yaml
```

All of it happens in one process. Nothing is written between steps — the accession set goes
straight from the spec reader into the fetch filter.

---

## What the generated schema looks like

**1. The join to schema-automator output is exact, not fuzzy.** In the generated
`$(DM_SCHEMA_NAME).yaml`, classes are named by `pht` accession and slots by `phv`
accession — for example, from the synthetic corpus:

```yaml
classes:
  pht000113:
    slots:
      - dbGaP_Subject_ID
      - phv10111300
      - phv10111305
```

So `(pht, phv)` from a trans spec indexes directly into the source schema. No name
matching, no heuristic join — a `SchemaView` lookup.

**2. There is no `enums:` block in that generated schema.** Slots carry a `range` and a
`num_distinct_values` annotation instead:

```yaml
  phv10111101:
    annotations:
      num_distinct_values: {tag: num_distinct_values, value: '2'}
    examples:
      - value: OMOP:8507
    range: OMOP identifier
```

A classifier keyed on "is the range an enum?" finds nothing here. `num_distinct_values`
plus `range` is the available signal, and any threshold on it is a **heuristic** — a
judgement about what counts as categorical, not something to bury in code.

---

## Design decisions

### Layers: parse, decide, express

```
src/dm_bip/variable_lib/
├── extract.py          # spec → VariableRecord (the IR)
├── classify.py         # source schema → continuous | categorical
├── dbgap.py            # digest XML → {pht: {phv: DbgapVariable}}
├── dbgap_metadata.py   # that index → BDC slot values
├── emit.py             # VariableRecord + kind + metadata → schema instances
└── datamodel/          # gen-pydantic output
```

plus `prepare_study/fetch_digests.py`, which fetches and caches the digests.

Same split as `mapping_prov`. `emit.py` is separate from `extract.py` because emitting
depends on the schema-automator output that types a variable, while extraction depends only
on the transformation specs. Keeping them apart means the spec-reading half stays testable
on its own, and the typing question stays isolated in one module.

The dbGaP pair splits along the same line: `dbgap.py` reads XML and knows nothing about BDC
classes, `dbgap_metadata.py` is the only layer that knows slot names.

### Reuse the spec-reading layer, don't re-parse

The hard part already exists. `extract.py` imports `iter_spec_blocks`, `spec_url`,
`read_study`, and `default_base_dir` from `dm_bip.mapping_prov.extract`; nothing in
`variable_lib` parses YAML itself.

That layer is owned by `mapping_prov`, and improving it improves both consumers.
`iter_spec_blocks` used to shape each fragment by way of linkml-map's `ObjectTransformer`,
which re-materializes the transformer metamodel per fragment; `_canonicalize` now applies
the handful of shaping rules that actually matter here instead. Reading the 101 ARIC specs
went from **36.1s to 0.2s** — same 1312 variables, 164 datasets, and 2560 usages, byte for
byte. The variable library is the larger beneficiary, since spec reading would otherwise
dominate a warm-cache run that does no fetching at all.

If a third consumer appears, those should be lifted into a shared module rather than
imported sideways.

### The IR accumulates, it doesn't overwrite

This is the one place the design deliberately differs from `mapping_prov`, which
deduplicates variable entities by id and so records only a variable's *first* use — the
rest survives there indirectly, in the `derived_from` back-links of the derived entities.
A variable library entry *is* the variable, so it must state everything that variable
feeds:

- `VariableUsage` — frozen, ordered: `target_class`, `slot`, `via_expression`, `spec_id`
- `VariableRecord` — `accession`, `datasets`, `study_id`, `usages`

`via_expression` is kept because an identifier woven into a `uuid5()` call is a materially
weaker claim about a variable's role than a value copied straight across, and a library
entry shouldn't flatten the two.

### The generation shim

`src/dm_bip/variable_lib/schema/variable_lib_schema.yaml` exists only because `gen-pydantic`
takes a local file and will not accept a URL. It adds nothing of its own, importing the
upstream `bdc-variable-library` schema by URL and tracking `main` deliberately so upstream
fixes are picked up when the datamodel is regenerated.

### `datasets` is a set

Nothing in the spec format prevents the same accession appearing under two `pht` values.
`file_id` is single-valued, so `sole_dataset()` collapses it — warning and picking
deterministically rather than silently taking whichever spec was read first.

That collapse used to be cosmetic. It is now load-bearing: the chosen `pht` decides **which
data dictionary is consulted**, so a wrong pick attaches the wrong `variable_name`, `unit`,
and `coded_values`. No ARIC variable is affected — 1312 spec pairs, 1312 distinct accessions
— but preferring the `pht` under which the dbGaP index actually knows the variable would be
the better rule.

### Classification is injected, and reads declared types only

`classify.py` resolves a slot's **declared range** and follows `typeof` to a base type;
numeric bases are continuous, everything else categorical. That is a fact read off the
schema, not a guess.

It deliberately does **not** apply a `num_distinct_values` threshold. A threshold is a
judgement about what counts as categorical rather than something the schema states, so it
is an open judgement — see [the concrete case](#the-classification-question-made-concrete)
below.

`classifier_for(None)` returns `always_unknown`, so the module runs without a source
schema and says so. Adding dbGaP did not change any of this: `classify.py` was not modified.

### Unclassified variables are held back, not defaulted

`source_id` and `file_id` are defined only on the two typed classes, so there is no
correctly-typed home for an unclassified variable's identity, and defaulting to either
class would assert something unproven about the data. They are collected in
`VariableEntries.unclassified`, counted, and reported. Running without `-s` therefore emits
nothing — the honest outcome, since classification is the blocker.

### Output is grouped, not a flat list

`to_yaml` emits `single_continuous_variables:` and `single_categorical_variables:`, both
keys always present, unset slots omitted rather than written as nulls.

When descriptive slots were empty, a continuous and a categorical entry were byte-identical
on the page and the grouping was the only thing distinguishing them. With dbGaP metadata
they now differ in substance too — continuous entries carry `minimum_value`,
`maximum_value`, and `unit`; categorical ones carry `coded_values`.

### The metadata source is given the classifier

`to_entries` picks the entry class by calling the classifier, then calls `lookup`, which is
not told what it picked. The two classes are not interchangeable, and returning the union of
their slots would leave `emit`'s `model_fields` filter to drop the mismatches — warning once
per dropped key per variable, thousands of lines on a real study.

`DbgapMetadata` is handed the **same** classifier instead, so it returns exactly the
accepted slot set and the two can never disagree. Verified on ARIC: zero dropped-slot
warnings.

### Read the digests directly, not through schema-automator

`schema_automator.adapters.dbgap.parse_dbgap_digest` reads the same files, but it is driven
by a metamodel whose `Variable` class declares eight attributes — `id`, `name`,
`description`, `reported_type`, `calculated_type`, `values`, `min`, `max`. There is no slot
for `<unit>`, `<logical_min>`, `<logical_max>` or `<comment>`, so those are silently
dropped. Four of the eleven slots this work exists to fill are unreachable through it.

Accessions join on their stem. Specs are unversioned (`phv00202843`), dbGaP versions
everything (`phv00202843.v2`), and var_report adds participant set and consent group
(`phv00202843.v2.p2.c1`). Only the total-set row of a var_report is read; the
per-consent-group rows restate the same variable over a subset.

### Determinism

- Records sorted by accession; usages sorted within each record; usages deduplicated.
- Digest files loaded in sorted order.
- Coded values kept in **document order** — dbGaP orders them meaningfully (Yes/No, severity
  scales) and the order of an input file is already stable, so sorting would lose
  information and gain nothing.
- No `uuid4()` and no timestamps anywhere — ids derive from the accession.
- The dirty-repo guard from `spec_url` is preserved for spec ids.

Verified by running twice and diffing: byte-identical. A cold-fetch run and a cached run
produce the same file.

---

## What fills each slot

**From the specs** — the join, available without any second input:

| Slot | Value | From |
|---|---|---|
| `id` | `dbgap:phv10111300` | accession, matching the mapping-prov convention |
| `source_id` | `phv10111300` | `VariableRecord.accession` |
| `file_id` | `pht000113` | `VariableRecord.sole_dataset()` |
| `associated_study` | `bdchm:Study/phs000280` | `read_study()` — **placeholder today**, pending study identity |
| `variable_description` | rendered from `usages` | `describe()` |

**From dbGaP** — everything else:

| Slot | Source | Notes |
|---|---|---|
| `variable_name` | `<name>` | dbGaP's VARNAME |
| `source_variable_description` | `<description>` | dbGaP's VARDESC |
| `file_name` | `var_report` root `@name` | The dbGaP table name (`ANTA`). The data_dict root has no name attribute |
| `data_type` | `calculated_type`, else `<type>` | `integer`/`decimal`/`enum`/`string`; without var_report, `numeric`/`code`/`string` |
| `comment` | `<comment>` | |
| `minimum_value`, `maximum_value` | `<stat @min/@max>`, else `<logical_min>`/`<logical_max>` | **Continuous only** |
| `unit` | `<unit>`, UCUM-normalized | **Continuous only** |
| `coded_values` | `<value code="X">label</value>` | **Categorical only**, in document order |
| `missing_value` | `<value>` on a continuous variable | See sentinels below |
| `resolution`, `alert_values` | — | Always empty; dbGaP states neither, and deriving them would be inference |

`associated_study` is **never** supplied by the metadata source. `emit` merges `lookup`'s
return over the identity fields, so returning it would let a table contributed by another
study overwrite the study the spec belongs to.

A real entry — the first five slots from the spec, the rest from dbGaP:

```yaml
single_continuous_variables:
- id: dbgap:phv00203151
  associated_study: bdchm:Study/phs000280
  variable_description: Source for Quantity.value_decimal
  source_id: phv00203151
  file_id: pht004032
  file_name: ANTA
  variable_name: ANTA01
  source_variable_description: '[Height and weight]. Standing height (to the nearest
    cm). Q1 [Anthropometry Form, ANTA. Visit 1]'
  data_type: integer
  minimum_value: '125'
  maximum_value: '199'
  unit: cm
```

Keys with no matching slot on the chosen class are dropped with a warning rather than
silently discarded.

### Sentinel values

About a dozen ARIC variables are numeric *and* carry a coded value — `CHMA05`, a blood
measure in mmol/L ranging 126 to 155, has one code `5 = Transport condition`. That code is
not the variable's domain; it is an out-of-band marker on a measurement.

Those become `missing_value`, not `coded_values`. `MissingValue` carries exactly the code
and label dbGaP publishes, and `coded_values` does not exist on `SingleContinuousVariable`
anyway.

**On `associated_study`:** its range is `ResearchStudy`, but that class is not inlined and
defines only `id` (inherited from `Entity`), so `gen-pydantic` emits the slot as a plain
`Optional[str]` holding a reference. Study identity has nowhere to live except that id
string — no name, no accession authority — which sharpens the study-identity question.

---

## Fetching dbGaP metadata

### Why the fetch is selective

A cohort's `pheno_variable_summaries/` directory holds every dataset the study ever
published. ARIC's has 736 files. The ARIC transformation specs reference 164 datasets — so
573 of those files describe variables no spec mentions.

The `pht` accession is in the filename:

```
phs000280.v8.pht004027.v3.ABI04.data_dict.xml
                └──────┘
```

so the filter runs on the FTP listing before anything is downloaded, at no extra request
cost. For ARIC that is **326 files instead of 736**.

At `NCBI_DELAY_SECONDS = 0.5`, a cold ARIC run takes roughly three minutes plus transfer.
Cached runs re-read from disk.

### When a dataset has no dictionary

One ARIC spec dataset, `pht015212`, has no file in the published listing. The command
reports it rather than silently emitting 14 entries with empty slots:

```
1 of 164 datasets have no dbGaP data dictionary: pht015212
```

Those variables still get entries; they just carry identity only.

### Why both digest files are fetched

They are not interchangeable. `data_dict.xml` is what the study **declares**:

```xml
<variable id="phv00203151.v2">
  <name>ANTA01</name>
  <description>[Height and weight]. Standing height (to the nearest cm). Q1</description>
  <type>string</type>
  <unit>cm</unit>
</variable>
```

`var_report.xml` is what the data **contains**:

```xml
<variable id="phv00203151.v2.p2" calculated_type="integer" reported_type="string">
  <total><stats><stat n="15045" nulls="2" mean="168.5" min="125" max="199"/></stats></total>
</variable>
```

Note the disagreement: ARIC declares a standing height in centimetres as
`<type>string</type>`. Measured across all 1298 ARIC spec variables that have a dictionary:

| | `data_dict` | `var_report` |
|---|---|---|
| `minimum_value` / `maximum_value` | `<logical_min>` present on **0** | `<stat min max>` present on **100%** of numeric variables |
| type signal | `<type>` is one of four spellings, all reading as string or encoded | `calculated_type` is a closed vocabulary: `integer`, `decimal`, `enum_integer`, `string` |

That is why `--no-var-report` is not the default. It halves the download and produces
entries with no `minimum_value`, no `maximum_value`, and a `data_type` derived from the
declared type — which for ARIC-shaped studies means `string` on real measurements.

---

## Running it

### Prerequisite

The `-s` argument is a **pipeline product**, not a checked-in file. It is the schema
schema-automator infers from the prepared data (`pipeline.Makefile:333-339`), so it has to
be built first:

```
raw dbGaP files  ──prepare_input.py──▶  prepared/*.tsv  ──schemauto generalize-tsvs──▶  <DM_SCHEMA_NAME>.yaml
```

`make schema-create` does both steps and is the **only** prerequisite — the variable library
reads the specs and the inferred schema, and never touches validation output or mapped data,
so the later pipeline stages are irrelevant to it. Running the full `make pipeline` works but
does minutes of unrelated work.

The transformation specs are checked into the study repo, so nothing needs to be run for
them. The dbGaP cache manages itself. The output directory is created by `schema-create`.

### Commands

```sh
# One directory of specs (one study), typed against that study's inferred schema
dm-bip extract-variable-library path/to/specs/<study> \
  -s path/to/output/<study>/<DM_SCHEMA_NAME>.yaml \
  --cohort aric \
  -o variable-library.yaml

# As part of the pipeline, with every path resolved from the pipeline config
make schema-create      CONFIG=path/to/study.mk    # builds the -s schema
make variable-library   CONFIG=path/to/study.mk DM_COHORT=aric
```

`--cohort` may be omitted: the command reads the study accession from the specs'
`researchstudy.yaml` and matches it against the upstream cohort manifests, reporting which
cohort it picked. Pass it explicitly when the spec directory has no `researchstudy.yaml`,
which release repos often don't carry. Omitting it on a study with no dbGaP presence is not
an error — the command says so and emits entries with the descriptive slots empty.

Directories are searched recursively for `*.yaml` spec files, as in
[mapping provenance](mapping-provenance.md).

| Option | Default | Effect |
|---|---|---|
| `-s` / `--source-schema` | none | schema-automator output; without it nothing is typed and nothing is emitted |
| `--cohort` | auto-detect | dbGaP cohort key (`aric`, `jhs`, …); `dm-bip fetch-digests --list` shows them |
| `--dbgap-cache` | `.dbgap-cache` | Where fetched XML lives. Gitignored |
| `--no-fetch` | fetches | Use only what is already cached — a genuine offline path |
| `--no-var-report` | uses both | Skip `var_report.xml`. Halves the download and **loses observed bounds** |
| `--refresh` | reuses cache | Re-download files already cached |

Where each argument comes from, for any study:

| Argument | Pipeline variable |
|---|---|
| spec dir | `DM_TRANS_SPEC_DIR` |
| `-s` | `SCHEMA_FILE`, i.e. `$(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml` |
| `-o` | `VARIABLE_LIBRARY_FILE`, i.e. `$(DM_OUTPUT_DIR)/variable-library.yaml` |
| `--cohort` | `DM_COHORT` |
| `--dbgap-cache` | `DM_DBGAP_CACHE_DIR` |

Unlike `mapping-provenance`, `variable-library` is **not** wired into `make pipeline` and is
**not** produced as a side effect of `make map-data` — it has to be asked for by name.

Being a file target, it prints **"Nothing to be done"** when the output is newer than its
inputs. Delete just that file to force a rebuild — not the output directory, which holds the
`-s` schema. The dbGaP cache is deliberately *not* a prerequisite: it is network-populated
and managed by the command, so listing it would leave the target perpetually out of date.
The direct `dm-bip extract-variable-library` form always regenerates, which makes it the
better loop while iterating.

### Exercising it without a real study

The two halves need different inputs, and no single corpus supplies both.

**The classification half** needs a schema-automator output, which needs prepared data. The
[study-palette](https://github.com/tis-lab/study-palette) synthetic corpus already ships one,
so it runs offline from a dm-bip checkout with nothing else built:

```sh
SYNTH=/path/to/study-palette/synthetic
make variable-library CONFIG=$SYNTH/pipeline/example_study_one.mk \
                      SYNTH_DIR=$SYNTH SYNTH_OUTPUT_DIR=$SYNTH/output/study_one
```

That emits 35 entries from 35 source variables, 19 continuous and 16 categorical. It exercises
spec reading, typing, and emission end to end — but **not** the dbGaP half: the corpus's
accessions are fictional (`phs000101`, `pht000111`), no cohort manifest pins that study, and
NCBI has nothing to fetch. The run reports as much and carries on:

```
No study accession in these specs; descriptive slots will be empty
```

That check runs *before* the cohort registry is consulted, so a study that cannot match one
never triggers the network fetch that loading it would require.

**The dbGaP half** needs a real cohort, and works without any prepared data as long as you
have something to pass to `-s`:

```sh
uv run dm-bip extract-variable-library \
  ~/Developer/NHLBI-BDC-DMC-HV/priority_variables_transform/ARIC-ingest \
  -s <schema>.yaml \
  --cohort aric \
  --dbgap-cache /tmp/dbgap-cache \
  -o /tmp/vl.yaml
```

Without `-s` this still fetches, joins, and reports coverage — it just emits nothing, because
every variable lands in `unclassified`. That is a useful smoke test of steps 1 and 2 on its own.

To regenerate the checked-in datamodel after an upstream schema change (needs network):

```bash
make variable-lib-datamodel
```

## Running the tests

```bash
uv run pytest tests/unit/variable_lib tests/unit/test_fetch_digests.py -q
```

These are offline. The classifier fixture is a local schema, and the digest fixtures under
`tests/input/variable_lib/dbgap/` are small hand-written XML covering the shapes that
matter: consent-group rows, a `<value>` with no code, duplicate codes, a table contributed
by another study, and a variable whose report carries no `<stat>`.

The full `make test` also runs `tests/integration/test_mapping_prov_schema.py`, which needs
network: it validates against the upstream PROV schema imported by URL.

The pydantic `UserWarning` about `FieldInfo(annotation=NoneType...)` is pre-existing noise
from the generated datamodel, not a failure.

---

## The classification question, made concrete

`phv10111100` is the participant identifier in the synthetic study. Its declared range in
the generated schema is `integer`, so the current rule types it **continuous** — which is
wrong: it is a label that happens to be numeric. Its `num_distinct_values` is `500` out of
500 rows, exactly the signal that would catch it.

dbGaP now supplies a rival signal that resolves this class of error on the study's own
authority: `var_report`'s `calculated_type` distinguishes `enum_integer` from `integer`.
Across the 1298 ARIC spec variables that have a dictionary it types every one of them, 569
continuous and 729 categorical, from a closed four-value vocabulary.

It is deliberately **not** wired into classification — that stayed on the source schema, so
this work changed what entries say and not which class they take. But the signal is fetched
and available, and `Classifier` is an injection seam, which makes switching a contained
change rather than a redesign.

That single variable is the whole typing question in one case.

---

## The other consumer: `adapt-digests`

The same digest cache feeds a second, unrelated target. It predates this work, is not part
of it, and is documented here because the two are easy to confuse.

```sh
make adapt-digests DM_COHORT=aric DM_DBGAP_CACHE_DIR=<dir>
```

It wraps `schemauto adapt-dbgap`, calling it once per data_dict/var_report pair to emit
schema-automator's **canonical Data Dictionary TSV**:

```make
$(DM_DD_DIR)/%.dd.tsv: $$(DBGAP_DD_$$*) $$(DBGAP_VR_$$*)
	@mkdir -p $(@D)
	$(RUN) schemauto adapt-dbgap $< --var-report $(word 2,$^) --tsv -o $@
```

Output lands in `output/$(DM_COHORT)/dd/`, independent of `DM_DBGAP_CACHE_DIR`, which only
says where the input XML is read from. The whole block is guarded by
`ifneq ($(strip $(DM_COHORT)),)`, so the targets exist only when a cohort is set.

`.SECONDEXPANSION:` is what lets the pattern rule dereference `DBGAP_DD_<key>` /
`DBGAP_VR_<key>`. Make cannot pair the two files with a plain stem match, because dbGaP puts a
`.p<N>` participant-set segment in var_report filenames but not in data_dict ones — which is
why `write_pairs_mk()` emits an explicit `digest_pairs.mk` for the Makefile to include.

Three things to know before relying on it:

**TSV only.** There is no JSON or CSV path, in this repo or in the adapter. Columns are
`name / type / description / codes / unit / min / max / uri`:

```
name          type                 description                      ...  uri
SUBJECT_ID    string               De-identified ARIC subject ID         dbgap:phv00098579.v6
CONSENT       permissible_values   Restriction on Use/Storage of DNA     ...
```

**It fails partway through on ARIC.** The run writes 20 of 351 TSVs, then:

```
schema_automator/adapters/codes.py:125, in serialize_codes
ValueError: Code record missing 'code' key: {'label': 'N/A'}
make: *** [output/aric/dd/phs000280.v8.pht004046.v6.CCELPS18.dd.tsv] Error 1
```

schema-automator 0.5.6 assumes every `<value>` element carries a `code` attribute. That table
contains a bare `<value>N/A</value>`. **17 of ARIC's 368 data dictionaries** have bare `<value>`
elements, so the failure recurs and Make halts on the first; `make -k` gets the ~334 that
convert and skips the rest. It is an upstream defect against real published data.

**Conversion is a shell-out.** No Python function to call directly.

None of this affects the variable library. The defect is in `serialize_codes()`, on the TSV
*serialization* path — those 17 files parse cleanly through `variable_lib/dbgap.py`, which
never goes near it.

---

## Known limitations

- **`-s` is still required.** Classification is unchanged, so variables it cannot type are
  held back entirely and their dbGaP metadata is fetched and discarded. Building a variable
  library still needs the prepared data files.
- **Units are not all UCUM.** The slot asks for UCUM and the normalization table covers most
  of what dbGaP emits (`Years` → `a`, `lb` → `[lb_av]`), but unmapped units pass through in
  the study's own spelling. Emitting `SI` unchanged beats emitting a lowercased corruption
  of it.
- **Decimal slots serialize as quoted strings** — `minimum_value: '125'`. That is `Decimal`
  round-tripping through `model_dump(mode="json")`, and it is stable. Not a bug.
- **Duplicate codes are preserved.** Fifteen ARIC variables list the same code twice. Echoing
  a dbGaP defect faithfully beats silently disagreeing with dbGaP.

---

## Remaining work

- **Classification rule beyond declared range** — needs the typing question answered. The
  dbGaP `calculated_type` signal is now available for it.
- **Real study accession** — needs the study-identity question answered.
- **`sole_dataset()` should prefer a known dictionary** rather than the alphabetically
  first, now that the choice decides which metadata a variable gets.
- **Integration test** validating emitted entries against the upstream schema. Needs a
  decision on whether to validate against the generation shim or the upstream URL.
- **Upstream schema defect**: the `alert_value`/`alert_values` duplication in
  bdc-variable-library is unfiled.
