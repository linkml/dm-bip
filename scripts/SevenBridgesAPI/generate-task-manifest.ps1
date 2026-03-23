<#
.SYNOPSIS
    Generates a batch task manifest (CSV) from the Seven Bridges project folder structure.

.DESCRIPTION
    Crawls the Seven Bridges API starting from the PilotParentStudies folder, iterates
    through each cohort and its consent groups, and produces a CSV file (batch_tasks.csv)
    mapping each consent-group folder name to its parent cohort (schema).

    The output CSV is consumed by submit-batch-tasks.ps1 to launch harmonization tasks.

.OUTPUTS
    batch_tasks.csv - Two-column CSV with headers: Filename, Schema

.NOTES
    Prerequisites:
      - A valid Seven Bridges developer token in ~/.sevenbridges/token or env var SBG_AUTH_TOKEN.
        See: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token

    Project: dm-bip (https://github.com/linkml/dm-bip)
#>

# --- CONFIGURATION ---
. "$PSScriptRoot\config.ps1"

# --- HELPER FUNCTION ---
# Retrieves folder-type children from the SBG files API.
# Pass -Project to list root-level folders, or -ParentID to list children of a specific folder.
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
$manifestRows = @()

foreach ($cohort in $cohorts) {
    $currentSchema = $cohort.name
    Write-Host "  Extracting Consent Groups for: $currentSchema" -ForegroundColor Yellow

    # 3. Iterate through Consent Groups inside each Cohort
    $consentGroups = Get-SBGContents -ParentID $cohort.id

    foreach ($group in $consentGroups) {
        $manifestRows += [PSCustomObject]@{
            Filename = $group.name
            Schema   = $currentSchema
        }
    }
}

# --- OUTPUT ---
$ManifestPath = Join-Path $PSScriptRoot "batch_tasks.csv"

if ($manifestRows.Count -gt 0) {
    $manifestRows | Export-Csv -Path $ManifestPath -NoTypeInformation -Encoding utf8
    
    Write-Host "`nSUCCESS: Manifest generated with $($manifestRows.Count) rows." -ForegroundColor Green
    Write-Host "File saved to: $ManifestPath" -ForegroundColor Cyan
    
    # Preview
    $manifestRows | Select-Object -First 50 | Format-Table -AutoSize
} else {
    Write-Host "No subfolders found." -ForegroundColor Red
}