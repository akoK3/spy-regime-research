# A25 (AMENDMENT_A25.md), O9 M1 fix: LEGACY delay scored by the data time used. Unattended, checkpointed: a crash resumes from the per-fold checkpoints, up to 5 retries.
# Guard refusal (3), Ctrl+C (2) and a reproduction mismatch (4) stop. No freeze, no era calibration. Log: results\a25_log.txt (Python lines) and results\a25_runner_log.txt (this script).
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
param(
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"
$Log    = Join-Path $Here "results\a25_runner_log.txt"
$Done   = Join-Path $Here "results\a25\delay_datatime.json"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
function Write-Log([string]$msg) { $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }

Set-Location $Here
$attempt = 0
while ($true) {
    $attempt++; $started = Get-Date
    Write-Log ("A25 attempt {0} of {1}" -f $attempt, ($MaxRetries + 1))
    & $Python (Join-Path $Here "s5_a25_delay.py") $ProtocolSha256 | Out-Host
    $code = $LASTEXITCODE
    Write-Log ("A25 attempt {0}: exit code {1} after {2} min" -f $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
    if ($code -eq 0 -and (Test-Path $Done) -and ((Get-Item $Done).LastWriteTime -ge $started)) { Write-Log "=== A25 DONE (results\a25\delay_datatime.json written). No freeze, no era calibration."; exit 0 }
    if ($code -in 2, 3, 4) { Write-Log "=== A25 stopped (code $code; see results\a25_log.txt)"; exit $code }
    if ($attempt -gt $MaxRetries) { Write-Log "=== A25 GAVE UP after $attempt attempts; finished folds are checkpointed"; exit 1 }
    Start-Sleep -Seconds $RetryWaitSeconds
}
