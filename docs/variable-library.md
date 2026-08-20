# Variable Library Extractor

Design notes for `src/dm_bip/variable_lib/` — a deterministic script that
takes a transformation spec and emits variable library entries (`SingleContinuousVariable`
and `SingleCategoricalVariable` instances).

Deliverable.4.5.Task.2,
[tis-lab/BDC-Add-On-Tracker#93](https://github.com/tis-lab/BDC-Add-On-Tracker/issues/93).
Modeled on the dm-bip mapping-provenance tool, whose spec-reading layer it reuses.

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

## Scope, and what it settles

#93 names one input: a transformation spec. That decides several things that would
otherwise be judgement calls.

- **Descriptive slots are out of scope, not deferred.** `variable_name`,
  `source_variable_description`, `minimum_value`, `maximum_value`, `resolution`, `unit`,
  `comment`, `missing_value`, and `coded_values` each correspond to a dbGaP data dictionary
  field. A data dictionary is a different input, so an entry carries the phv/pht/phs join
  and a description of what the variable feeds, and nothing else. `MetadataSource` exists as
  the seam if that ever widens.
- **No values are read from data.** Nothing computes an observed minimum or maximum, so
  there is no observed-versus-declared tension to resolve.
- **Deterministic.** No model runs in the extraction path — it is `ast`, `SchemaView`, and
  dataclasses.

## Open questions

Two remain.

- **Typing needs a second input.** "Single variable instances" are necessarily one of the
  two *typed* BDC classes, and a transformation spec does not say which a variable is. So
  the script takes `-s <schema-automator output>` — an input #93 does not mention.
  `source_id` and `file_id` are defined only on the typed classes, so emitting untyped is
  not available either.
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

That schema is this script's typing input, so the limitation is inherited: a variable
library built from a merged multi-study schema cannot be trusted to have typed each study's
variables independently. Until it is resolved, run one pipeline per study — which is what
the synthetic config does. The open question is whether the ingest should become
study-aware instead.

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

### Three layers: parse, decide, express

```
src/dm_bip/variable_lib/
├── extract.py     # spec → VariableRecord (the IR)
├── classify.py    # source schema → continuous | categorical
├── emit.py        # VariableRecord + kind → schema instances
└── datamodel/     # gen-pydantic output
```

Same split as `mapping_prov`. `emit.py` is separate from `extract.py` because emitting
depends on the schema-automator output that types a variable, while extraction depends only
on the transformation specs. Keeping them apart means the spec-reading half stays testable
on its own, and the typing question stays isolated in one module.

### Reuse the spec-reading layer, don't re-parse

The hard part already exists. `extract.py` imports `iter_spec_blocks`, `spec_url`,
`read_study`, and `default_base_dir` from `dm_bip.mapping_prov.extract`; nothing in
`variable_lib` parses YAML itself.

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

### Classification is injected, and reads declared types only

`classify.py` resolves a slot's **declared range** and follows `typeof` to a base type;
numeric bases are continuous, everything else categorical. That is a fact read off the
schema, not a guess.

It deliberately does **not** apply a `num_distinct_values` threshold. A threshold is a
judgement about what counts as categorical rather than something the schema states, so it
is an open judgement — see [the concrete case](#the-classification-question-made-concrete)
below.

`classifier_for(None)` returns `always_unknown`, so the module runs without a source
schema and says so.

### Unclassified variables are held back, not defaulted

`source_id` and `file_id` are defined only on the two typed classes, so there is no
correctly-typed home for an unclassified variable's identity, and defaulting to either
class would assert something unproven about the data. They are collected in
`VariableEntries.unclassified`, counted, and reported. Running without `-s` therefore emits
nothing — the honest outcome, since classification is the blocker.

### Output is grouped, not a flat list

With descriptive slots empty, a continuous and a categorical entry are byte-identical on
the page. `to_yaml` emits `single_continuous_variables:` and `single_categorical_variables:`,
both keys always present, unset slots omitted rather than written as nulls.

### Determinism

- Records sorted by accession; usages sorted within each record; usages deduplicated.
- No `uuid4()` and no timestamps anywhere — ids derive from the accession.
- The dirty-repo guard from `spec_url` is preserved for spec ids.

Verified by running twice and diffing: byte-identical.

---

## What the specs alone can fill

| Slot | Value | From |
|---|---|---|
| `id` | `dbgap:phv10111300` | accession, matching the mapping-prov convention |
| `source_id` | `phv10111300` | `VariableRecord.accession` |
| `file_id` | `pht000113` | `VariableRecord.sole_dataset()` |
| `associated_study` | `bdchm:Study/phs000280` | `read_study()` — **placeholder today**, pending study identity |
| `variable_description` | rendered from `usages` | `describe()` |

Everything else — `variable_name`, `source_variable_description`, `minimum_value`,
`maximum_value`, `resolution`, `unit`, `comment`, `missing_value`, `coded_values` — needs
dbGaP data dictionaries — a different input, and so out of scope for #93. The optional
`MetadataSource` protocol is the seam if that widens: one
`lookup(dataset, accession) -> dict` implementation, rather than a restructure. Keys with
no matching slot are dropped with a warning rather than silently discarded.

**On `associated_study`:** its range is `ResearchStudy`, but that class is not inlined and
defines only `id` (inherited from `Entity`), so `gen-pydantic` emits the slot as a plain
`Optional[str]` holding a reference. Study identity has nowhere to live except that id
string — no name, no accession authority — which sharpens the study-identity question.

---

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
them. The output directory is created by `schema-create`.

### Commands

```sh
# One directory of specs (one study), typed against that study's inferred schema
dm-bip extract-variable-library path/to/specs/<study> \
  -s path/to/output/<study>/<DM_SCHEMA_NAME>.yaml \
  -o variable-library.yaml

# As part of the pipeline, with every path resolved from the pipeline config
make schema-create      CONFIG=path/to/study.mk    # builds the -s schema
make variable-library   CONFIG=path/to/study.mk
```

Directories are searched recursively for `*.yaml` spec files, as in
[mapping provenance](mapping-provenance.md).

Where each argument comes from, for any study:

| Argument | Pipeline variable |
|---|---|
| spec dir | `DM_TRANS_SPEC_DIR` |
| `-s` | `SCHEMA_FILE`, i.e. `$(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml` |
| `-o` | `VARIABLE_LIBRARY_FILE`, i.e. `$(DM_OUTPUT_DIR)/variable-library.yaml` |

Unlike `mapping-provenance`, `variable-library` is **not** wired into `make pipeline` and is
**not** produced as a side effect of `make map-data` — it has to be asked for by name.

Being a file target, it prints **"Nothing to be done"** when the output is newer than its
inputs. Delete just that file to force a rebuild — not the output directory, which holds the
`-s` schema. The direct `dm-bip extract-variable-library` form always regenerates, which
makes it the better loop while iterating.

For a worked end-to-end invocation with real paths, see `synthetic/README.md` in
[tis-lab/study-palette](https://github.com/tis-lab/study-palette), which runs this against
its synthetic cohorts.

To regenerate the checked-in datamodel after an upstream schema change (needs network):

```bash
make variable-lib-datamodel
```

## Running the tests

```bash
uv run pytest tests/unit/variable_lib -q
```

These are offline — the classifier fixture is a local schema. The full `make test` also runs
`tests/integration/test_mapping_prov_schema.py`, which needs network: it validates against
the upstream PROV schema imported by URL.

The pydantic `UserWarning` about `FieldInfo(annotation=NoneType...)` is pre-existing noise
from the generated datamodel, not a failure.

---

## The classification question, made concrete

`phv10111100` is the participant identifier in the synthetic study. Its declared range in
the generated schema is `integer`, so the current rule types it **continuous** — which is
wrong: it is a label that happens to be numeric. Its `num_distinct_values` is `500` out of
500 rows, exactly the signal that would catch it.

That single variable is the whole typing question in one case.

---

## Remaining work

- **Classification rule beyond declared range** — needs the typing question answered.
- **Real study accession** — needs the study-identity question answered.
- **`MetadataSource` implementation** — out of scope for #93; build only if scope widens.
- **Integration test** validating emitted entries against the upstream schema. Needs a
  decision on whether to validate against the generation shim or the upstream URL.
- **Upstream schema defect**: the `alert_value`/`alert_values` duplication in
  bdc-variable-library is unfiled.
