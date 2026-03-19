# --- Configuration ---
# --- CONFIGURATION ---
# Pull the token from the external file and trim any hidden whitespace/newlines
$TokenPath = "$PSScriptRoot\token.txt"

if (Test-Path $TokenPath) {
    $Token = (Get-Content $TokenPath).Trim()
} else {
    Write-Error "Token file not found at $TokenPath. Please create it and try again."
    return
}

$BaseUrl = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
$ProjectID = "rmathur2/dmc-task-4-controlled"
$Headers = @{ "X-SBG-Auth-Token" = $Token; "Content-Type" = "application/json" }

# --- Helper Function: Get Folder Contents ---
function Get-SBGContents {
    param ([string]$ParentID, [string]$Project = $null)
    $url = if ($Project) { "$BaseUrl/files?project=$Project" } else { "$BaseUrl/files?parent=$ParentID" }
    $response = Invoke-RestMethod -Uri $url -Method Get -Headers $Headers
    return $response.items | Where-Object { $_.type -eq "folder" }
}

# --- Execution: Crawl and Map ---
Write-Host "Crawl started: Building manifest (No Quotes)..." -ForegroundColor Cyan

# 1. Find PilotParentStudies at the root
$rootFolders = Get-SBGContents -Project $ProjectID
$pilotRoot = $rootFolders | Where-Object { $_.name -eq "PilotParentStudies" }

if (-not $pilotRoot) { 
    Write-Error "Could not find 'PilotParentStudies' folder."
    return 
}

# 2. Iterate through Cohorts
$cohorts = Get-SBGContents -ParentID $pilotRoot.id
$rows = @("Filename,Schema") # Start with the Header row

foreach ($cohort in $cohorts) {
    $currentSchema = $cohort.name
    Write-Host "  Extracting Consent Groups for: $currentSchema" -ForegroundColor Yellow

    # 3. Iterate through Consent Groups inside each Cohort
    $consentGroups = Get-SBGContents -ParentID $cohort.id

    foreach ($group in $consentGroups) {
        # Join the filename and schema with a comma, no quotes
        $rows += "$($group.name),$currentSchema"
    }
}

# --- Save Results without Quotes ---
if ($rows.Count -gt 1) {
    $rows | Set-Content -Path "batch_tasks.csv" -Encoding utf8
    
    Write-Host "`nSUCCESS: Manifest generated with $($rows.Count - 1) rows (Quote-Free)." -ForegroundColor Green
    Write-Host "File saved to: batch_tasks.csv" -ForegroundColor Cyan
    
    # Preview
    $rows | Select-Object -First 50
} else {
    Write-Host "No subfolders found." -ForegroundColor Red
}