# A35 chain (AMENDMENT_A35 rule 2; user order 2026-11-10), in order, stopping at the first failure:
#   0. finding-17 data-hash preflight
#   1. gate: A28-A35 (with A33.1) ADOPTED with matching sidecars
#   2. warm-up: the development panels are loaded once, so the two runs below read the Section 6 cache instead of writing it at the same time
#   3. rerun of the A28 7d(ii) null control (s6_a35.py null), Gaussian HMM and HSMM in parallel: 200 sets, same seeds, H4 p on valid resamples (A35 rule 1)
#      exit 0 = written and the A29 1d rates reproduce the development run; exit 4 = written but not reproduced (A35 2d: not used)
# Python output goes to files. Memory is logged. No freeze, no O8, no era calibration, no evaluation-period read.
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file> [-Workers 3]
param([int]$Workers = 3)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Here
$S5     = Join-Path $Root "section5"
$Python = Join-Path $Root "research_hmm_env\Scripts\python.exe"
$Res    = Join-Path $Here "results"
$Log    = Join-Path $Res "a35_log.txt"
$Status = Join-Path $Res "a35_status.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
$env:OPENBLAS_NUM_THREADS = "1"; $env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"; $env:PYTHONDONTWRITEBYTECODE = "1"
function Write-Log([string]$msg) { $line = "{0} [a35 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }
function Free-MB { $o = Get-CimInstance Win32_OperatingSystem; "{0} MB free of {1} MB" -f [int]($o.FreePhysicalMemory / 1KB), [int]($o.TotalVisibleMemorySize / 1KB) }
function Start-Py([string]$dir, [string[]]$a, [string]$tag) {
    $p = Start-Process -FilePath $Python -ArgumentList $a -WorkingDirectory $dir -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Res "a35_$tag.stdout.txt") -RedirectStandardError (Join-Path $Res "a35_$tag.stderr.txt")
    $null = $p.Handle; return $p
}
function Run-Py([string]$dir, [string[]]$a, [string]$tag) { $p = Start-Py $dir $a $tag; $p.WaitForExit(); return $p.ExitCode }
function Stop-Chain([string]$why, [int]$code) { Write-Log "=== A35 CHAIN STOPPED: $why"; [System.IO.File]::WriteAllText($Status, "STOPPED: $why`n", $Utf8); exit $code }
$A35 = Join-Path $Here "s6_a35.py"

Write-Log ("chain starts; workers 2 x {0}; {1}" -f $Workers, (Free-MB))
$code = Run-Py $S5 @((Join-Path $S5 "s5_preflight_data_hashes.py"), "--out", (Join-Path $S5 "results\breaks_preflight\data_hashes_a35.json")) "data_hashes"
Write-Log ("step 0 data-hash preflight: exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "data-hash preflight failed (exit $code)" 3 }

$code = Run-Py $Here @("-c", ('"' + "import sys; sys.path.insert(0, r'$Here'); sys.path.insert(0, r'$S5'); import s6_a35 as A, s6_run as R; R.a29_guard(A.AMENDMENTS)" + '"')) "gate"
Write-Log ("step 1 gate (A28-A35, A33.1 adopted): exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A28-A35 not all ADOPTED with matching sidecars" 2 }

$t = Get-Date
$code = Run-Py $Here @("-c", ('"' + "import sys; sys.path.insert(0, r'$Here'); sys.path.insert(0, r'$S5'); import s6_run as R; print({e: len(R.load_era(e, 'development').days) for e in ('LEGACY', 'RAW')})" + '"')) "warmup"
Write-Log ("step 2 warm-up (development panels, Section 6 cache): exit {0} after {1} min; {2}" -f $code, [math]::Round(((Get-Date) - $t).TotalMinutes, 1), (Free-MB)); if ($code -ne 0) { Stop-Chain "warm-up failed (exit $code)" 1 }

$t = Get-Date; $ps = @{}
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @($A35, "null", $det, "--workers", "$Workers") "null_$det" }
Write-Log ("step 3 null-control rerun started: PIDs {0}" -f (($ps.Values | ForEach-Object { $_.Id }) -join ", "))
$n = 0
while (($ps.Values | Where-Object { -not $_.HasExited }).Count -gt 0) { Start-Sleep -Seconds 60; $n++; if ($n % 15 -eq 0) { Write-Log ("step 3 after {0} min: {1}" -f $n, (Free-MB)) } }
$bad = @()
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det].WaitForExit(); Write-Log ("step 3 null-control rerun {0}: exit {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $bad += "$det exit $($ps[$det].ExitCode)" } }
Write-Log ("step 3: {0} min; {1}" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1), (Free-MB))
if ($bad.Count -gt 0) { Stop-Chain ("null-control rerun: " + ($bad -join "; ") + " (exit 4 = A29 1d rates not reproduced, A35 2d)") 1 }
[System.IO.File]::WriteAllText($Status, "DONE`n", $Utf8); Write-Log "=== A35 CHAIN DONE. No freeze, no O8, no era calibration."
exit 0
