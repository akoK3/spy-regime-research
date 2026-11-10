# Queue (user instruction 2026-11-09): after the A25 post-hoc absolute-pAUC run ends, (1) finding-17 data-hash preflight, (2) SPY break export (--check on RAW 3 / LEGACY 29,
# then the 26 confirmatory folds), (3) A28 rule 6d power check for gaussian_hmm and hsmm in parallel. Each step stops the queue on a nonzero exit.
# Python output goes to files, never to a pipe owned by this script. No freeze, no O8, no era calibration, no asset outcome read.
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file> -WaitPid <A25 post-hoc python PID>
param(
    [int]$WaitPid = 0,
    [string]$ProtocolSha256 = "15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3"
)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Here
$S5     = Join-Path $Root "section5"
$Python = Join-Path $Root "research_hmm_env\Scripts\python.exe"
$Res    = Join-Path $Here "results"
$Log    = Join-Path $Res "queue_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
New-Item -ItemType Directory -Force $Res | Out-Null
function Write-Log([string]$msg) { $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }
function Start-Py([string]$dir, [string[]]$a, [string]$tag) {
    $p = Start-Process -FilePath $Python -ArgumentList $a -WorkingDirectory $dir -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Res "$tag.stdout.txt") -RedirectStandardError (Join-Path $Res "$tag.stderr.txt")
    $null = $p.Handle      # cache the handle so ExitCode is available after WaitForExit
    return $p
}
function Run-Py([string]$dir, [string[]]$a, [string]$tag) { $p = Start-Py $dir $a $tag; $p.WaitForExit(); return $p.ExitCode }

if ($WaitPid -gt 0) {
    Write-Log "waiting for the A25 post-hoc run (PID $WaitPid)"
    while (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 30 }
}
if (-not (Test-Path (Join-Path $S5 "results\a25\abs_pauc.json"))) { Write-Log "=== queue stopped: the A25 post-hoc run ended without results\a25\abs_pauc.json"; exit 3 }
Write-Log "A25 post-hoc finished; queue starts"

$code = Run-Py $S5 @((Join-Path $S5 "s5_preflight_data_hashes.py"), "--out", (Join-Path $S5 "results\breaks_preflight\data_hashes.json")) "q_data_hashes"
Write-Log ("finding-17 data-hash preflight: exit code {0}" -f $code)
if ($code -ne 0) { Write-Log "=== queue stopped: data hashes"; exit 3 }

$t = Get-Date
$code = Run-Py $S5 @((Join-Path $S5 "s5_break_export.py"), $ProtocolSha256, "--check") "q_breaks_check"
Write-Log ("break export preflight (RAW 3 / LEGACY 29): exit code {0} after {1} min" -f $code, [math]::Round(((Get-Date) - $t).TotalMinutes, 1))
if ($code -ne 0) { Write-Log "=== queue stopped: break export preflight (see section5\results\breaks_log.txt)"; exit $code }

$t = Get-Date
$code = Run-Py $S5 @((Join-Path $S5 "s5_break_export.py"), $ProtocolSha256) "q_breaks"
Write-Log ("break export: exit code {0} after {1} min" -f $code, [math]::Round(((Get-Date) - $t).TotalMinutes, 1))
if ($code -ne 0 -or -not (Test-Path (Join-Path $S5 "results\breaks\breaks.csv"))) { Write-Log "=== queue stopped: break export"; exit 4 }

$t = Get-Date
$ps = @{}
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @((Join-Path $Here "s6_power.py"), $det) "q_power_$det" }
$fail = $false
foreach ($det in $ps.Keys) { $ps[$det].WaitForExit(); Write-Log ("power {0}: exit code {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $fail = $true } }
Write-Log ("power done after {0} min" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1))
if ($fail) { Write-Log "=== queue stopped: power"; exit 1 }
Write-Log "=== queue DONE. No freeze, no O8, no era calibration."
exit 0
