# Variable Library Extractor

Design notes and build record for `src/dm_bip/variable_lib/` — a deterministic script that
takes a transformation spec and emits variable library entries (`SingleContinuousVariable`
and `SingleCategoricalVariable` instances).

Deliverable.4.5.Task.2,
[tis-lab/BDC-Add-On-Tracker#93](https://github.com/tis-lab/BDC-Add-On-Tracker/issues/93).
Modeled on the dm-bip mapping-provenance tool, whose spec-reading layer it reuses.

## Why the join matters

[linkml/dm-bip#352](https://github.com/linkml/dm-bip/issues/352) is the governing
requirement: **study → dataset → variable alignment must survive.** The variable library
flattens contributing sources into parallel comma-delimited lists — 7 studies, 11 datasets,
33 variables for a single harmonized concept — which loses the join between them. You can
no longer say which variable came from which dataset in which study.

dm-bip is where that join still exists losslessly, because a transformation spec states it
directly: the dataset is a class-level `populated_from`, the variables are the slot-level
ones beneath it, and the study is the directory they sit in. Preserving that structure is
the point of this script, and it is why each entry carries the full phv/pht/phs triple
rather than a variable id alone.

## The steps

| # | Step | State |
|---|---|---|
| 1 | **IR + `collect_variables`** — `VariableUsage` / `VariableRecord` index the specs by `phv` accession, accumulating every use | done |
| 2 | **`emit.py` + `classify.py`** — records become typed BDC instances, typed from schema-automator output | done |
| 3 | **CLI + make target** — `dm-bip extract-variable-library`, `make variable-library` | done |
| 4 | **Classification rule beyond declared range** | open — typing |
| 5 | **Real study accession** for `associated_study` | open — study identity |
| 6 | **`MetadataSource` implementation** filling descriptive slots | out of scope for #93 |

Steps 1–3 are built and passing: 11 files added, 4 modified, 22 tests. On the synthetic
study, 35 of 35 source variables are typed and emitted, byte-identical across runs.
Details in [What got built](#what-got-built-steps-13); the open questions are named below.

## Scope, and what it settles

#93 names one input: a transformation spec. That decides several things that would
otherwise be judgement calls.

- **Descriptive slots are out of scope, not deferred.** `variable_name`,
  `source_variable_description`, `minimum_value`, `maximum_value`, `resolution`, `unit`,
  `comment`, `missing_value`, and `coded_values` each correspond to a dbGaP data dictionary
  field. A data dictionary is a different input, so an entry carries the phv/pht/phs join
  and a description of what the variable feeds, and nothing else. `MetadataSource` exists as
  the seam if that ever widens.

  Worth knowing before anyone reaches for the obvious source: the toy dictionary at
  `toy_data/data_dictionary/toy_data_dictionary.tsv` carries only
  `table / Column Name / Description / Data Type / Example Value(s)`. It has no
  MIN/MAX/RESOLUTION/VALUES columns, so it cannot model these slots even as a stand-in.
- **No values are read from data.** Nothing computes an observed minimum or maximum, so
  there is no observed-versus-declared tension to resolve.
- **Deterministic means no model in the runtime path.** Per the Aug 11 note on #93, Claude
  wrote this script; it does not run inside it. Extraction is `ast`, `SchemaView`, and
  dataclasses.

## Open questions

Two remain.

- **Typing needs a second input.** "Single variable instances" are necessarily one of the
  two *typed* BDC classes, and a transformation spec does not say which a variable is. So
  the script takes `-s <schema-automator output>` — an input #93 does not mention.
  `source_id` and `file_id` are defined only on the typed classes, so emitting untyped is
  not available either. Worth confirming in the briefing.
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

## Two findings about the inputs

**1. The join to schema-automator output is exact, not fuzzy.** In the generated schema
(`$SYNTH/output/study_one/ExampleStudyOne.yaml`), classes are named by `pht` accession and
slots by `phv` accession:

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
imported sideways. Worth raising on the PR rather than deciding alone.

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

## What got built (steps 1–3)

11 files added, 4 modified.

### Step 1 — IR + `collect_variables` + unit tests

**Added**

| File | Contents |
|---|---|
| `src/dm_bip/variable_lib/__init__.py` | package marker |
| `src/dm_bip/variable_lib/extract.py` | `VariableUsage`, `VariableRecord`, `collect_variables` |
| `tests/unit/variable_lib/__init__.py` | package marker |
| `tests/unit/variable_lib/test_extract.py` | 10 tests |

Depends on nothing but the specs. Reuses the existing fixtures under
`tests/input/mapping_prov/ARIC-ingest/`, so no new spec fixtures were needed.

### Step 2 — `emit.py` (+ `classify.py`)

**Added**

| File | Contents |
|---|---|
| `src/dm_bip/variable_lib/emit.py` | `describe`, `to_entries`, `to_yaml`, `MetadataSource` |
| `src/dm_bip/variable_lib/classify.py` | `VariableKind`, `classify_from_source_schema`, `classifier_for` |
| `src/dm_bip/variable_lib/schema/variable_lib_schema.yaml` | gen-pydantic shim importing bdc-variable-library |
| `src/dm_bip/variable_lib/datamodel/__init__.py` | package marker |
| `src/dm_bip/variable_lib/datamodel/variable_lib.py` | generated, 3075 lines, lint-excluded |
| `tests/input/variable_lib/source_schema.yaml` | stand-in for schema-automator output |
| `tests/unit/variable_lib/test_emit.py` | 12 tests |

**Modified**

| File | Change |
|---|---|
| `Makefile` | split `datamodel` into `mapping-prov-datamodel` + `variable-lib-datamodel` |
| `pyproject.toml` | added the generated file to ruff's `extend-exclude` |

The schema shim exists only because `gen-pydantic` takes a local file and will not accept a
URL; it adds nothing of its own and imports the upstream schema by URL, tracking `main`
deliberately so open-question-4 fixes are picked up.

`classify.py` was step 4 in the original plan. It was pulled forward because a stub
classifier returning `unknown` would have emitted an empty file and proved nothing, whereas
the declared-range rule is defensible on its own.

### Step 3 — CLI + make target

**Modified**

| File | Change |
|---|---|
| `src/dm_bip/cli.py` | `extract-variable-library` command (+39 lines) |
| `pipeline.Makefile` | `VARIABLE_LIBRARY_FILE` variable and `variable-library` target (+14 lines) |

The make target takes `$(SCHEMA_FILE)` as a prerequisite alongside the specs — that
dependency is the typing question expressed in make: the specs say which variables exist,
the schema says what each one is. It is not wired into `make pipeline`.

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

Run from the dm-bip checkout, since `uv run` resolves against that project. `SYNTH` points
at the `synthetic/` directory of a study-palette checkout.

```bash
SYNTH=/path/to/study-palette/synthetic

# 1. Build the schema that types each variable (seconds)
make schema-create CONFIG=$SYNTH/pipeline/example_study_one.mk \
     SYNTH_DIR=$SYNTH SYNTH_OUTPUT_DIR=$SYNTH/output/study_one

# 2. Extract the variable library
uv run dm-bip extract-variable-library \
  $SYNTH/specs/example_study_one \
  -s $SYNTH/output/study_one/ExampleStudyOne.yaml \
  -o $SYNTH/output/study_one/variable-library.yaml
```

Where each argument comes from, for other studies:

| Argument | Value | Source |
|---|---|---|
| spec dir | `$SYNTH/specs/example_study_one` | `DM_TRANS_SPEC_DIR` in the config `.mk` |
| `-s` | `$SYNTH/output/study_one/ExampleStudyOne.yaml` | `$(DM_OUTPUT_DIR)/$(DM_SCHEMA_NAME).yaml` |
| `-o` | `$SYNTH/output/study_one/variable-library.yaml` | your choice; the make target uses this |

The make target wraps step 2 with those paths resolved from the config:

```bash
make variable-library CONFIG=$SYNTH/pipeline/example_study_one.mk \
     SYNTH_DIR=$SYNTH SYNTH_OUTPUT_DIR=$SYNTH/output/study_one
```

Being a file target, it prints **"Nothing to be done"** when the output is newer than its
inputs. Delete just that file to force a rebuild — not the output directory, which holds the
`-s` schema:

```bash
rm $SYNTH/output/study_one/variable-library.yaml
```

The direct `uv run` form always regenerates, which makes it the better loop while iterating.

To regenerate the checked-in datamodel after an upstream schema change (needs network):

```bash
make variable-lib-datamodel
```

Result on the synthetic study — 35 of 35 source variables typed and emitted, byte-identical
across runs.

## Running the tests

```bash
uv run pytest tests/unit/variable_lib -q     # the 22 new tests, ~3s
make test                                    # full suite, 318 tests, ~52s
```

Useful variants:

```bash
uv run pytest tests/unit/variable_lib/test_emit.py -v          # one file, with test names
uv run pytest tests/unit/variable_lib -k classify              # match by name
uv run pytest tests/unit/variable_lib -q -x                    # stop at first failure
uv run pytest tests/unit/variable_lib --cov=dm_bip.variable_lib --cov-report=term-missing
```

The `variable_lib` unit tests are fully offline — the classifier fixture is a local schema.
But `tests/integration/test_mapping_prov_schema.py`, which `make test` includes, **needs
network**: it validates against the upstream PROV schema imported by URL. Use
`uv run pytest tests/unit -q` to skip it.

The pydantic `UserWarning` about `FieldInfo(annotation=NoneType...)` is pre-existing noise
from the generated datamodel, not a failure.

Before pushing:

```bash
uv run ruff check && uv run ruff format --check   # both pass clean
make lint                                         # also runs the notebook checks
```

`make lint` currently exits non-zero on 16 pre-existing errors in `notebooks/*.ipynb`,
unrelated to this work.

---

## The classification question, made concrete

`phv10111100` is the participant identifier in the synthetic study. Its declared range in
the generated schema is `integer`, so the current rule types it **continuous** — which is
wrong: it is a label that happens to be numeric. Its `num_distinct_values` is `500` out of
500 rows, exactly the signal that would catch it.

That single variable is the whole typing question in one case. Worth putting in front of
Daniel as-is rather than describing it abstractly.

---

## Remaining work

- **Classification rule beyond declared range** — needs the typing question answered.
- **Real study accession** — needs the study-identity question answered.
- **`MetadataSource` implementation** — out of scope for #93; build only if scope widens.

Also not done:

- **Integration test** validating emitted entries against the upstream schema (the
  `tests/integration/test_mapping_prov_schema.py` equivalent). Needs a decision on whether
  to validate against the generation shim or the upstream URL.
- **Pipeline wiring** — #93 asks for a script, not a stage, so this is optional.
- **`docs/` page.** `docs/mapping-provenance.md` has no counterpart yet.
- **Upstream schema defects** are unfiled. Note that `data_type` and `unit`
  *do* resolve — `gen-pydantic` succeeds and `data_type` comes through as `DataTypeEnum`
  from the imported microschema profiles — so that half of the concern is resolved. The
  `alert_value`/`alert_values` duplication stands. Upstream `main` is at `535f837`, ahead of
  the local checkout at `fd49e7f`.
