# Overnight chain (user instruction 2026-11-10): in order, stopping at the first failure:
#   0. finding-17 data-hash preflight (incl. the finding-14 cache stamp)
#   1. A31 rule 4 synthetic checks (tag a31; must pass: s6_check_synth.py)
#   2. A31 adoption (s6_adopt_a31.py; user pre-approval, only after step 1 passes)
#   3. gate: A28, A29 and A31 ADOPTED with matching sidecars (A29 is a DRAFT awaiting the user; there is no A30 in the repository)
#   4. power check, Gaussian HMM and HSMM in parallel (A29 1f, A31 5d)
#   5. Section 6 development run (TRAIN-span test segments only), Gaussian HMM and HSMM in parallel
# Python output goes to files. No freeze, no O8, no era calibration, no evaluation-period read.
#   Run: powershell -NoProfile -ExecutionPolicy Bypass -File <this file>
param([int]$SynthWorkers = 12, [int]$PowerWorkers = 7, [int]$DevWorkers = 6)
$ErrorActionPreference = "Continue"
$Here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root   = Split-Path -Parent $Here
$S5     = Join-Path $Root "section5"
$Python = Join-Path $Root "research_hmm_env\Scripts\python.exe"
$Res    = Join-Path $Here "results"
$Log    = Join-Path $Res "overnight_log.txt"
$Utf8   = New-Object System.Text.UTF8Encoding($false)
$env:OPENBLAS_NUM_THREADS = "1"; $env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
New-Item -ItemType Directory -Force $Res | Out-Null
function Write-Log([string]$msg) { $line = "{0} [ps1 {1}] {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), $PID, $msg; [System.IO.File]::AppendAllText($Log, $line + [Environment]::NewLine, $Utf8) }
function Start-Py([string]$dir, [string[]]$a, [string]$tag) {
    $p = Start-Process -FilePath $Python -ArgumentList $a -WorkingDirectory $dir -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Res "on_$tag.stdout.txt") -RedirectStandardError (Join-Path $Res "on_$tag.stderr.txt")
    $null = $p.Handle; return $p
}
function Run-Py([string]$dir, [string[]]$a, [string]$tag) { $p = Start-Py $dir $a $tag; $p.WaitForExit(); return $p.ExitCode }
function Stop-Chain([string]$why, [int]$code) { Write-Log "=== CHAIN STOPPED: $why"; [System.IO.File]::WriteAllText((Join-Path $Res "overnight_status.txt"), "STOPPED: $why`n", $Utf8); exit $code }

Write-Log "chain starts"
$t = Get-Date; $code = Run-Py $S5 @((Join-Path $S5 "s5_preflight_data_hashes.py"), "--out", (Join-Path $S5 "results\breaks_preflight\data_hashes_overnight.json")) "data_hashes"
Write-Log ("step 0 data-hash preflight: exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "data-hash preflight failed (exit $code)" 3 }

$t = Get-Date; $code = Run-Py $Here @((Join-Path $Here "s6_synth_validation.py"), "--null-reps", "200", "--effect-reps", "40", "--nboot", "999", "--workers", "$SynthWorkers", "--tag", "a31") "synth_a31"
Write-Log ("step 1 synthetic run: exit {0} after {1} min" -f $code, [math]::Round(((Get-Date) - $t).TotalMinutes, 1)); if ($code -ne 0) { Stop-Chain "synthetic run crashed (exit $code)" 1 }
$code = Run-Py $Here @((Join-Path $Here "s6_check_synth.py"), "a31") "check_a31"
Write-Log ("step 1 acceptance (A31 rule 4b): exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A31 rule 4 synthetic checks FAILED (see results\on_check_a31.stdout.txt); A31 not adopted; power and development run not started" 1 }

$code = Run-Py $Here @((Join-Path $Here "s6_adopt_a31.py"), "a31") "adopt_a31"
Write-Log ("step 2 A31 adoption: exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A31 adoption failed (exit $code)" 1 }

$code = Run-Py $Here @("-c", "import sys; sys.path.insert(0, r'$S5'); import s5_amendment_manifest as AM; bad=[e['amendment'] for e in AM.manifest(('A28','A29','A31')) if not (e['present'] and e['status']=='ADOPTED' and e['sidecar_matches'])]; print('not adopted:', bad); sys.exit(1 if bad else 0)") "gate"
Write-Log ("step 3 gate (A28, A29, A31 adopted): exit {0}" -f $code); if ($code -ne 0) { Stop-Chain "A29 (or A28/A31) is not ADOPTED with a matching sidecar; power and development run wait for the user (no A30 exists)" 2 }

$t = Get-Date; $ps = @{}
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @((Join-Path $Here "s6_power.py"), $det, "--workers", "$PowerWorkers") "power_$det" }
$fail = $false; foreach ($det in $ps.Keys) { $ps[$det].WaitForExit(); Write-Log ("step 4 power {0}: exit {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $fail = $true } }
Write-Log ("step 4 power: {0} min" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1)); if ($fail) { Stop-Chain "power check failed" 1 }

$t = Get-Date; $ps = @{}
foreach ($det in "gaussian_hmm", "hsmm") { $ps[$det] = Start-Py $Here @((Join-Path $Here "s6_run.py"), "development", $det, "--workers", "$DevWorkers") "dev_$det" }
$fail = $false; foreach ($det in $ps.Keys) { $ps[$det].WaitForExit(); Write-Log ("step 5 development run {0}: exit {1}" -f $det, $ps[$det].ExitCode); if ($ps[$det].ExitCode -ne 0) { $fail = $true } }
Write-Log ("step 5 development runs: {0} min" -f [math]::Round(((Get-Date) - $t).TotalMinutes, 1)); if ($fail) { Stop-Chain "development run failed" 1 }
[System.IO.File]::WriteAllText((Join-Path $Res "overnight_status.txt"), "DONE`n", $Utf8); Write-Log "=== CHAIN DONE. No freeze, no O8, no era calibration."
exit 0
