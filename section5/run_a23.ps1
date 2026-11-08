# A23 (AMENDMENT_A23.md), EXPLORATORY combined volatility + volume model: unattended, checkpointed. Waits until the post-hoc grid pAUC run (close-out item 2) has stopped, so the two
# never run at the same time (user instruction: A23 overnight after item 2). A crash resumes from the checkpoints, up to 5 retries. Guard refusal (3), Ctrl+C (2) and a reproduction
# mismatch (4) stop. No freeze, no era calibration. Log: results\a23_log.txt (Python lines) and results\a23_runner_log.txt (this script).
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
param(
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60,
    [switch]$NoWait
)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"
$Log    = Join-Path $Here "results\a23_runner_log.txt"
$Done   = Join-Path $Here "results\a23\a23_results.json"
$PostHocOut = Join-Path $Here "results\posthoc_grid_pauc_stdout.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
function Write-Log([string]$msg) { $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8); Write-Host $line }

Set-Location $Here
if (-not $NoWait) {
    Write-Log "waiting for the post-hoc grid pAUC run to stop (its stdout file gets a final 'rc=' line from the retry loop)"
    while ($true) {
        $alive = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like "*s5_posthoc_grid_pauc.py*" }
        $txt = if (Test-Path $PostHocOut) { Get-Content $PostHocOut -Raw } else { "" }
        $finished = ($txt -match "(?m)^rc=[0234]\s*$") -or ([regex]::Matches($txt, "(?m)^rc=").Count -ge 4)
        if (-not $alive -and $finished) { break }
        Start-Sleep -Seconds 120
    }
    Write-Log "post-hoc grid pAUC run has stopped; starting A23"
}
$attempt = 0
while ($true) {
    $attempt++; $started = Get-Date
    Write-Log ("A23 attempt {0} of {1}" -f $attempt, ($MaxRetries + 1))
    & $Python (Join-Path $Here "s5_a23.py") $ProtocolSha256 | Out-Host
    $code = $LASTEXITCODE
    Write-Log ("A23 attempt {0}: exit code {1} after {2} min" -f $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
    if ($code -eq 0 -and (Test-Path $Done) -and ((Get-Item $Done).LastWriteTime -ge $started)) { Write-Log "=== A23 DONE (results\a23\a23_results.json written). No freeze, no era calibration."; exit 0 }
    if ($code -in 2, 3, 4) { Write-Log "=== A23 stopped (code $code; see results\a23_log.txt)"; exit $code }
    if ($attempt -gt $MaxRetries) { Write-Log "=== A23 GAVE UP after $attempt attempts; finished units are checkpointed"; exit 1 }
    Start-Sleep -Seconds $RetryWaitSeconds
}
