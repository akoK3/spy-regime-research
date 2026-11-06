# MR2 under A20, unattended: main run (34 folds) -> A17-style phase on its fits -> D7 per A19.3 (AMENDMENT_A20.md rule 4). One Python process at a time, checkpointed;
# a crash resumes from the checkpoints, up to 5 retries per phase. A phase starts only after the previous one finished (exit 0 and its output file exists).
# Guard refusal (3), Ctrl+C (2) and an A17-style reproduction mismatch (4) stop everything. No 5.12 freeze, no era calibration. Never asks questions.
# Independent of Claude Code: start it from your own PowerShell window.
#   Run:        powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
#   Preflight:  add -Check (guards + full preflight on the contaminated RAW 3 and LEGACY 29 folds, incl. D7's positive control; writes only results\mr2_preflight)
param(
    [switch]$Check,
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",   # sha256 of the FROZEN SECTION5_PROTOCOL.md (integrated through A20)
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"     # project environment: Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.0
$Log    = Join-Path $Here "results\mr2_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)

function Write-Log([string]$msg) {
    $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg
    [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8)
    Write-Host $line
}

function Run-Phase([string]$name, [string]$stage, [string]$doneFile) {
    $attempt = 0
    while ($true) {
        $attempt++
        Write-Log ("{0} attempt {1} of {2}: starting Python" -f $name, $attempt, ($MaxRetries + 1))
        $started = Get-Date
        if ($Check) { & $Python (Join-Path $Here "s5_mr2.py") $ProtocolSha256 $stage --check | Out-Host } else { & $Python (Join-Path $Here "s5_mr2.py") $ProtocolSha256 $stage | Out-Host }   # Out-Host: keep Python output out of the return value
        $code = $LASTEXITCODE
        Write-Log ("{0} attempt {1}: Python exited with code {2} after {3} min" -f $name, $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
        if ($code -eq 0) {
            if ($Check) { return 0 }
            if (Test-Path (Join-Path $Here $doneFile)) { Write-Log "$name DONE ($doneFile written)"; return 0 }
            Write-Log "$name exit code 0 but $doneFile missing: treated as a crash"
        }
        elseif ($code -eq 2) { Write-Log "=== $name STOPPED by the user (Ctrl+C); re-run this script to resume"; return 2 }
        elseif ($code -eq 3) { Write-Log "=== $name REFUSED by a guard (see the log); not retried"; return 3 }
        elseif ($code -eq 4) { Write-Log "=== $name reproduction MISMATCH (see the log); everything stops"; return 4 }
        if ($attempt -gt $MaxRetries) { Write-Log ("=== {0} GAVE UP after {1} attempts; finished units are checkpointed; re-run this script to resume" -f $name, $attempt); return 1 }
        Write-Log ("{0} crash: resuming from checkpoints in {1} s (retry {2} of {3})" -f $name, $RetryWaitSeconds, $attempt, $MaxRetries)
        Start-Sleep -Seconds $RetryWaitSeconds
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null
if (-not (Test-Path $Python)) { Write-Log "ABORT: Python not found at $Python"; exit 3 }
Set-Location $Here
$mode = "MR2 -> A17-style -> D7"
if ($Check) { $mode = "preflight only (-Check)" }
Write-Log ("=== run_mr2_overnight.ps1 start: {0}; protocol {1}...; max retries {2} per phase" -f $mode, $ProtocolSha256.Substring(0, 16), $MaxRetries)

if ($Check) {
    $r = Run-Phase "MR2 preflight" "mr2" ""
    if ($r -ne 0) { Write-Log "=== preflight FAILED (code $r)"; exit $r }
    Write-Log "=== preflight passed; nothing was started"; exit 0
}
$r = Run-Phase "MR2" "mr2" "results\main_run_2\run_complete.json"
if ($r -ne 0) { Write-Log "=== stopped in MR2 (code $r); A17-style phase and D7 not started"; exit $r }
$r = Run-Phase "A17-style" "a17" "results\mr2\a17\a17_results.json"
if ($r -ne 0) { Write-Log "=== stopped in the A17-style phase (code $r); D7 not started"; exit $r }
$r = Run-Phase "D7" "d7" "results\mr2\d7\d7_results.json"
if ($r -ne 0) { Write-Log "=== stopped in D7 (code $r)"; exit $r }
Write-Log "=== MR2, A17-style phase and D7 DONE. No 5.12 freeze, no era calibration."
exit 0
