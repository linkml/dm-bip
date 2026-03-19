# --- CONFIGURATION ---
# --- CONFIGURATION ---
# Pull the token from the external file and trim any hidden whitespace/newlines
$TokenPath = "$PSScriptRoot\token.txt"

if (Test-Path $TokenPath) {
    $Token = (Get-Content $TokenPath).Trim()
} else {
    Write-Error "Token file not found at $TokenPath. Please create it and try again."
    return
}

$ProjectID = "rmathur2/dmc-task-4-controlled"
$AppID = "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/31"
$BaseUrl = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
$JHSParentID = "698f1ca3c4824a34ffbad769" # The 'JHS' folder ID

$Headers = @{
    "X-SBG-Auth-Token" = $Token
    "Content-Type"     = "application/json"
}

# --- STEP 1: PRE-FETCH ALL COHORT PARENT IDS ---
Write-Host "Initializing Cohort Lookup Table..." -ForegroundColor Cyan

# 1a. Find the PilotParentStudies folder ID first
$rootFiles = Invoke-RestMethod -Uri "$BaseUrl/files?project=$ProjectID" -Method Get -Headers $Headers
$pilotRoot = $rootFiles.items | Where-Object { $_.name -eq "PilotParentStudies" }

if (-not $pilotRoot) { Write-Error "Could not find PilotParentStudies folder."; return }

# 1b. Get all Cohort folders inside PilotParentStudies
$cohortFolders = Invoke-RestMethod -Uri "$BaseUrl/files?parent=$($pilotRoot.id)" -Method Get -Headers $Headers
$CohortLookup = @{}
foreach ($c in $cohortFolders.items) {
    $CohortLookup[$c.name] = $c.id
}

Write-Host "Found $($CohortLookup.Count) cohorts (Schemas) available.`n" -ForegroundColor Green

# --- STEP 2: LOAD BATCH DATA ---
$BatchData = Import-Csv "batch_tasks.csv"
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
    $SearchUrl = "$BaseUrl/files?parent=$CurrentParentID&name=$Name"
    $SearchResponse = Invoke-RestMethod -Uri $SearchUrl -Method Get -Headers $Headers
    $Folder = $SearchResponse.items | Where-Object { $_.name -eq $Name }

    if (-not $Folder) {
        Write-Host " [ERROR: Folder not found inside $Schema]" -ForegroundColor Red
        continue
    }

    # Construct Task Body
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

    # Fire Task
    try {
        $CreateResponse = Invoke-RestMethod -Uri "$BaseUrl/tasks" -Method Post -Headers $Headers -Body $TaskBody
        $NewTaskID = $CreateResponse.id

        $RunUrl = "$BaseUrl/tasks/$NewTaskID/actions/run"
        $RunResponse = Invoke-RestMethod -Uri $RunUrl -Method Post -Headers $Headers
        
        Write-Host " [RUNNING: $NewTaskID]" -ForegroundColor Green
    } catch {
        Write-Host " [FAILED: $($_.Exception.Message)]" -ForegroundColor Red
    }
	
	# --- SURGICAL ADDITION ---
    Write-Host "Waiting 1 minutes before processing the next cohort..." -ForegroundColor Gray
    Start-Sleep -Seconds 60
}

Write-Host "`nBatch process complete." -ForegroundColor Cyan