# SevenBridgesAPI Scripts

PowerShell scripts for automating harmonization task execution on the
[Seven Bridges BioData Catalyst](https://biodatacatalyst.nhlbi.nih.gov/) platform.

## Overview

| Script | Purpose |
|---|---|
| `config.ps1` | Shared configuration (token, project, app, headers) — dot-sourced by all scripts |
| `generate-task-manifest.ps1` | Crawls SBG project folders and generates `batch_tasks.csv` |
| `submit-batch-tasks.ps1` | Reads the manifest and launches harmonization tasks on SBG |
| `get-task-status.ps1` | Displays a live status dashboard for running tasks |

## Prerequisites

### 1. Get a Developer Token

Obtain an authentication token from the BioData Catalyst Seven Bridges platform:

**https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token**

### 2. Store the Token

The scripts look for your token in the following order:

1. **Environment variable** (recommended for CI/automation):
   ```powershell
   $env:SBG_AUTH_TOKEN = "your-token-here"
   ```

2. **Token file** (recommended for local development):
   ```
   ~/.sevenbridges/token
   ```
   Create this file with your token as the only content (one line, no quotes):
   ```powershell
   # PowerShell
   New-Item -ItemType Directory -Path "$HOME/.sevenbridges" -Force
   Set-Content -Path "$HOME/.sevenbridges/token" -Value "your-token-here"
   ```
   ```bash
   # Bash / WSL
   mkdir -p ~/.sevenbridges
   echo "your-token-here" > ~/.sevenbridges/token
   ```

> **Security note:** The token file lives in your home directory, outside the
> repository, so there is no risk of accidentally committing it. Never paste
> your token directly into a script.
>
> **Note:** `batch_tasks.csv` is a generated file and is excluded via `.gitignore`.
> Do not commit it to the repository.

## Usage

### Step 1: Generate the Task Manifest

```powershell
cd scripts/SevenBridgesAPI
.\generate-task-manifest.ps1
```

This crawls `PilotParentStudies` in the configured SBG project and produces
`batch_tasks.csv` — a two-column CSV mapping each consent-group folder to its
parent cohort:

```
Filename,Schema
phs000007-HMB-IRB-MDS,FHS
phs000007-HMB-IRB-NPU,FHS
...
```

### Step 2: Submit Batch Tasks

```powershell
.\submit-batch-tasks.ps1
```

Reads `batch_tasks.csv`, resolves each folder to its SBG file ID, and launches
a harmonization task for every row. Tasks are submitted with a 60-second delay
between each to avoid API rate limits.

To use a different app revision:

```powershell
$AppID = "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/32"
.\submit-batch-tasks.ps1
```

### Step 3: Monitor Running Tasks

```powershell
.\get-task-status.ps1
```

Displays a table of all running tasks with name, health status, submission time,
elapsed duration, and instance type. Tasks with no active compute jobs are
flagged as `!! ZOMBIE !!`.

## Configuration

All shared settings live in `config.ps1`:

| Variable | Description |
|---|---|
| `$Token` | Developer auth token (resolved from env var or file) |
| `$BaseUrl` | SBG API base URL (`https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2`) |
| `$ProjectID` | Target SBG project ID |
| `$AppID` | Harmonization app (CWL workflow) revision — can be overridden per-run |
| `$Headers` | Pre-built HTTP headers with auth token |
