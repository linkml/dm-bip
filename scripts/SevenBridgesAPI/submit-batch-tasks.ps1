<#
.SYNOPSIS
    Submits batch harmonization tasks to Seven Bridges from a CSV manifest.

.DESCRIPTION
    Reads batch_tasks.csv (produced by generate-task-manifest.ps1), resolves each
    consent-group folder to its Seven Bridges file ID, and launches a harmonization
    task for every row. Tasks are submitted sequentially with a 60-second delay
    between each to avoid API rate limits.

    Workflow:
      1. Pre-fetches all cohort folder IDs from PilotParentStudies.
      2. For each CSV row, resolves the consent-group folder inside its cohort.
      3. POSTs a new task to the SBG Tasks API and immediately runs it.

.INPUTS
    batch_tasks.csv - Two-column CSV (Filename, Schema) in the script directory.

.NOTES
    Prerequisites:
      - A valid Seven Bridges developer token in ~/.sevenbridges/token or env var SBG_AUTH_TOKEN.
        See: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token
      - Run generate-task-manifest.ps1 first to create batch_tasks.csv.

    Project: dm-bip (https://github.com/linkml/dm-bip)
#>

# --- CONFIGURATION ---
# To override the default AppID (e.g., a newer revision), set $AppID before this line:
#   $AppID = "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/32"
. "$PSScriptRoot\config.ps1"

# --- STEP 1: PRE-FETCH ALL COHORT PARENT IDS ---
Write-Host "Initializing Cohort Lookup Table..." -ForegroundColor Cyan

# 1a. Find the PilotParentStudies folder ID first
$rootFiles = Invoke-RestMethod -Uri "$BaseUrl/files?project=$ProjectID" -Method Get -Headers $Headers
$pilotRoot = $rootFiles.items | Where-Object { $_.name -eq "PilotParentStudies" -and $_.type -eq "folder" }

if (-not $pilotRoot) { Write-Error "Could not find PilotParentStudies folder."; return }

# 1b. Get all Cohort folders inside PilotParentStudies
$cohortFolders = Invoke-RestMethod -Uri "$BaseUrl/files?parent=$($pilotRoot.id)" -Method Get -Headers $Headers
$CohortLookup = @{}
foreach ($c in $cohortFolders.items | Where-Object { $_.type -eq "folder" }) {
    $CohortLookup[$c.name] = $c.id
}

Write-Host "Found $($CohortLookup.Count) cohorts (Schemas) available.`n" -ForegroundColor Green

# --- STEP 2: LOAD BATCH DATA ---
$ManifestPath = Join-Path $PSScriptRoot "batch_tasks.csv"

if (-not (Test-Path $ManifestPath)) {
    Write-Error "Manifest not found at $ManifestPath. Run generate-task-manifest.ps1 first."
    return
}

$BatchData = Import-Csv $ManifestPath
Write-Host "Loaded $($BatchData.Count) tasks from CSV.`n" -ForegroundColor Cyan

# --- STEP 3: EXECUTION LOOP ---
foreach ($row in $BatchData) {
    $Name = $row.Filename
    $Schema = $row.Schema
    
    Write-Host "Processing $Name ($Schema)..." -NoNewline

    # Get the correct Parent ID for this specific Schema
    $CurrentParentID = $CohortLookup[$Schema]

    if (-not $CurrentParentID) {
        Write-Host " [ERROR: Schema '$Schema' not found in PilotParentStudies]" -ForegroundColor Red
        continue
    }

    # Resolve Filename to Hex ID inside the CORRECT parent
    $EncodedName = [uri]::EscapeDataString($Name)
    $SearchUrl = "$BaseUrl/files?parent=$CurrentParentID&name=$EncodedName"
    $SearchResponse = Invoke-RestMethod -Uri $SearchUrl -Method Get -Headers $Headers
    $Folder = $SearchResponse.items | Where-Object { $_.type -eq "folder" -and $_.name -eq $Name }

    if (-not $Folder) {
        Write-Host " [ERROR: Folder not found inside $Schema]" -ForegroundColor Red
        continue
    }

    # Construct the SBG Task API request body.
    # Task name format: Harmonization_<Cohort>_<ConsentSuffix> (e.g., Harmonization_FHS_HMB)
    $TaskBody = @{
        project = $ProjectID
        app     = $AppID
        name    = "Harmonization_$($Schema)_$($Name.Split('-')[-1])"
        inputs  = @{
            Schema    = $Schema
            RawSource = @{
                class = "Directory"
                path  = $Folder.id
            }
        }
    } | ConvertTo-Json -Depth 10

    # Submit and immediately run the task (two-step: create draft, then execute)
    try {
        $CreateResponse = Invoke-RestMethod -Uri "$BaseUrl/tasks" -Method Post -Headers $Headers -Body $TaskBody
        $NewTaskID = $CreateResponse.id

        $RunUrl = "$BaseUrl/tasks/$NewTaskID/actions/run"
        Invoke-RestMethod -Uri $RunUrl -Method Post -Headers $Headers | Out-Null
        
        Write-Host " [RUNNING: $NewTaskID]" -ForegroundColor Green
    } catch {
        Write-Host " [FAILED: $($_.Exception.Message)]" -ForegroundColor Red
    }

    # Throttle: wait between submissions to avoid SBG API rate limits (skip after last task)
    if ($row -ne $BatchData[-1]) {
        Write-Host "Waiting 60 seconds before next submission..." -ForegroundColor Gray
        Start-Sleep -Seconds 60
    }
}

Write-Host "`nBatch process complete." -ForegroundColor Cyan