# H2 chain (AMENDMENT_A33: protocol 5.0 primary; user instruction 2026-11-10), in order, stopping at the first failure:
#   0. finding-17 data-hash preflight
#   1. A33 rule 3 synthetic check (s6_h2.py synth, then check: must pass)
#   2. gate: A28-A33 ADOPTED with matching sidecars
#   3. A33 G11 power, Gaussian HMM and HSMM (reported, not a gate unless it crashes)
#   4. H2 development run (TRAIN-span test segments only), Gaussian HMM and HSMM in parallel
# Python output goes to files. Memory is logged at each step. No freeze, no O8, no era calibration, no evaluation-period read.
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file> [-Tag a33] [-SynthWorkers 6] [-PowerWorkers 3]
param([string]$Tag = "a33p08", [int]$SynthWorkers = 6, [int]$PowerWorkers = 3)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Here
$S5     = Join-Path $Root "section5"
$Python = Join-Path $Root "research_hmm_env\Scripts\python.exe"
$Res    = Join-Path $Here "results"
$Log    = Join-Path $Res "h2_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
$env:OPENBLAS_NUM_THREADS = "1"; $env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
function Write-Log([string]$msg) { $line = "{0} [h2 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }
function Free-MB { $o = Get-CimInstance Win32_OperatingSystem; "{0} MB free of {1} MB" -f [int]($o.FreePhysicalMemory / 1KB), [int]($o.TotalVisibleMemorySize / 1KB) }
function Start-Py([string]$dir, [string[]]$a, [string]$tag) {
    $p = Start-Process -FilePath $Python -ArgumentList $a -WorkingDirectory $dir -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Res "h2_$tag.stdout.txt") -RedirectStandardError (Join-Path $Res "h2_$tag.stderr.txt")
    $null = $p.Handle; return $p
}
function Run-Py([string]$dir, [string[]]$a, [string]$tag) { $p = Start-Py $dir $a $tag; $p.WaitForExit(); return $p.ExitCode }
function Stop-Chain([string]$why, [int]$code) { Write-Log "=== H2 CHAIN STOPPED: $why"; [System.IO.File]::WriteAllText((Join-Path $Res "h2_status.txt"), "STOPPED: $why`n", $Utf8); exit $code }
$H2 = Join-Path $Here "s6_h2.py"

Write-Log ("chain starts; {0}" -f (Free-MB))
$code = Run-Py $S5 @((Join-Path $S5 "s5_preflight_data_hashes.py"), "--out", (Join-Path $S5 "results\breaks_preflight\data_hashes_h2.json")) "data_hashes"
Write-Log ("step 0 data-hash preflight: exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "data-hash preflight failed (exit $code)" 3 }

$t = Get-Date; $code = Run-Py $Here @($H2, "synth", "--tag", $Tag, "--null-reps", "200", "--effect-reps", "40", "--draws", "10000", "--workers", "$SynthWorkers") "synth_$Tag"
Write-Log ("step 1 synthetic run: exit {0} after {1} min; {2}" -f $code, [math]::Round(((Get-Date) - $t).TotalMinutes, 1), (Free-MB)); if ($code -ne 0) { Stop-Chain "synthetic run crashed (exit $code)" 1 }
$code = Run-Py $Here @($H2, "check", $Tag) "check_$Tag"
Write-Log ("step 1 acceptance (A33 rule 3): exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A33 rule 3 synthetic check FAILED (see results\h2_check_$Tag.stdout.txt); power and development run not started" 1 }

$code = Run-Py $Here @("-c", ('"' + "import sys; sys.path.insert(0, r'$S5'); import s5_amendment_manifest as AM; bad=[e['amendment'] for e in AM.manifest(('A28','A29','A30','A31','A32','A33','A33_1')) if not (e['present'] and e['status']=='ADOPTED' and e['sidecar_matches'])]; print('not adopted:', bad); sys.exit(1 if bad else 0)" + '"')) "gate"
Write-Log ("step 2 gate (A28-A33, A33.1 adopted): exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A28-A33 not all ADOPTED with matching sidecars" 2 }

$t = Get-Date; $ps = @{}
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @($H2, "power", $det, "--workers", "$PowerWorkers") "power_$det" }
$fail = $false; foreach ($det in $ps.Keys) { $ps[$det].WaitForExit(); Write-Log ("step 3 power {0}: exit {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $fail = $true } }
Write-Log ("step 3 power: {0} min; {1}" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1), (Free-MB)); if ($fail) { Stop-Chain "power crashed" 1 }

$t = Get-Date; $ps = @{}; Write-Log ("step 4 H2 development run starts; memory {0}" -f (Free-MB))
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @($H2, "development", $det) "dev_$det" }
$fail = $false; foreach ($det in $ps.Keys) { $ps[$det].WaitForExit(); Write-Log ("step 4 H2 development run {0}: exit {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $fail = $true } }
Write-Log ("step 4: {0} min; {1}" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1), (Free-MB)); if ($fail) { Stop-Chain "H2 development run failed" 1 }
[System.IO.File]::WriteAllText((Join-Path $Res "h2_status.txt"), "DONE`n", $Utf8); Write-Log "=== H2 CHAIN DONE. No freeze, no O8, no era calibration."
exit 0
