# A17 then A18, unattended (AMENDMENT_A17.md, AMENDMENT_A18.md). One Python process at a time (1 worker), checkpointed; a crash resumes from the checkpoints, up to 5 retries per phase.
# A17 must finish (exit 0) before A18 starts. A reproduction mismatch in A17 (exit 4) stops everything. No freeze, no era calibration. Never asks questions.
# Independent of Claude Code: start it from your own PowerShell window.
#   Run:        powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
#   Preflight:  add -Check (guards + smoke tests on the contaminated RAW 3 fold only; writes no A17/A18 results)
param(
    [switch]$Check,
    [string]$ProtocolSha256 = "0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9",   # sha256 of the FROZEN SECTION5_PROTOCOL.md (through A16; A17/A18 are not integrated)
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"     # project environment: Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0
$Log    = Join-Path $Here "results\a17_a18_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)

function Write-Log([string]$msg) {
    $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg
    [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8)
    Write-Host $line
}

function Run-Phase([string]$name, [string]$script, [string]$doneFile) {
    $attempt = 0
    while ($true) {
        $attempt++
        Write-Log ("{0} attempt {1} of {2}: starting Python" -f $name, $attempt, ($MaxRetries + 1))
        $started = Get-Date
        if ($Check) { & $Python (Join-Path $Here $script) $ProtocolSha256 --check | Out-Host } else { & $Python (Join-Path $Here $script) $ProtocolSha256 | Out-Host }   # Out-Host: Python output must not become the function's return value
        $code = $LASTEXITCODE
        Write-Log ("{0} attempt {1}: Python exited with code {2} after {3} min" -f $name, $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
        if ($code -eq 0) {
            if ($Check) { return 0 }
            if (Test-Path (Join-Path $Here $doneFile)) { Write-Log "$name DONE ($doneFile written)"; return 0 }
            Write-Log "$name exit code 0 but $doneFile missing: treated as a crash"
        }
        elseif ($code -eq 2) { Write-Log "=== $name STOPPED by the user (Ctrl+C); re-run this script to resume"; return 2 }
        elseif ($code -eq 3) { Write-Log "=== $name REFUSED by a guard (see the log); not retried"; return 3 }
        elseif ($code -eq 4) { Write-Log "=== $name reproduction MISMATCH (results\a17\MISMATCH.json); everything stops"; return 4 }
        if ($attempt -gt $MaxRetries) { Write-Log ("=== {0} GAVE UP after {1} attempts; finished units are checkpointed; re-run this script to resume" -f $name, $attempt); return 1 }
        Write-Log ("{0} crash: resuming from checkpoints in {1} s (retry {2} of {3})" -f $name, $RetryWaitSeconds, $attempt, $MaxRetries)
        Start-Sleep -Seconds $RetryWaitSeconds
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null
if (-not (Test-Path $Python)) { Write-Log "ABORT: Python not found at $Python"; exit 3 }
Set-Location $Here
$mode = "A17 then A18"
if ($Check) { $mode = "preflight only (-Check)" }
Write-Log ("=== run_a17_a18_overnight.ps1 start: {0}; protocol {1}...; max retries {2} per phase" -f $mode, $ProtocolSha256.Substring(0, 16), $MaxRetries)

$r = Run-Phase "A17" "s5_a17.py" "results\a17\a17_results.json"
if ($r -ne 0) { Write-Log "=== stopped after A17 (code $r); A18 not started"; exit $r }
$r = Run-Phase "A18" "s5_a18.py" "results\a18\a18_results.json"
if ($r -ne 0) { Write-Log "=== stopped in A18 (code $r)"; exit $r }
if ($Check) { Write-Log "=== preflight passed for A17 and A18; nothing was started" } else { Write-Log "=== A17 and A18 DONE. No freeze, no era calibration." }
exit 0
