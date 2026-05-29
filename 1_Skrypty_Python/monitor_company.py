"""
EnergoSmart - Local company monitor (read-only dashboard).

Shows the state of the local pipeline at a glance:
  * Inbox     - prepared documents in OUTPUT_DIR by path type (green/yellow/red)
  * Warehouse - SQLite stats: rows, clients, anomalies, status breakdown and
                readings synced via the RPA bridge (sector = 'Unknown')
  * Flow      - a one-line snapshot of prepared -> emailed -> synced

Use --watch to refresh continuously (Ctrl+C to stop).
    python monitor_company.py
    python monitor_company.py --watch --interval 3
"""

import argparse
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DB_PATH', '../2_Baza_Danych/energosmart_history.db')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')

PREFIXES = {'green': 'GREEN_', 'yellow': 'YELLOW_', 'red': 'RED_'}


def scan_inbox():
    """Count prepared documents in OUTPUT_DIR by path type."""
    counts = {'green': 0, 'yellow': 0, 'red': 0, 'other': 0}
    base = Path(OUTPUT_DIR)
    if not base.exists():
        return counts
    for file_path in base.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in ('.pdf', '.xlsx'):
            continue
        if file_path.name.startswith(PREFIXES['green']):
            counts['green'] += 1
        elif file_path.name.startswith(PREFIXES['yellow']):
            counts['yellow'] += 1
        elif file_path.name.startswith(PREFIXES['red']):
            counts['red'] += 1
        else:
            counts['other'] += 1
    return counts


def db_stats():
    """Read warehouse statistics from the SQLite database."""
    stats = {'exists': False}
    if not os.path.exists(DB_PATH):
        return stats
    stats['exists'] = True
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM energosmart_history')
    stats['total'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(DISTINCT client_id) FROM energosmart_history')
    stats['clients'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM energosmart_history WHERE anomaly_flag = 1')
    stats['anomalies'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM energosmart_history WHERE sector = 'Unknown'")
    stats['synced_rpa'] = cur.fetchone()[0]
    cur.execute('SELECT status, COUNT(*) AS n FROM energosmart_history '
                'GROUP BY status ORDER BY n DESC')
    stats['by_status'] = [(row['status'], row['n']) for row in cur.fetchall()]
    cur.execute('SELECT MAX(inserted_at) FROM energosmart_history')
    stats['last_activity'] = cur.fetchone()[0]
    cur.execute("SELECT client_id, reading_date, consumption_kwh, status, inserted_at "
                "FROM energosmart_history WHERE sector = 'Unknown' "
                "ORDER BY inserted_at DESC LIMIT 5")
    stats['recent_synced'] = [dict(row) for row in cur.fetchall()]
    conn.close()
    return stats


def render(inbox, stats):
    """Print the dashboard once."""
    line = '=' * 64
    print(line)
    print('  ENERGOSMART - LOKALNY MONITOR FIRMY')
    print(f'  {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(line)

    inbox_total = sum(inbox.values())
    print('\n[1] SKRZYNKA / DOKUMENTY DO WYSLANIA  (OUTPUT_DIR)')
    print(f'    GREEN  (auto-accept)    : {inbox["green"]}')
    print(f'    YELLOW (do weryfikacji) : {inbox["yellow"]}')
    print(f'    RED    (do odrzucenia)  : {inbox["red"]}')
    print(f'    inne / niesklasyfikowane: {inbox["other"]}')
    print(f'    RAZEM                   : {inbox_total}')

    print('\n[2] HURTOWNIA DANYCH (SQLite)')
    if not stats['exists']:
        print(f'    [!] Brak bazy: {DB_PATH}')
        print('        Uruchom: python generate_history_db.py')
    else:
        print(f'    Rekordy: {stats["total"]:,}   Klienci: {stats["clients"]}')
        print(f'    Anomalie (flaga): {stats["anomalies"]:,}')
        print(f'    Zsynchronizowane przez RPA (sector=Unknown): {stats["synced_rpa"]}')
        statuses = ', '.join(f'{s}={n}' for s, n in stats['by_status'])
        print(f'    Statusy: {statuses}')
        print(f'    Ostatnia aktywnosc: {stats["last_activity"]}')

    print('\n[3] PRZEPLYW (FLOW)')
    synced = stats.get('synced_rpa', 0) if stats.get('exists') else 0
    print(f'    [Dokumenty: {inbox_total}] --email--> [Cloud Flow + AI Builder] '
          f'--RPA--> [SQLite: {synced} zsync.]')

    if stats.get('recent_synced'):
        print('\n    Ostatnio zsynchronizowane odczyty (RPA bridge):')
        for row in stats['recent_synced']:
            print(f'      - {row["client_id"]}  {row["reading_date"]}  '
                  f'{row["consumption_kwh"]:.2f} kWh  [{row["status"]}]  '
                  f'@ {row["inserted_at"]}')
    print(line)


def main():
    parser = argparse.ArgumentParser(description='EnergoSmart local company monitor.')
    parser.add_argument('--watch', action='store_true',
                        help='refresh continuously until Ctrl+C')
    parser.add_argument('--interval', type=float, default=3.0,
                        help='refresh interval in seconds (with --watch)')
    args = parser.parse_args()

    if not args.watch:
        render(scan_inbox(), db_stats())
        return 0

    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            render(scan_inbox(), db_stats())
            print(f'\n(odswiezanie co {args.interval}s - Ctrl+C aby zakonczyc)')
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print('\n[STOP] Monitor zatrzymany.')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
