# BDC Cohort Harmonization Workflow

This document covers both execution modes for harmonizing BioData Catalyst
(BDC) cohort data with dm-bip, using **COPDGene** (two consent groups: `c1`
and `c2`) as a worked example throughout.

---

## Overview

| Mode | Entry point | Use case |
|---|---|---|
| **Single Consent Execution** | `bdc-workflow.sh` | One consent group at a time — for debugging, re-runs, or when only one consent group needs to be processed |
| **Parallel Multi-Consent Execution** | `bdc-cohort-workflow.sh` | All consent groups for one cohort in a single task — harmonizes in parallel, then runs hv_dataqc comparison automatically |

Both modes use the same Docker image. The Parallel Multi-Consent Execution
entry point internally calls `bdc-workflow.sh` once per consent group, so
everything the single-consent mode does is preserved and unchanged.

---

## Prerequisites

### SBG authentication

The `dm-bip seven-bridges` CLI commands require your Seven Bridges auth token.
Set it before running any `seven-bridges` subcommand:

```powershell
$env:SBG_AUTH_TOKEN = "your-token-here"
# OR place the token in: $HOME/.sevenbridges/token
```

Get a token: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token

### SBG project

The default project is `rmathur2/dmc-task-4-controlled`. Override if yours differs:

```powershell
$env:SBG_DEFAULT_PROJECT = "your-org/your-project"
```

### SBG app (cohort mode)

Cohort mode has **no default app**. Either pass `--cohort-app` on every
invocation, or set it once:

```powershell
$env:SBG_DEFAULT_COHORT_APP = "owner/project/dmc-harmonization-multiconsent-app"
```

`submit` and `plan` print the resolved project and app before doing anything, and
say which of the two sources it came from. Check that line: **the app's own
"Docker Repository" field decides which container image runs**, so the app ID is
what selects dev vs test vs prod images, not anything in the CLI.

An app ID with no trailing `/<revision>` runs the app's latest revision. Editing
the Docker Repository field creates a new revision, so a pinned ID such as
`.../my-app/4` keeps running the old image.

### Dev mode (`BDC_PULL_LATEST`) and cohort mode

**Cohort mode does not require dev mode** for `--trans-spec` or
`--hv-dataqc-branch`. `bdc-cohort-workflow.sh` resolves the trans-spec slug to a
SHA and pre-clones it once at startup, then hands each per-consent worker
`DM_TRANS_SPEC_DIR_PREBUILT`. Workers never run git, so they never reach
`bdc-workflow.sh`'s dev-mode gate. `--hv-dataqc-branch` is likewise fetched and
checked out by `bdc-cohort-workflow.sh` itself.

This error --

```
ERROR: --trans-spec is only supported when BDC_PULL_LATEST=true (dev mode)
```

-- comes from `bdc-workflow.sh` and applies to **Single Consent Execution Mode
only**, i.e. `submit` *without* `--cohort-mode`.

What dev mode does still change in cohort mode: `bdc-workflow.sh` sets
`DM_MAP_STRICT=false` when `BDC_PULL_LATEST=true`. On a test- or prod-tier image
(built `false`) mapping runs **strict** and aborts a consent group on the first
error rather than logging every error in one pass. Combined with the default
`--strict-consent-groups`, one bad transform can end the cohort run early. Pass
`--no-strict-consent-groups` for a survey run.

Note that `--strict-hv-dataqc-branch` defaults to `true` inside the container and
is not exposed by the CLI, so a failed `--hv-dataqc-branch` fetch is fatal.

### Working directory

All `uv run dm-bip` commands must be run from the dm-bip repository root:

```powershell
cd c:\SourceCode\dm-bip
```

---

## Mode 1: Single Consent Execution (COPDGene example)

Run one consent group at a time against the existing single-consent SBG app.
Use this for debugging, targeted re-runs, or when you need to inspect the
output of one specific consent group in isolation.

### Step 1 — Generate the task manifest

```powershell
uv run dm-bip seven-bridges manifest -o batch_tasks.csv
```

This crawls `PilotParentStudies_NoDRS/<Cohort>/<consent-group>` in your SBG
project and emits a CSV row per consent group:

```
Filename,Schema
COPDGene-c1,COPDGene
COPDGene-c2,COPDGene
FHS-c1,FHS
...
```

### Step 2 — Filter to COPDGene only

```powershell
"Filename,Schema" | Set-Content copdgene_tasks.csv
Get-Content batch_tasks.csv | Where-Object { $_ -match 'COPDGene$' } |
  Add-Content copdgene_tasks.csv
Get-Content copdgene_tasks.csv
# Expected output:
#   Filename,Schema
#   COPDGene-c1,COPDGene
#   COPDGene-c2,COPDGene
```

### Step 3 — Submit two per-consent tasks (using baked image defaults)

```powershell
uv run dm-bip seven-bridges submit --manifest copdgene_tasks.csv
```

This submits two tasks — one for `COPDGene-c1`, one for `COPDGene-c2` — each
using whatever HV YAML version is baked into the current Docker image. Tasks
are throttled at 60 seconds between submissions by default.

### Step 3 (alt) — Submit using a specific HV branch

Requires the SBG app to be running in dev mode (`BDC_PULL_LATEST=true`):

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main
```

To skip the 60 s throttle between the two submissions:

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main `
  --throttle 0
```

> **Tip:** pin to a SHA instead of a branch name for reproducibility:
> `--trans-spec RTIInternational/NHLBI-BDC-DMC-HV@abc123def456`
>
> Get the current main SHA:
> ```powershell
> git ls-remote https://github.com/RTIInternational/NHLBI-BDC-DMC-HV.git refs/heads/main
> ```

### Step 4 — Monitor task progress

```powershell
uv run dm-bip seven-bridges status
```

### Step 5 — Fetch logs for a specific task

```powershell
uv run dm-bip seven-bridges logs <task-id>
```

### Output layout (per consent group)

Each Single Consent Execution task writes to:
```
$HOME/DMC_COPDGene-c1_COPDGene_Processed_<YYYYMMDD_HHMMSS>/
├── COPDGene-c1_CleanedSource/     # prepared input TSV files
├── COPDGene-c1_BDCHM/
│   ├── mapped-data/               # harmonized output TSVs
│   ├── validation-logs/
│   └── provenance.yaml
├── pipeline.log
└── Dockerfile.archived
```

---

## Mode 2: Parallel Multi-Consent Execution (COPDGene example)

Run all consent groups for COPDGene in a single task. The cohort driver
harmonizes both consent groups in parallel, then automatically runs hv_dataqc
(source extract + harmonized extract + compare report) across both.

### Step 1 — Generate and review the manifest (same as Mode 1)

```powershell
uv run dm-bip seven-bridges manifest -o batch_tasks.csv
Get-Content batch_tasks.csv
```

### Step 2 — Preview the cohort-mode task body (dry run, no API calls)

```powershell
uv run dm-bip seven-bridges plan `
  --manifest copdgene_tasks.csv `
  --cohort-app <your-cohort-mode-app-id> `
  --dbgap-cache <sbg-folder-id-for-dbgap-cache>
```

This prints the JSON task body that `submit --cohort-mode` would post — no
tasks are actually submitted. Verify the consent-group list and inputs look
correct before going live.

To include real SBG folder IDs in the preview (requires API call):

```powershell
uv run dm-bip seven-bridges plan `
  --manifest copdgene_tasks.csv `
  --cohort-app <your-cohort-mode-app-id> `
  --dbgap-cache <sbg-folder-id-for-dbgap-cache> `
  --resolve-folders
```

### Step 3 — Submit one cohort-mode task

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --cohort-mode `
  --cohort-app <your-cohort-mode-app-id> `
  --dbgap-cache <sbg-folder-id-for-dbgap-cache>
```

This submits **one** task for COPDGene (not two). The task internally
processes both consent groups in parallel, then runs hv_dataqc at the end.

### Step 3 (alt) — With a specific HV branch

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --cohort-mode `
  --cohort-app <your-cohort-mode-app-id> `
  --dbgap-cache <sbg-folder-id-for-dbgap-cache> `
  --trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main
```

> **Note:** when `--trans-spec` is used, the HV repo is cloned and checked out
> once at task startup. All parallel workers share the pre-built YAML directory
> via the `DM_TRANS_SPEC_DIR_PREBUILT` environment variable — no repeated
> git operations, no race conditions.

### Step 3 (alt) — Allow a known-problematic consent group to fail gracefully

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --cohort-mode `
  --cohort-app <your-cohort-mode-app-id> `
  --allow-fail COPDGene:COPDGene-c2
```

If `COPDGene-c2` fails, it is recorded as `FAIL_ALLOWED` in
`consent_group_status.tsv` and hv_dataqc runs on the surviving consent group
(`COPDGene-c1` only). The task still exits 0.

### Step 3 (alt) — Continue through failures and still run hv_dataqc

```powershell
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --cohort-mode `
  --cohort-app <your-cohort-mode-app-id> `
  --no-strict-consent-groups `
  --no-strict-hv-dataqc
```

Any unauthorized failures are recorded as `FAIL` (not `FAIL_ALLOWED`) and
hv_dataqc runs on the survivors. The report banner marks the run `PARTIAL`.

### Step 4 — Monitor and fetch logs (same commands as Mode 1)

```powershell
uv run dm-bip seven-bridges status
uv run dm-bip seven-bridges logs <task-id>
```

### Output layout (whole cohort)

The Parallel Multi-Consent Execution task writes one top-level folder:

```
$HOME/DMC_COPDGene_<YYYYMMDD_HHMMSS>/
├── run_manifest.yaml                        # cohort, timestamps, HM/HV commits,
│                                            # per-consent status list, overall_status
├── consent_group_status.tsv                 # flat one-row-per-consent summary
├── consent_groups/
│   ├── COPDGene-c1/                         # same layout as Single Consent output
│   │   ├── COPDGene-c1_CleanedSource/
│   │   ├── COPDGene-c1_BDCHM/
│   │   │   ├── mapped-data/
│   │   │   ├── validation-logs/
│   │   │   └── provenance.yaml
│   │   ├── pipeline.log
│   │   └── Dockerfile.archived
│   └── COPDGene-c2/                         # same structure
├── hv_dataqc/
│   ├── source/copdgene_source_<ts>.json     # aggregate-only source stats
│   ├── harmonized/copdgene_harmonized_<ts>.json  # aggregate-only harmonized stats
│   └── compare/
│       ├── copdgene_comparison_report.md    # the QC report
│       ├── copdgene_comparison_results.json
│       └── manifest.json                    # inputs, git commits, step status
└── logs/
    ├── cohort-workflow.log                  # top-level driver log
    ├── COPDGene-c1/pipeline.log
    └── COPDGene-c2/pipeline.log
```

### While a consent group is running

`bdc-workflow.sh` writes to `$HOME`, which is redirected to
`logs/<cg>/HOME/`. Live output appears there while the consent group is
in progress:

```
DMC_COPDGene_<ts>/
└── logs/
    └── copdgene_phs000179_v7_r1_c1/
        └── HOME/
            └── DMC_copdgene_phs000179_v7_r1_c1_COPDGene_Processed_<ts>/
                ├── copdgene_phs000179_v7_r1_c1_CleanedSource/   ← input being prepared
                ├── copdgene_phs000179_v7_r1_c1_BDCHM/
                │   ├── mapped-data/                             ← entity TSVs appear as entities complete
                │   └── validation-logs/
                └── pipeline.log                                 ← live progress
```

### When a consent group finishes

`bdc-cohort-workflow.sh` moves the completed output from the `HOME/`
isolation area into the stable `consent_groups/` location:

```
DMC_COPDGene_<ts>/
└── consent_groups/
    └── copdgene_phs000179_v7_r1_c1/         ← moved here on consent-group completion
        ├── copdgene_phs000179_v7_r1_c1_CleanedSource/
        ├── copdgene_phs000179_v7_r1_c1_BDCHM/
        │   └── mapped-data/
        └── pipeline.log
```

A row is also appended to `consent_group_status.tsv` (`PASS` or `FAIL`).
Once all consent groups are in `consent_groups/`, the hv_dataqc fan-in
starts and `hv_dataqc/` appears under `DMC_COPDGene_<ts>/`.

---

## Reference: All bdc-cohort-workflow.sh options

```
--schema <COHORT>                   Required. Cohort name (e.g. COPDGene).
--consent-group <DIR>               Repeatable. Path to one consent-group raw source dir.
--dbgap-cache <DIR>                 Optional. Mounted dbGaP cache root.
                                    Layout: <root>/<cohort-lowercase>/pheno_variable_summaries/*.xml
                                    If missing, hv_dataqc compare step is skipped.
--allow-fail <CG_NAME>              Repeatable. Consent group allowed to fail without
                                    stopping the workflow.
--strict-consent-groups true|false  Default: true (fail-fast — halt remaining consent groups
                                    on first unauthorized failure).
--strict-hv-dataqc true|false       Default: true (skip hv_dataqc if any unauthorized failure).
--strict-hv-dataqc-branch true|false  Default: true (fail at startup if --hv-dataqc-branch
                                      fetch/checkout fails).
--consent-parallelism N             Default: computed from vCPU count (typically 2 on 8 vCPU).
--jobs N                            Default: 8. Per-consent make -j (validate step parallelism).
--output-root <DIR>                 Default: $HOME.
--hv-dataqc-branch <name>           Override hv_dataqc code branch (separate from YAML branch).
--trans-spec OWNER/REPO[@REF][:PATH]  Alternate YAML source. SHA-pinned at startup; pre-checked
                                      out once; workers never touch git.
--profile                           Enable map-step CPU/memory diagnostics (forwarded to
                                    bdc-workflow.sh).
```

---

## Reference: dm-bip seven-bridges CLI quick reference

### `manifest` — discover consent groups in SBG project

```powershell
uv run dm-bip seven-bridges manifest -o batch_tasks.csv
```

### `plan` — dry-run for cohort-mode (no task submission)

```powershell
uv run dm-bip seven-bridges plan `
  --manifest copdgene_tasks.csv `
  --cohort-app <app-id> `
  --dbgap-cache <folder-id> `
  [--allow-fail COPDGene:COPDGene-c2] `
  [--trans-spec RTIInternational/NHLBI-BDC-DMC-HV@main] `
  [--resolve-folders]                # add to get real SBG folder IDs in the preview
```

### `submit` — submit tasks from the manifest

```powershell
# Single Consent Execution (one task per row):
uv run dm-bip seven-bridges submit --manifest copdgene_tasks.csv

# Parallel Multi-Consent Execution (one task per cohort):
uv run dm-bip seven-bridges submit `
  --manifest copdgene_tasks.csv `
  --cohort-mode `
  --cohort-app <app-id> `
  --dbgap-cache <folder-id>
```

### `status` — check running tasks

```powershell
uv run dm-bip seven-bridges status
```

### `logs` — fetch task logs

```powershell
uv run dm-bip seven-bridges logs              # list recent tasks
uv run dm-bip seven-bridges logs <task-id>    # fetch specific task log
```

---

## SBG app configuration

### Single Consent Execution app (existing)

No changes required. Set `BDC_PULL_LATEST=true` in the app's environment if
you need to use `--trans-spec` for branch-targeted testing.

### Parallel Multi-Consent Execution app (new)

Create a new SBG app pointing at the same Docker image with these settings:

| Input name | Type | Description |
|---|---|---|
| `Schema` | string | Cohort name |
| `ConsentGroups` | Directory[] | One per consent group |
| `DbgapCache` | Directory | Shared dbGaP cache directory |
| `AllowFail` | string[] | Consent groups allowed to fail (optional) |
| `StrictConsentGroups` | string | `"true"` / `"false"`, default `"true"` -- see note below |
| `StrictHvDataqc` | string | `"true"` / `"false"`, default `"true"` -- see note below |
| `HvDataqcBranch` | string | hv_dataqc code branch override (optional) |
| `TransSpec` | string | YAML source slug (optional, e.g. `RTIInternational/NHLBI-BDC-DMC-HV@main`) |
| `Jobs` | integer | Default: 8 |
| `ConsentParallelism` | integer | Optional. Only sent when `--consent-parallelism` is passed; otherwise the script computes its own default -- see [Sizing guidance](#sizing-guidance) |

**`StrictConsentGroups` and `StrictHvDataqc` are strings, not booleans.** The CLI
posts them as the lowercase strings `"true"` / `"false"`, because the SBG API
rejected native JSON booleans for these inputs (`str(x).lower()` in
`_build_cohort_task_bodies`). Declaring them as `boolean` in the app will not
match what the CLI sends. When wiring a new app, confirm the input types against
the existing `dmc-harmonization-multiconsent-app`, which is the working
reference.

Entry point command:
```bash
/app/scripts/workflow/bdc-cohort-workflow.sh \
  --schema $(Schema) \
  --consent-group $(ConsentGroups[*]) \
  --dbgap-cache $(DbgapCache) \
  ... (map remaining inputs)
```

---

## Failure semantics

| Consent group failed? | In `--allow-fail`? | `--strict-consent-groups` | Loop behavior | hv_dataqc | `overall_status` |
|---|---|---|---|---|---|
| No | — | — | continues | runs on all | PASS |
| Yes | Yes | — | continues | runs on survivors | PASS |
| Yes | No | true (default) | halts remaining | skipped | FAIL |
| Yes | No | false, strict-hv-dataqc=true | continues | skipped | FAIL |
| Yes | No | false, strict-hv-dataqc=false | continues | runs on survivors, PARTIAL banner | PARTIAL |

**The container always exits 0** regardless of outcome. Status is captured in
`run_manifest.yaml`, `consent_group_status.tsv`, and the hv_dataqc compare
report. This means SBG will always mark the task as "Completed" — check the
`overall_status` field in `run_manifest.yaml` for the actual result.

---

## Sizing guidance

When `--consent-parallelism` is not passed, `bdc-cohort-workflow.sh` computes:

```
min(#consent-groups, max(1, floor(vCPU / --jobs)))
```

The intent is to hold peak validate-step concurrency
(`consent-parallelism x jobs`) at roughly vCPU. Because the default `--jobs` is
8, the computed default depends on `--jobs`:

| vCPU | `--jobs` | Computed `--consent-parallelism` | Peak threads |
|---|---|---|---|
| 8 | 8 (default) | 1 -- **serial** | 8 |
| 8 | 4 | 2 | 8 |
| 16 | 8 | 2 | 16 |
| 16 | 4 | 4 | 16 |

The result is also capped by the number of consent groups, so a cohort with 2
consent groups never exceeds 2 regardless of vCPU.

**On a typical 8-vCPU SBG instance the default `--jobs 8` means consent groups
run serially.** To overlap them, lower `--jobs` rather than raising
`--consent-parallelism`:

```bash
--consent-parallelism 2 --jobs 4   # 2 x 4 = 8 threads peak, fits 8 vCPU
--consent-parallelism 4 --jobs 4   # 4 x 4 = 16 threads peak, fits 16 vCPU
```

Raising `--consent-parallelism` without lowering `--jobs` oversubscribes the
instance: `--consent-parallelism 4 --jobs 8` peaks at 32 threads, 4x an 8-vCPU
instance.

Single Consent Execution Mode runs one worker, so `--jobs 8` gives that worker
the whole instance.

---

## Tracking

This feature was implemented in [linkml/dm-bip#350](https://github.com/linkml/dm-bip/issues/350)
on branch `feature/bdc-cohort-workflow`.
