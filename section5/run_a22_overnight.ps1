# A22, unattended, priority order (AMENDMENT_A22.md rule 5a): power -> D8c -> era/flagged -> thresholds 0.15/0.25 -> LEGACY delay -> A18 rerun (A20 inputs) -> seeds 1-3 -> RAW pool 69
# -> grids 5 (reference) and 15 min -> 1-min grid (no HSMM) -> 1-min HSMM (only if the preflight projection is <= 24 h). One Python process at a time, checkpointed; a crash resumes from the
# checkpoints, up to 5 retries per phase. A phase starts only after the previous one finished (exit 0 and its output file exists).
# Guard refusal (3), Ctrl+C (2) and a reproduction mismatch (4) stop everything. No 5.12 freeze, no era calibration. Never asks questions. Log: results\a22_log.txt.
#   Run:        powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
#   Preflight:  add -Check (unit tests + preflight on the contaminated RAW 3 and LEGACY 29 folds; writes only results\a22_preflight)
#   Start later: add -From <phase> (earlier phases must already be done; their output files are checked)
param(
    [switch]$Check,
    [string]$From = "power",
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3",   # sha256 of the FROZEN SECTION5_PROTOCOL.md (through A20; A21, A22 not integrated)
    [int]$MaxRetries = 5,
    [int]$RetryWaitSeconds = 60
)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path (Split-Path -Parent $Here) "research_hmm_env\Scripts\python.exe"
$Log    = Join-Path $Here "results\a22_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
$Phases = @(
    @("power",      "results\a22\power.json"),
    @("d8c",        "results\d8\d8c_results.json"),
    @("era_flagged","results\a22\era_flagged.json"),
    @("thresholds", "results\a22\thresholds.json"),
    @("delay",      "results\a22\delay.json"),
    @("a18",        "results\mr2\a18\a18_results.json"),
    @("seeds",      "results\a22\seeds.json"),
    @("raw80",      "results\a22\raw80.json"),
    @("grids",      "results\a22\grids.json"),
    @("grid1",      "results\a22\grids.json"),
    @("grid1_hsmm", "results\a22\grid1_hsmm.json")
)

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
            if ((Test-Path (Join-Path $Here $doneFile)) -and ((Get-Item (Join-Path $Here $doneFile)).LastWriteTime -ge $started)) { Write-Log "$name DONE ($doneFile written)"; return 0 }
            Write-Log "$name exit code 0 but $doneFile not written by this attempt: treated as a crash"
        }
        elseif ($code -eq 2) { Write-Log "=== $name STOPPED by the user (Ctrl+C); re-run this script with -From $name to resume"; return 2 }
        elseif ($code -eq 3) { Write-Log "=== $name REFUSED by a guard or failed preflight (see the log); not retried"; return 3 }
        elseif ($code -eq 4) { Write-Log "=== $name reproduction MISMATCH (see the log); everything stops"; return 4 }
        if ($Check) { Write-Log "=== $name preflight crashed (code $code); not retried"; return $code }
        if ($attempt -gt $MaxRetries) { Write-Log ("=== {0} GAVE UP after {1} attempts; finished units are checkpointed; re-run with -From {0}" -f $name, $attempt); return 1 }
        Write-Log ("{0} crash: resuming from checkpoints in {1} s (retry {2} of {3})" -f $name, $RetryWaitSeconds, $attempt, $MaxRetries)
        Start-Sleep -Seconds $RetryWaitSeconds
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null
if (-not (Test-Path $Python)) { Write-Log "ABORT: Python not found at $Python"; exit 3 }
Set-Location $Here
$Script = Join-Path $Here "s5_a22.py"
if ($Check) {
    Write-Log ("=== run_a22_overnight.ps1 start: preflight only (-Check); protocol {0}..." -f $ProtocolSha256.Substring(0, 16))
    $r = Run-Phase "A22 preflight" @($Script, $ProtocolSha256, "all", "--check") ""
    if ($r -ne 0) { Write-Log "=== preflight FAILED (code $r)"; exit $r }
    Write-Log "=== preflight passed; nothing was started"; exit 0
}
$names = $Phases | ForEach-Object { $_[0] }
$start = [array]::IndexOf($names, $From)
if ($start -lt 0) { Write-Log "ABORT: unknown phase $From"; exit 3 }
for ($i = 0; $i -lt $start; $i++) { if (-not (Test-Path (Join-Path $Here $Phases[$i][1]))) { Write-Log ("ABORT: -From {0} but {1} has no output ({2})" -f $From, $Phases[$i][0], $Phases[$i][1]); exit 3 } }
Write-Log ("=== run_a22_overnight.ps1 start: phases {0}; protocol {1}...; max retries {2} per phase" -f (($names[$start..($names.Length - 1)]) -join " -> "), $ProtocolSha256.Substring(0, 16), $MaxRetries)
for ($i = $start; $i -lt $Phases.Count; $i++) {
    $p = $Phases[$i]
    $r = Run-Phase ("A22 " + $p[0]) @($Script, $ProtocolSha256, $p[0]) $p[1]
    if ($r -ne 0) { Write-Log ("=== stopped in {0} (code {1}); later phases not started" -f $p[0], $r); exit $r }
}
Write-Log "=== A22 DONE (all phases). No 5.12 freeze, no era calibration."
exit 0
