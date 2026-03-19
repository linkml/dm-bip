<#
.SYNOPSIS
    Displays a live status dashboard for running Seven Bridges tasks.

.DESCRIPTION
    Queries the Seven Bridges Tasks API for all currently RUNNING tasks in the
    configured project and renders a formatted table showing:
      - Task name (truncated to 25 chars)
      - Health status (Healthy, Zombie, or API Delay)
      - Submission time (local timezone)
      - Elapsed duration (computed in UTC for accuracy)
      - Instance type

    A task is flagged as "ZOMBIE" if it has no active jobs in its execution details,
    which may indicate a stalled or orphaned task requiring manual intervention.

.NOTES
    Prerequisites:
      - A valid Seven Bridges developer token in ~/.sevenbridges/token or env var SBG_AUTH_TOKEN.
        See: https://sb-biodatacatalyst.readme.io/docs/get-your-authentication-token

    Project: dm-bip (https://github.com/linkml/dm-bip)
#>

# --- CONFIGURATION ---
. "$PSScriptRoot\config.ps1"

Write-Host "`n--- TASK STATUS: $ProjectID ---" -ForegroundColor Cyan

# --- STEP 1: Fetch all tasks with RUNNING status (up to 100) ---
$TasksUrl = "$BaseUrl/tasks?project=$ProjectID&status=RUNNING&limit=100"
$RunningTasks = Invoke-RestMethod -Uri $TasksUrl -Method Get -Headers $Headers

# Capture UTC now — all duration math uses UTC to avoid timezone drift
$NowUTC = (Get-Date).ToUniversalTime()

if ($null -eq $RunningTasks.items -or $RunningTasks.items.Count -eq 0) {
    Write-Host "No active tasks found." -ForegroundColor Green
    return
}

# --- STEP 2: Build report by inspecting each task's metadata and execution details ---
$Report = foreach ($t in $RunningTasks.items) {
    # Fetch full task object (the list endpoint returns a summary only)
    $fullTask = Invoke-RestMethod -Uri "$BaseUrl/tasks/$($t.id)" -Method Get -Headers $Headers
    
    $submittedOnLocal = "N/A"
    $durationStr = "00h 00m"
    
    if ($fullTask.created_time) {
        # Seven Bridges returns ISO 8601 UTC strings
        $createdUTC = [DateTime]$fullTask.created_time
        
        # MATH: UTC - UTC = Accurate Duration
        $timeSpan = $NowUTC - $createdUTC
        
        # FORMAT: For your display, convert to local EDT time
        $submittedOnLocal = $createdUTC.ToLocalTime().ToString("MM/dd HH:mm")
        
        # Handle "Total Hours" for tasks running over 24 hours
        $totalHours = [Math]::Floor($timeSpan.TotalHours)
        # Defensive: If clock skew makes duration negative, show 0
        if ($totalHours -lt 0) { $totalHours = 0; $mins = 0 } else { $mins = $timeSpan.Minutes }
        
        $durationStr = "{0:00}h {1:00}m" -f $totalHours, $mins
    }

    # --- INFRASTRUCTURE HEALTH CHECK ---
    # Query execution_details to determine if the task has active compute jobs.
    $health = "Healthy"
    $instance = "Pending..."
    
    try {
        $Details = Invoke-RestMethod -Uri "$BaseUrl/tasks/$($t.id)/execution_details" -Method Get -Headers $Headers
        if ($null -eq $Details.jobs -or $Details.jobs.Count -eq 0) {
            $health = "!! ZOMBIE !!"
        } else {
            $job = $Details.jobs[0]
            $instance = if ($job.instance_type) { $job.instance_type } else { "Running..." }
        }
    } catch { $health = "API Delay" }

    [PSCustomObject]@{
        TaskName  = $fullTask.name.PadRight(25).Substring(0,25)
        Status    = $health
        Submitted = $submittedOnLocal  # Shown in EDT for you
        Duration  = $durationStr       # Calculated in UTC for accuracy
        Instance  = $instance
        TaskID    = $fullTask.id
    }
}

# --- STEP 3: Render the report sorted by longest-running tasks first ---
$Report | Sort-Object Duration -Descending | Format-Table -AutoSize