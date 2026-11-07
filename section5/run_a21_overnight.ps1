# A21, unattended: D7 rerun on the MR2 fits with the A21 rule-1 exclusion (results\mr2\d7_a21) -> Step 2 for liquidity (results\step2_liquidity). One Python process at a time,
# checkpointed; a crash resumes from the checkpoints, up to 5 retries per phase. A phase starts only after the previous one finished (exit 0 and its output file exists).
# Guard refusal (3) and Ctrl+C (2) stop everything. No 5.12 freeze, no era calibration. Never asks questions. Log: results\a21_log.txt.
#   Run:        powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
#   Preflight:  add -Check (unit tests + preflight on the contaminated RAW 3 and LEGACY 29 folds; writes only results\step2_preflight)
param(
    [switch]$Check,
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",   # sha256 of the FROZEN SECTION5_PROTOCOL.md (through A20; A21 not integrated)
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"
$Log    = Join-Path $Here "results\a21_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)

function Write-Log([string]$msg) {
    $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg
    [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8)
    Write-Host $line
}

function Run-Phase([string]$name, [string[]]$pyArgs, [string]$doneFile) {
    $attempt = 0
    while ($true) {
        $attempt++
        Write-Log ("{0} attempt {1} of {2}: starting Python" -f $name, $attempt, ($MaxRetries + 1))
        $started = Get-Date
        & $Python @pyArgs | Out-Host
        $code = $LASTEXITCODE
        Write-Log ("{0} attempt {1}: Python exited with code {2} after {3} min" -f $name, $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
        if ($code -eq 0) {
            if ($doneFile -eq "") { return 0 }
            if (Test-Path (Join-Path $Here $doneFile)) { Write-Log "$name DONE ($doneFile written)"; return 0 }
            Write-Log "$name exit code 0 but $doneFile missing: treated as a crash"
        }
        elseif ($code -eq 2) { Write-Log "=== $name STOPPED by the user (Ctrl+C); re-run this script to resume"; return 2 }
        elseif ($code -eq 3) { Write-Log "=== $name REFUSED by a guard or failed preflight (see the log); not retried"; return 3 }
        if ($Check) { Write-Log "=== $name preflight crashed (code $code); not retried"; return $code }
        if ($attempt -gt $MaxRetries) { Write-Log ("=== {0} GAVE UP after {1} attempts; finished units are checkpointed; re-run this script to resume" -f $name, $attempt); return 1 }
        Write-Log ("{0} crash: resuming from checkpoints in {1} s (retry {2} of {3})" -f $name, $RetryWaitSeconds, $attempt, $MaxRetries)
        Start-Sleep -Seconds $RetryWaitSeconds
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null
if (-not (Test-Path $Python)) { Write-Log "ABORT: Python not found at $Python"; exit 3 }
Set-Location $Here
$mode = "D7 (A21) -> Step 2 liquidity"
if ($Check) { $mode = "preflight only (-Check)" }
Write-Log ("=== run_a21_overnight.ps1 start: {0}; protocol {1}...; max retries {2} per phase" -f $mode, $ProtocolSha256.Substring(0, 16), $MaxRetries)

if ($Check) {
    $r = Run-Phase "A21 preflight" @((Join-Path $Here "s5_step2.py"), $ProtocolSha256, "--check") ""
    if ($r -ne 0) { Write-Log "=== preflight FAILED (code $r)"; exit $r }
    Write-Log "=== preflight passed; nothing was started"; exit 0
}
$r = Run-Phase "D7 (A21)" @((Join-Path $Here "s5_mr2.py"), $ProtocolSha256, "d7a21") "results\mr2\d7_a21\d7_results.json"
if ($r -ne 0) { Write-Log "=== stopped in D7 (A21) (code $r); Step 2 not started"; exit $r }
$r = Run-Phase "Step 2 liquidity" @((Join-Path $Here "s5_step2.py"), $ProtocolSha256) "results\step2_liquidity\step2_results.json"
if ($r -ne 0) { Write-Log "=== stopped in Step 2 (code $r)"; exit $r }
Write-Log "=== D7 (A21) and Step 2 liquidity DONE. No 5.12 freeze, no era calibration."
exit 0
