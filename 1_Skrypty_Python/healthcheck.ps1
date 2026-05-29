<#
.SYNOPSIS
    EnergoSmart warehouse health-check - read-only report on the local SQLite
    history DB, with a focus on rows synced from the cloud by the RPA bridge.

.DESCRIPTION
    Connects to energosmart_history.db through the SQLite3 ODBC Driver (the same
    driver the Power Automate Desktop flow uses, installed by setup.py) and prints:
      - total rows, distinct clients, flagged anomalies
      - status breakdown
      - the most recent RPA-synced readings (PAD inserts them with sector='Unknown')

    Use it after running Flow 2 to confirm an Accepted reading actually reached
    the local warehouse.

.PARAMETER DbPath
    Path to the .db file. Defaults to $env:ENERGOSMART_DB_PATH, then DB_PATH from
    .env, then ..\2_Baza_Danych\energosmart_history.db relative to this script.

.PARAMETER Recent
    How many recent RPA-synced rows to list (default 10).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File healthcheck.ps1
    powershell -ExecutionPolicy Bypass -File healthcheck.ps1 -Recent 20
#>
[CmdletBinding()]
param(
    [string]$DbPath = '',
    [int]$Recent = 10
)

$ErrorActionPreference = 'Stop'
$DriverName = 'SQLite3 ODBC Driver'

function Write-Header($text) {
    Write-Host ''
    Write-Host ('=' * 56)
    Write-Host "  $text"
    Write-Host ('=' * 56)
}

function Resolve-DbPath {
    param([string]$Explicit)
    if ($Explicit) { return $Explicit }
    if ($env:ENERGOSMART_DB_PATH) { return $env:ENERGOSMART_DB_PATH }
    $envFile = Join-Path $PSScriptRoot '.env'
    if (Test-Path $envFile) {
        foreach ($line in Get-Content $envFile) {
            if ($line -match '^\s*DB_PATH\s*=\s*(.+?)\s*$') {
                $val = $matches[1].Trim()
                if ($val -and -not $val.StartsWith('your-')) {
                    return (Join-Path $PSScriptRoot $val)
                }
            }
        }
    }
    return (Join-Path $PSScriptRoot '..\2_Baza_Danych\energosmart_history.db')
}

function Get-Scalar {
    param($Connection, [string]$Sql)
    $cmd = $Connection.CreateCommand()
    $cmd.CommandText = $Sql
    $value = $cmd.ExecuteScalar()
    $cmd.Dispose()
    if ($null -eq $value -or $value -is [DBNull]) { return 0 }
    return $value
}

function Read-Rows {
    param($Connection, [string]$Sql)
    $cmd = $Connection.CreateCommand()
    $cmd.CommandText = $Sql
    $reader = $cmd.ExecuteReader()
    $rows = @()
    while ($reader.Read()) {
        $obj = [ordered]@{}
        for ($i = 0; $i -lt $reader.FieldCount; $i++) {
            $obj[$reader.GetName($i)] = $reader.GetValue($i)
        }
        $rows += [pscustomobject]$obj
    }
    $reader.Close()
    $cmd.Dispose()
    return $rows
}

# --- resolve + validate the DB path ------------------------------------------
$resolved = Resolve-DbPath -Explicit $DbPath
try { $resolved = (Resolve-Path $resolved -ErrorAction Stop).Path } catch { }

Write-Header 'EnergoSmart - Warehouse Health-Check'
Write-Host "  Database: $resolved"

if (-not (Test-Path $resolved)) {
    Write-Host ''
    Write-Host '[ERROR] Database not found.' -ForegroundColor Red
    Write-Host '        Build it first: run_local_pipeline.bat (or generate_history_db.py).'
    exit 1
}

# --- connect through the SQLite ODBC driver ----------------------------------
$conn = New-Object System.Data.Odbc.OdbcConnection
$conn.ConnectionString = "Driver={$DriverName};Database=$resolved;"
try {
    $conn.Open()
} catch {
    Write-Host ''
    Write-Host '[ERROR] Could not open the database via ODBC.' -ForegroundColor Red
    Write-Host "        $($_.Exception.Message)"
    Write-Host "        The '$DriverName' (64-bit) is probably missing - install it"
    Write-Host '        with setup.bat (python setup.py), and run from 64-bit PowerShell.'
    exit 1
}

try {
    $total = [int](Get-Scalar $conn 'SELECT COUNT(*) FROM energosmart_history')
    $clients = [int](Get-Scalar $conn 'SELECT COUNT(DISTINCT client_id) FROM energosmart_history')
    $anomalies = [int](Get-Scalar $conn 'SELECT COUNT(*) FROM energosmart_history WHERE anomaly_flag = 1')
    $synced = [int](Get-Scalar $conn "SELECT COUNT(*) FROM energosmart_history WHERE sector = 'Unknown'")

    Write-Header 'Overview'
    Write-Host ("  Total readings   : {0:N0}" -f $total)
    Write-Host ("  Distinct clients : {0:N0}" -f $clients)
    Write-Host ("  Flagged anomalies: {0:N0}" -f $anomalies)
    Write-Host ("  RPA-synced rows  : {0:N0}   (sector='Unknown', from Cloud Flow 2 -> PAD)" -f $synced)

    Write-Header 'Status breakdown'
    $statusRows = Read-Rows $conn 'SELECT status, COUNT(*) AS readings FROM energosmart_history GROUP BY status ORDER BY readings DESC'
    if ($statusRows) {
        $statusRows | Format-Table -AutoSize | Out-String | Write-Host
    } else {
        Write-Host '  (no rows)'
    }

    Write-Header "Recent RPA-synced readings (last $Recent)"
    if ($synced -eq 0) {
        Write-Host '  None yet. Accept a reading so Cloud Flow 2 inserts it here.'
        Write-Host "  (Looking for rows with sector='Unknown'.)"
    } else {
        $recentRows = Read-Rows $conn ("SELECT client_id, reading_date, consumption_kwh, status, inserted_at " +
            "FROM energosmart_history WHERE sector = 'Unknown' ORDER BY inserted_at DESC LIMIT $Recent")
        $recentRows | Format-Table -AutoSize | Out-String | Write-Host
    }
} finally {
    $conn.Close()
}

Write-Host ''
Write-Host '[OK] Health-check complete.' -ForegroundColor Green
exit 0
