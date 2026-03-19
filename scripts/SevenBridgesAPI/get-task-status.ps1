# --- CONFIGURATION ---
$Token = (Get-Content "$PSScriptRoot\token.txt").Trim()
$ProjectID = "rmathur2/dmc-task-4-controlled"
$BaseUrl = "https://api.sb.biodatacatalyst.nhlbi.nih.gov/v2"
$Headers = @{ "X-SBG-Auth-Token" = $Token; "Content-Type" = "application/json" }

Write-Host "`n--- PROJECT TELEMETRY (UTC CORRECTED): $ProjectID ---" -ForegroundColor Cyan

# 1. Fetch Running Tasks
$TasksUrl = "$BaseUrl/tasks?project=$ProjectID&status=RUNNING&limit=100"
$RunningTasks = Invoke-RestMethod -Uri $TasksUrl -Method Get -Headers $Headers

# CRITICAL FIX: Get current time and immediately convert to UTC for the math
$NowUTC = (Get-Date).ToUniversalTime()

if ($null -eq $RunningTasks.items -or $RunningTasks.items.Count -eq 0) {
    Write-Host "No active tasks found." -ForegroundColor Green
    return
}

$Report = foreach ($t in $RunningTasks.items) {
    # Deep Inspect to get the full metadata
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

    # --- INFRASTRUCTURE STATUS ---
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

# 3. Render
$Report | Sort-Object Duration -Descending | Format-Table -AutoSize