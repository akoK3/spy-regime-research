# Logs memory every 5 min while A23 or A25 python processes run: free RAM, free commit, and each job's working set / peak / private bytes. Read-only; exits when both have stopped.
$Log = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "results\mem_watch_log.txt"
while ($true) {
    $os = Get-CimInstance Win32_OperatingSystem
    $jobs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match 's5_a23|s5_a25' }
    $parts = foreach ($j in $jobs) { $p = Get-Process -Id $j.ProcessId -ErrorAction SilentlyContinue; if ($p -and $p.WorkingSet64 -gt 100MB) { "{0} WS {1:N2} peak {2:N2} priv {3:N2} GB" -f ($(if ($j.CommandLine -match 's5_a23') { 'A23' } else { 'A25' })), ($p.WorkingSet64/1GB), ($p.PeakWorkingSet64/1GB), ($p.PrivateMemorySize64/1GB) } }
    $line = "{0} RAM free {1:N1} GB, commit free {2:N1} of {3:N1} GB; {4}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"), ($os.FreePhysicalMemory/1MB), ($os.FreeVirtualMemory/1MB), ($os.TotalVirtualMemorySize/1MB), ($parts -join "; ")
    Add-Content -Path $Log -Value $line -Encoding UTF8
    if (-not $jobs) { break }
    Start-Sleep -Seconds 300
}
