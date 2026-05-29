<#
.SYNOPSIS
    EnergoSmart control panel / monitor (PowerShell).

.DESCRIPTION
    Central hub for the local pipeline:
      * Logs every .bat run (start / end / exit code / duration) to
        logs/run_history.jsonl. Each wrapper .bat calls -Begin at start and
        -End at finish, so usage is recorded even on a direct double-click.
      * Shows tasks currently IN PROGRESS and a history of what each run did.
      * Reads the local SQLite warehouse (totals + RPA-synced rows).
      * Can launch Power Automate Desktop (the RPA runtime).
    The history file is cleared by clean.py (target: logs) / clean.bat.

.PARAMETER Begin
    [logging] Task name; writes a 'running' record and prints its run-id (only).
.PARAMETER End
    [logging] Run-id to finalize (pair with -ExitCode).
.PARAMETER ExitCode
    [logging] Exit code to store on -End (0 = ok).
.PARAMETER TaskArgs
    [logging] Optional free text stored with the run.
.PARAMETER Menu
    Interactive control panel (default when no other action is given).
.PARAMETER Dashboard
    Render the dashboard once and exit.
.PARAMETER Watch
    Live dashboard, refreshing every -Interval seconds (read-only).
.PARAMETER LaunchPad
    Start Power Automate Desktop and exit.
.PARAMETER ClearHistory
    Delete the run-history log and exit.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File monitor.ps1            # control panel
    powershell -ExecutionPolicy Bypass -File monitor.ps1 -Watch
    powershell -ExecutionPolicy Bypass -File monitor.ps1 -LaunchPad
#>
[CmdletBinding()]
param(
    [string]$Begin,
    [string]$End,
    [int]$ExitCode = 0,
    [string]$TaskArgs = '',
    [switch]$Menu,
    [switch]$Dashboard,
    [switch]$Watch,
    [int]$Interval = 5,
    [switch]$LaunchPad,
    [switch]$ClearHistory,
    [int]$Recent = 12,
    [string]$DbPath = ''
)

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$LogDir = Join-Path $Root 'logs'
$LogFile = Join-Path $LogDir 'run_history.jsonl'
$DriverName = 'SQLite3 ODBC Driver'

# Task name -> wrapper .bat in the repo root (used by the launcher menu).
$Tasks = [ordered]@{
    'install'     = 'install.bat'
    'setup'       = 'setup.bat'
    'setup_env'   = 'setup_env.bat'
    'pipeline'    = 'run_local_pipeline.bat'
    'generate'    = 'generate_invoices.bat'
    'send'        = 'send_documents.bat'
    'demo'        = 'run_demo.bat'
    'tests'       = 'run_tests.bat'
    'healthcheck' = 'healthcheck.bat'
    'clean'       = 'clean.bat'
}

# --------------------------------------------------------------------------- #
# logging primitives
# --------------------------------------------------------------------------- #
function Add-Event($obj) {
    try {
        if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
        ($obj | ConvertTo-Json -Compress) | Add-Content -Path $LogFile -Encoding UTF8
    } catch { }
}

function Invoke-Begin {
    $id = [guid]::NewGuid().ToString('N')
    Add-Event ([ordered]@{
        id = $id; phase = 'start'; task = $Begin; args = $TaskArgs
        time = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'); pid = $PID
    })
    Write-Output $id          # the ONLY thing on stdout, so a .bat can capture it
}

function Invoke-End {
    if (-not $End) { return }
    Add-Event ([ordered]@{
        id = $End; phase = 'end'; exitcode = $ExitCode
        time = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    })
}

function Get-Runs {
    if (-not (Test-Path $LogFile)) { return @() }
    $runs = @{}
    foreach ($line in Get-Content $LogFile) {
        if (-not $line.Trim()) { continue }
        try { $e = $line | ConvertFrom-Json } catch { continue }
        if (-not $runs.ContainsKey($e.id)) {
            $runs[$e.id] = [pscustomobject]@{
                id = $e.id; task = $null; args = ''; start = $null; end = $null; exitcode = $null
            }
        }
        $r = $runs[$e.id]
        if ($e.phase -eq 'start') { $r.task = $e.task; $r.args = $e.args; $r.start = $e.time }
        elseif ($e.phase -eq 'end') { $r.end = $e.time; $r.exitcode = $e.exitcode }
    }
    return $runs.Values
}

function Format-Duration([datetime]$a, [datetime]$b) {
    $s = [int]([math]::Round(($b - $a).TotalSeconds))
    if ($s -lt 60) { return "${s}s" }
    return ('{0}m {1}s' -f [int]($s / 60), ($s % 60))
}

# --------------------------------------------------------------------------- #
# dashboard
# --------------------------------------------------------------------------- #
function Resolve-DbPath {
    if ($DbPath) { return $DbPath }
    if ($env:ENERGOSMART_DB_PATH) { return $env:ENERGOSMART_DB_PATH }
    $envFile = Join-Path $PSScriptRoot '.env'
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*DB_PATH\s*=\s*(.+?)\s*$') {
                $v = $matches[1].Trim()
                if ($v -and -not $v.StartsWith('your-')) { return (Join-Path $PSScriptRoot $v) }
            }
        }
    }
    return (Join-Path $PSScriptRoot '..\2_Baza_Danych\energosmart_history.db')
}

function Show-Warehouse {
    Write-Host ''
    Write-Host '-- Warehouse (local SQLite) ----------------------------'
    $db = Resolve-DbPath
    try { $db = (Resolve-Path $db -ErrorAction Stop).Path } catch { }
    if (-not (Test-Path $db)) {
        Write-Host '   (no database yet - run pipeline)'; return
    }
    $conn = New-Object System.Data.Odbc.OdbcConnection
    $conn.ConnectionString = "Driver={$DriverName};Database=$db;"
    try { $conn.Open() } catch {
        Write-Host '   (ODBC driver missing - run setup.bat)'; return
    }
    try {
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = 'SELECT COUNT(*) FROM energosmart_history'
        $total = [int]$cmd.ExecuteScalar()
        $cmd.CommandText = "SELECT COUNT(*) FROM energosmart_history WHERE sector='Unknown'"
        $synced = [int]$cmd.ExecuteScalar()
        $cmd.CommandText = "SELECT MAX(inserted_at) FROM energosmart_history WHERE sector='Unknown'"
        $last = $cmd.ExecuteScalar()
        Write-Host ("   Total readings : {0:N0}" -f $total)
        Write-Host ("   RPA-synced     : {0:N0}   (sector='Unknown', from Flow 2 -> PAD)" -f $synced)
        if ($last) { Write-Host "   Last sync      : $last" }
    } finally { $conn.Close() }
}

function Show-Dashboard {
    Write-Host '========================================================'
    Write-Host '  EnergoSmart - Monitor / Control Panel'
    Write-Host ('  ' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))
    Write-Host '========================================================'

    Show-Warehouse

    $runs = @(Get-Runs)
    $running = @($runs | Where-Object { $_.start -and -not $_.end })
    Write-Host ''
    Write-Host '-- In progress -----------------------------------------'
    if ($running.Count -eq 0) {
        Write-Host '   (nothing running)'
    } else {
        foreach ($r in ($running | Sort-Object start)) {
            $el = Format-Duration ([datetime]$r.start) (Get-Date)
            Write-Host ("   * {0,-12} started {1}  (+{2})" -f $r.task, $r.start, $el)
        }
    }

    Write-Host ''
    Write-Host "-- Recent runs (last $Recent) --------------------------"
    $done = @($runs | Where-Object { $_.start } | Sort-Object start -Descending | Select-Object -First $Recent)
    if ($done.Count -eq 0) {
        Write-Host '   (no history yet)'
    } else {
        foreach ($r in $done) {
            if (-not $r.end) {
                $status = 'RUNNING'; $dur = '-'
            } elseif ([int]$r.exitcode -eq 0) {
                $status = 'OK     '; $dur = Format-Duration ([datetime]$r.start) ([datetime]$r.end)
            } else {
                $status = ('ERR {0,-3}' -f $r.exitcode); $dur = Format-Duration ([datetime]$r.start) ([datetime]$r.end)
            }
            Write-Host ("   {0}  {1,-12} {2}  ({3})" -f $status, $r.task, $r.start, $dur)
        }
    }
    Write-Host ''
}

# --------------------------------------------------------------------------- #
# launch Power Automate Desktop
# --------------------------------------------------------------------------- #
function Start-PAD {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Power Automate Desktop\PAD.Console.Host.exe'),
        (Join-Path $env:ProgramFiles 'Power Automate Desktop\PAD.Console.Host.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Power Automate\PAD.Console.Host.exe')
    )
    foreach ($exe in $candidates) {
        if ($exe -and (Test-Path $exe)) {
            Write-Host "[PAD] launching $exe"
            Start-Process $exe
            return
        }
    }
    try {
        $app = Get-StartApps | Where-Object { $_.Name -match 'Power Automate' } | Select-Object -First 1
        if ($app) {
            Write-Host "[PAD] launching '$($app.Name)' (Store/MSIX)"
            Start-Process ("shell:AppsFolder\" + $app.AppID)
            return
        }
    } catch { }
    Write-Host '[PAD] Power Automate Desktop not found.' -ForegroundColor Yellow
    Write-Host '      Install it (Windows Pro + MSI) or open it manually before attended runs.'
}

# --------------------------------------------------------------------------- #
# interactive control panel
# --------------------------------------------------------------------------- #
function Start-Task($task) {
    $bat = Join-Path $Root $Tasks[$task]
    if (-not (Test-Path $bat)) { Write-Host "[ERR] $bat not found"; return }
    # The .bat logs its own begin/end, so just launch and wait.
    Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "`"$bat`"" -Wait
}

function Show-Menu {
    while ($true) {
        Clear-Host
        Show-Dashboard
        Write-Host '-- Run a task ------------------------------------------'
        $i = 1
        $index = @{}
        foreach ($t in $Tasks.Keys) {
            Write-Host ("   [{0,2}] {1,-12} ({2})" -f $i, $t, $Tasks[$t])
            $index[[string]$i] = $t
            $i++
        }
        Write-Host ''
        Write-Host '   [ p] launch Power Automate Desktop (PAD)'
        Write-Host '   [ r] refresh    [ c] clear history    [ q] quit'
        $choice = Read-Host 'Select'
        switch -Regex ($choice) {
            '^[Qq]$' { return }
            '^[Rr]$' { continue }
            '^[Pp]$' { Start-PAD; Read-Host 'Enter to continue' }
            '^[Cc]$' {
                if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
                Write-Host '[OK] history cleared.'; Start-Sleep -Milliseconds 600
            }
            default {
                if ($index.ContainsKey($choice)) {
                    Start-Task $index[$choice]
                } else {
                    Write-Host '[?] unknown choice'; Start-Sleep -Milliseconds 600
                }
            }
        }
    }
}

# --------------------------------------------------------------------------- #
# dispatch
# --------------------------------------------------------------------------- #
if ($PSBoundParameters.ContainsKey('Begin')) { Invoke-Begin; return }
if ($PSBoundParameters.ContainsKey('End')) { Invoke-End; return }
if ($LaunchPad) { Start-PAD; return }
if ($ClearHistory) {
    if (Test-Path $LogFile) { Remove-Item $LogFile -Force; Write-Host '[OK] history cleared.' }
    else { Write-Host '[OK] no history to clear.' }
    return
}
if ($Watch) {
    while ($true) { Clear-Host; Show-Dashboard; Write-Host "(Ctrl+C to stop; refresh ${Interval}s)"; Start-Sleep -Seconds $Interval }
}
if ($Dashboard) { Show-Dashboard; return }
Show-Menu
