# A27 (AMENDMENT_A27.md): confirmation-count sensitivity r = 1, 2, 3, 4 on the 26 confirmatory development folds. Unattended, checkpointed; up to 5 retries.
# Order: (1) audit-1 finding 17 data-hash preflight (s5_preflight_data_hashes.py; any mismatch stops); (2) A27 preflight on RAW 3 / LEGACY 29 (unit tests, r = 3 reproduction, timing),
# skipped if results\a27_preflight\a27_preflight.json exists; (3) the run. Guard refusal (3), Ctrl+C (2) and a reproduction mismatch (4) stop. No freeze, no era calibration.
# Log: results\a27_log.txt (Python lines) and results\a27_runner_log.txt (this script). Python output goes to results\a27_runner_stdout.txt (never to a pipe owned by this script).
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
param(
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"
$Log    = Join-Path $Here "results\a27_runner_log.txt"
$Out    = Join-Path $Here "results\a27_runner_stdout.txt"
$Done   = Join-Path $Here "results\a27\confirm_count.json"
$Pre    = Join-Path $Here "results\a27_preflight\a27_preflight.json"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
function Write-Log([string]$msg) { $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }
function Run-Py([string[]]$a) { $p = Start-Process -FilePath $Python -ArgumentList $a -WorkingDirectory $Here -NoNewWindow -Wait -PassThru -RedirectStandardOutput $Out -RedirectStandardError ($Out + ".err"); return $p.ExitCode }

Set-Location $Here
$code = Run-Py @((Join-Path $Here "s5_preflight_data_hashes.py"), "--out", (Join-Path $Here "results\a27_preflight\data_hashes.json"))
Write-Log ("finding-17 data-hash preflight: exit code {0}" -f $code)
if ($code -ne 0) { Write-Log "=== A27 stopped: data hashes differ or a record is missing (see results\a27_preflight\data_hashes.json)"; exit 3 }
if (-not (Test-Path $Pre)) {
    $code = Run-Py @((Join-Path $Here "s5_a27_confirm.py"), $ProtocolSha256, "--check")
    Write-Log ("A27 preflight: exit code {0}" -f $code)
    if ($code -ne 0) { Write-Log "=== A27 stopped: preflight failed (code $code; see results\a27_log.txt)"; exit $code }
}
$attempt = 0
while ($true) {
    $attempt++; $started = Get-Date
    Write-Log ("A27 attempt {0} of {1}" -f $attempt, ($MaxRetries + 1))
    $code = Run-Py @((Join-Path $Here "s5_a27_confirm.py"), $ProtocolSha256)
    Write-Log ("A27 attempt {0}: exit code {1} after {2} min" -f $attempt, $code, [math]::Round(((Get-Date) - $started).TotalMinutes, 1))
    if ($code -eq 0 -and (Test-Path $Done) -and ((Get-Item $Done).LastWriteTime -ge $started)) { Write-Log "=== A27 DONE (results\a27\confirm_count.json written). No freeze, no era calibration."; exit 0 }
    if ($code -in 2, 3, 4) { Write-Log "=== A27 stopped (code $code; see results\a27_log.txt)"; exit $code }
    if ($attempt -gt $MaxRetries) { Write-Log "=== A27 GAVE UP after $attempt attempts; finished folds are checkpointed"; exit 1 }
    Start-Sleep -Seconds $RetryWaitSeconds
}
