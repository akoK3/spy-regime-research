# Section 5 main run, unattended (A15 rule 5, A16). Runs s5_main_run.py: MainBackend over all 34 folds, one Python process (1 worker), checkpointed.
# Stops after run_all has written the completion record: no freeze, no era calibration. On a crash it resumes from the checkpoints, up to 5 retries.
# Never asks questions. Independent of Claude Code: start it from your own PowerShell window.
#   Run:        powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
#   Preflight:  add -Check (verifies protocol, contamination list, lock, registry, backend; reads no market data, scores nothing)
param(
    [switch]$Check,
    [string]$ProtocolSha256 = "0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9",   # sha256 of the FROZEN SECTION5_PROTOCOL.md (through A16)
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"     # project environment: Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0
$Script = Join-Path $Here "s5_main_run.py"
$Log    = Join-Path $Here "results\main_run_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)

function Write-Log([string]$msg) {
    $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg
    [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8)
    Write-Host $line
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null
if (-not (Test-Path $Python)) { Write-Log "ABORT: Python not found at $Python"; exit 3 }
if (-not (Test-Path $Script)) { Write-Log "ABORT: $Script not found"; exit 3 }
Set-Location $Here
$mode = "main run"
if ($Check) { $mode = "preflight only (-Check)" }
Write-Log ("=== run_main_overnight.ps1 start: {0}; protocol {1}...; max retries {2}" -f $mode, $ProtocolSha256.Substring(0, 16), $MaxRetries)

$attempt = 0
while ($true) {
    $attempt++
    Write-Log ("attempt {0} of {1}: starting Python" -f $attempt, ($MaxRetries + 1))
    $started = Get-Date
    if ($Check) { & $Python $Script $ProtocolSha256 --check } else { & $Python $Script $ProtocolSha256 }
    $code = $LASTEXITCODE
    $mins = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
    Write-Log ("attempt {0}: Python exited with code {1} after {2} min" -f $attempt, $code, $mins)

    if ($code -eq 0) {
        if ($Check) { Write-Log "=== preflight passed; the main run was NOT started"; exit 0 }
        $rec = Join-Path $Here "results\main_run\run_complete.json"
        if (Test-Path $rec) { Write-Log "=== DONE: completion record written ($rec). No freeze, no era calibration."; exit 0 }
        Write-Log "exit code 0 but no completion record: treated as a crash"
    }
    elseif ($code -eq 2) { Write-Log "=== STOPPED by the user (Ctrl+C); not retried. Re-run this script to resume from the checkpoints."; exit 2 }
    elseif ($code -eq 3) { Write-Log "=== REFUSED by a guard (see the log above); not retried."; exit 3 }

    if ($attempt -gt $MaxRetries) { Write-Log ("=== GAVE UP after {0} attempts; finished units are checkpointed. Re-run this script to resume." -f $attempt); exit 1 }
    Write-Log ("crash: resuming from checkpoints in {0} s (retry {1} of {2})" -f $RetryWaitSeconds, $attempt, $MaxRetries)
    Start-Sleep -Seconds $RetryWaitSeconds
}
