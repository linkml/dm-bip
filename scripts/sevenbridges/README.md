# Seven Bridges API Scripts

Python scripts for launching and monitoring harmonization tasks on
[BioData Catalyst](https://biodatacatalyst.nhlbi.nih.gov/) (Seven Bridges).

## Setup

### 1. Get a Developer Token

Follow the [Seven Bridges token guide](https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token).

### 2. Store the Token

**Option A — Environment variable** (CI/automation):

```bash
export SBG_AUTH_TOKEN="your-token-here"
```

**Option B — Token file** (local development):

```bash
mkdir -p ~/.sevenbridges
echo "your-token-here" > ~/.sevenbridges/token
```

The token file lives outside the repo — no risk of committing it.

## Usage

All scripts use `uv run` from the repo root. Each has `--help` for options.

### Step 1: Generate the task manifest

```bash
uv run python scripts/sevenbridges/generate_manifest.py
```

Crawls `PilotParentStudies` in the SBG project and produces `batch_tasks.csv` —
a two-column CSV mapping each consent-group folder to its parent cohort:

```
Filename,Schema
phs000007-HMB-IRB-MDS,FHS
phs000007-HMB-IRB-NPU,FHS
```

### Step 2: Submit batch tasks

```bash
uv run python scripts/sevenbridges/submit_tasks.py
```

Reads `batch_tasks.csv`, resolves each folder to its SBG file ID, and launches
a harmonization task for every row with a 60-second throttle between submissions.

Options:

```bash
# Use a different app revision
uv run python scripts/sevenbridges/submit_tasks.py --app "rmathur2/dmc-task-4-controlled/cc-dm-bip-test/4"

# Change throttle between submissions
uv run python scripts/sevenbridges/submit_tasks.py --throttle 30
```

### Step 3: Monitor running tasks

```bash
uv run python scripts/sevenbridges/check_status.py
```

Shows a table of running tasks with health status, duration, and instance type.
Tasks with no active compute jobs are flagged as `!! ZOMBIE !!`.

## Configuration

Default project and app IDs are set in `sbg_api.py`. Override per-run via CLI options:

```bash
uv run python scripts/sevenbridges/submit_tasks.py --project "other/project" --app "other/app/id/1"
```

| Setting | Value |
|---|---|
| Project | `rmathur2/dmc-task-4-controlled` |
| Default App (dev) | `rmathur2/dmc-task-4-controlled/cc-dm-bip-test/4` |
| Prod App | `rmathur2/dmc-task-4-controlled/dm-bip-test-siege/32` |
| API URL | `https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2` |

The **dev app** (`cc-dm-bip-test`) runs with `BDC_PULL_LATEST=true` (non-strict mode,
pulls latest repos, supports `--trans-spec`). The **prod app** (`dm-bip-test-siege`)
runs with pinned versions and strict mode. Switch with `--app`:

```bash
# Run against prod app
uv run python scripts/sevenbridges/submit_tasks.py --app "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/32"
```
