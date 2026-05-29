# 5 - RPA Desktop Flow (cloud → local SQLite bridge)

This is the **headline technical piece**: when a reading is `Accepted` in Dataverse,
Cloud Flow 2 calls a **Power Automate Desktop (PAD)** flow that writes the validated
reading straight into the on-prem warehouse `2_Baza_Danych/energosmart_history.db`.

SQLite has no native Power Platform connector, so the bridge runs **locally** over
an **ODBC** connection. PAD is the "machine connector" that lets a cloud flow reach
a file on this PC.

```
Dataverse (Accepted)  ──►  Cloud Flow 2  ──►  PAD_UpdateSQLDatabase  ──►  ODBC  ──►  energosmart_history.db
   db_status=Accepted        (cloud)           (this machine, RPA)              INSERT row
                                   ▲                                                  │
                                   └────────────── on success: db_status = Synced ◄──┘
```

Artifacts in this folder:
- **`PAD_kod_zrodlowy.txt`** — the desktop-flow logic (Robin source + GUI action map).

---

## Prerequisites

- Windows with the local warehouse generated (`run_local_pipeline.bat` →
  `2_Baza_Danych/energosmart_history.db` exists).
- The same Microsoft 365 account used for the cloud flows.
- Cloud Flow 1 + the Power Apps review app already working (layers 1–4).

---

## Step 1 — Install Power Automate Desktop

1. Install **Power Automate Desktop** (from Microsoft Store or aka.ms/PADInstaller).
2. Sign in with the **same M365 account** as the cloud environment.
   - On first sign-in the machine **auto-registers** as a runtime target, so cloud
     flows can call desktop flows on it.
3. Confirm the machine shows up: Power Automate (web) → **Monitor → Machines**.

---

## Step 2 — Install the SQLite ODBC driver

Power Automate has no SQLite connector, so install an ODBC driver.

**Automated (recommended):** run **`setup.bat`** from the repo root (or just
`install.bat`, which calls it). It checks the registry for the driver and, if
missing, downloads the 64-bit installer and runs it silently — accept the UAC
prompt — **and** sets the `ENERGOSMART_DB_PATH` env var (see Option A).
`python 1_Skrypty_Python/setup.py --check-only` reports driver status only.

**Manual:**

1. Download **"SQLite ODBC Driver"** by Ch. Werner: http://www.ch-werner.de/sqliteodbc/
   - Use the **64-bit** installer (`sqliteodbc_w64.exe`) to match 64-bit PAD.
2. Install with defaults. This registers the driver name **`SQLite3 ODBC Driver`**.

### Option A — env var (recommended, portable)

Don't hard-code the path. `setup.bat` / `install.bat` set the Windows env var
`ENERGOSMART_DB_PATH` to the absolute path of the warehouse. In the flow, read it
with a **Get Windows environment variable** action
(`ENERGOSMART_DB_PATH` → `EnvironmentVariableValue`) as the first step, then use:

```
Driver=SQLite3 ODBC Driver;Database=%EnvironmentVariableValue%;
```

> Env vars are read at process start — **restart PAD** after first setting it,
> otherwise the variable won't appear in the action's dropdown.

### Option B — DSN-less, hard-coded path (fallback)

Only if the env var isn't set. Use this string directly in "Open SQL connection":

```
Driver=SQLite3 ODBC Driver;Database=D:\EnergoSmart\EnergoSmart-Automatization\2_Baza_Danych\energosmart_history.db;
```

### Option C — System DSN (cleaner, reusable)

1. Open **ODBC Data Sources (64-bit)** (Windows search).
2. **System DSN** tab → **Add** → choose **SQLite3 ODBC Driver** → **Finish**.
3. Data Source Name: `EnergoSmartDB`; Database: browse to `energosmart_history.db`.
4. **OK**. Connection string becomes simply: `DSN=EnergoSmartDB;`

---

## Step 3 — Build the desktop flow `PAD_UpdateSQLDatabase`

1. PAD → **New flow** → name `PAD_UpdateSQLDatabase`.
2. **Variables** pane → **Input/Output variables** → add three **inputs**:
   | Variable | Type | Example |
   |---|---|---|
   | `ClientID` | Text | `CLIENT_0042` |
   | `Consumption` | Text | `12345.67` |
   | `ReadingDate` | Text | `2026-05-28` |
   Optionally add **outputs** `SyncStatus` (Text) and `RowsAffected` (Numeric).
3. Recreate the logic from **`PAD_kod_zrodlowy.txt`** — either paste the Robin
   source or build the actions via the **GUI action map** at the bottom of that file:
   - **Get Windows environment variable** (`ENERGOSMART_DB_PATH` → `EnvironmentVariableValue`)
   - **Open SQL connection** (`Driver=SQLite3 ODBC Driver;Database=%EnvironmentVariableValue%;`)
   - **Execute SQL statement** (the `INSERT OR REPLACE`)
   - **Close SQL connection**
   - guards for empty inputs + an error handler that reports back and closes.
4. **Save**.

### What gets written

The warehouse columns `client_id, client_name, sector, reading_date, consumption_kwh`
are `NOT NULL`. The flow fills them as:

| Column | Source |
|---|---|
| `client_id` | input `ClientID` |
| `client_name` | input `ClientID` (Dataverse row has no separate warehouse name) |
| `sector` | `'Unknown'` (sector unknown at sync time) |
| `reading_date` | `date(ReadingDate)` — normalized to `YYYY-MM-DD` |
| `consumption_kwh` | input `Consumption` |
| `status` | `'validated'` |
| `inserted_at` | `datetime('now')` |

`INSERT OR REPLACE` is used because of the `UNIQUE(client_id, reading_date)` key —
it makes a re-sync idempotent instead of throwing.

---

## Step 4 — Wire it to Cloud Flow 2

See **`../4_Power_Platform_Solucja/FLOW_2_STATUS_TRIGGER.md`**. Flow 2:
1. triggers on Dataverse row **Modified**,
2. checks `Status = Accepted`,
3. calls **Run a flow built with Power Automate Desktop → `PAD_UpdateSQLDatabase`**
   passing `ClientID`, `Consumption`, `ReadingDate`,
4. on success sets the row `Status = Synced`, `Verified At = utcNow()`.

> **Student / dev tenant note:** desktop flows here usually run **attended**.
> Keep PAD open and signed in while testing Flow 2, and pick the **attended**
> run mode + your machine (not a machine group) in the cloud action.

---

## Step 5 — Test end to end

1. Keep PAD open and signed in.
2. In the Power Apps review app, **Accept** a `Pending Review` reading
   (or flip a row's `Status` to `Accepted` in Dataverse directly).
3. Watch Flow 2's run history — the desktop-flow action should succeed.
4. Confirm the row landed locally:
   ```bat
   python -c "import sqlite3;c=sqlite3.connect(r'2_Baza_Danych/energosmart_history.db');print(c.execute(\"SELECT client_id,reading_date,consumption_kwh,status FROM energosmart_history WHERE sector='Unknown' ORDER BY inserted_at DESC LIMIT 5\").fetchall())"
   ```
5. Back in Dataverse the row's `Status` should now read **Synced**.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Cloud flow can't find the machine | PAD signed in with the **same** account? Machine shows under Monitor → Machines? |
| `Data source name not found` | Wrong bitness — install **64-bit** SQLite ODBC; or DSN created under 32-bit applet. |
| `database is locked` | Close any other process holding the `.db` (DB Browser, a Python script). |
| `UNIQUE constraint failed` | You used a plain `INSERT`; switch to `INSERT OR REPLACE` (see source). |
| Date mismatch / duplicate dates | Ensure `reading_date` is wrapped in SQLite `date(...)` to normalize ISO timestamps. |
| Desktop flow never runs | Choose **attended** mode + your specific machine in the cloud action. |

## Also see
- `PAD_kod_zrodlowy.txt` — the flow source
- `../2_Baza_Danych/README.md` — warehouse schema
- `../4_Power_Platform_Solucja/FLOW_2_STATUS_TRIGGER.md` — Cloud Flow 2
- `../NEXT_STEPS.md` — roadmap (Step 5 / Step 6)
