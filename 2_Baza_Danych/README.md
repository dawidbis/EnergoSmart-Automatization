# 2 - SQLite Database

`energosmart_history.db` is the simulated billing/warehouse system. It is
**generated** by `1_Skrypty_Python/generate_history_db.py` and is git-ignored
(rebuild it with `run_local_pipeline.bat`).

This is also the local target the **Desktop Flow (RPA)** writes validated readings
back into — the "bridge" between the cloud and the legacy on-prem database.

## Table: `energosmart_history`

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `client_id` | TEXT NOT NULL | e.g. `CLIENT_0042` |
| `client_name` | TEXT NOT NULL | e.g. `FabrykaChemiczna_42` |
| `sector` | TEXT NOT NULL | one of 7 sectors |
| `reading_date` | DATE NOT NULL | |
| `consumption_kwh` | REAL NOT NULL | |
| `month_avg_kwh` | REAL | monthly average (anomaly baseline) |
| `anomaly_flag` | INTEGER DEFAULT 0 | 1 if deviation > 40% from month avg |
| `anomaly_reason` | TEXT | populated when flagged |
| `status` | TEXT DEFAULT 'validated' | `validated` / future RPA inserts |
| `inserted_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

Constraints / indexes:
- `UNIQUE(client_id, reading_date)` — prevents duplicate readings
- `idx_client_date (client_id, reading_date)`
- `idx_anomaly (anomaly_flag, status)`

## Sectors

Factory (chemical), shopping mall, office building, logistics hall, data center,
hospital, hotel — each with its own consumption baseline range and variance.

## Connecting from Power Automate Desktop

SQLite has no native Power Platform connector. The Desktop Flow uses an **ODBC**
connection (e.g. the SQLite ODBC Driver by Ch. Werner) to run `INSERT INTO`
against this file. See `5_RPA_Desktop_Flow/`.
