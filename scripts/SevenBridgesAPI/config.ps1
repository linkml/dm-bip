<#
.SYNOPSIS
    Shared configuration for all SevenBridgesAPI scripts.

.DESCRIPTION
    Loads the developer token and sets common variables (ProjectID, AppID, BaseUrl,
    Headers) used by generate-task-manifest.ps1, submit-batch-tasks.ps1, and
    get-task-status.ps1.

    Dot-source this file at the top of each script:
      . "$PSScriptRoot\config.ps1"

.PARAMETER AppID
    Optional. Override the default harmonization app (CWL workflow) revision.
    Set $AppID before dot-sourcing config.ps1 to override the default.

.NOTES
    Token resolution order:
      1. Environment variable SBG_AUTH_TOKEN (useful for CI/automation)
      2. File at ~/.sevenbridges/token (recommended for local development)

    To create the token file:
      mkdir ~/.sevenbridges
      # Paste your token into ~/.sevenbridges/token (one line, no quotes)

    Get a token: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token
#>

# --- TOKEN ---
# Resolve token: environment variable takes precedence, then ~/.sevenbridges/token
$TokenPath = Join-Path $HOME ".sevenbridges" "token"

if ($env:SBG_AUTH_TOKEN) {
    $Token = $env:SBG_AUTH_TOKEN.Trim()
} elseif (Test-Path $TokenPath) {
    $Token = (Get-Content -Raw $TokenPath).Trim()
} else {
    Write-Error @"
Seven Bridges auth token not found.

Provide it via ONE of:
  1. Environment variable:  `$env:SBG_AUTH_TOKEN = 'your-token'
  2. Token file:            $TokenPath

Get a token at: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token
"@
    return
}

# --- PROJECT & APP ---
$BaseUrl   = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
$ProjectID = "rmathur2/dmc-task-4-controlled"

# AppID can be overridden by setting it before dot-sourcing this file
if (-not $AppID) {
    $AppID = "rmathur2/dmc-task-4-controlled/dm-bip-test-siege/31"
}

# --- HEADERS ---
$Headers = @{
    "X-SBG-Auth-Token" = $Token
    "Content-Type"     = "application/json"
}
