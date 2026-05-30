# EnergoSmart Automatization

End-to-end automation platform that ingests monthly energy-consumption reports
from business clients (Excel files and scanned meter readings), extracts the data
with **custom-trained AI**, routes anomalies through a **human-in-the-loop** review
process, and syncs validated readings back into a historical SQL database that
powers management dashboards.

This is a portfolio project demonstrating an integration across **Python data
engineering**, **Microsoft Power Platform** (Power Automate, AI Builder, Dataverse,
Power Apps), **RPA** (Power Automate Desktop) and **Power BI**.

---

## Architecture

```
[LOCAL SIMULATION]
  Python -> generates SQLite history + Excel/PDF reports -> emails them
        │
        ▼
[CLOUD - INTELLIGENT INTAKE]
  Cloud Flow 1 -> reads email -> passes attachment to AI
        ├─> AI Builder (custom model) -> extracts ClientID, Consumption, Date (+ confidence)
        ▼
[CLOUD - DATA & DECISIONS]
  Dataverse -> stores reading with a status
        ├─> Power Apps -> review screen for flagged readings (human-in-the-loop)
        ▼
[CLOUD - LOGIC PROCESSOR]
  Cloud Flow 2 -> fires when status = Accepted
        ▼
[LOCAL - RPA + WAREHOUSE]
  Desktop Flow -> INSERT INTO local SQLite (energosmart_history.db)
        ▼
[ANALYTICS]
  Power BI -> Dataverse (DirectQuery: live queue + AI accuracy)
           -> SQLite (Import: long-term trends, DAX measures)
```

### Decision logic (Green / Yellow / Red)

| Path | Condition | Action |
|---|---|---|
| 🟢 **Green** (auto-accept) | AI confidence > 85% AND consumption > 0 | Write to Dataverse as `Accepted` → straight to SQL via RPA |
| 🟡 **Yellow** (review) | Low confidence OR consumption anomaly | Write as `Pending Review` → queued in Power Apps |
| 🔴 **Red** (auto-reject) | Critical data missing (no Client ID / value) | No record; rejection email to client |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Data engineering | Python, pandas, SQLite, openpyxl, fpdf2 |
| CI/CD | GitHub Actions (flake8 lint + pytest) |
| Cloud automation | Power Automate (Cloud Flows) |
| AI / OCR | AI Builder (custom document-processing model) |
| Database (cloud) | Microsoft Dataverse |
| Front-end | Power Apps (model-driven app) |
| RPA / integration | Power Automate Desktop (ODBC → SQLite) |
| Analytics | Power BI (DirectQuery + Import, DAX) |

---

## Quick Start (local data layer)

> Requires Python 3.10+ on Windows.

```bat
:: Easiest - one guided run-through (asks before each step):
::   install -> configure email -> build DB -> generate -> send
demo.bat

:: Then watch the flow and capture screenshots for the docs:
monitor.bat
```

The helper tools live in `1_Scripts\bat\` (install, setup_odbc_bridge,
configure_email, build_database, generate_documents, send_documents, run_tests,
warehouse_healthcheck, clean_artifacts) and can also be launched from `monitor.bat`.

After `build_database.bat`:
- `2_Database/energosmart_history.db` — historical SQLite database

Then generate the test documents with `generate_documents.bat` (Green/Yellow/Red) into
`3_Test_Documents/`. Those PDFs are also the **training set** for the AI Builder model.

For the full run-through, double-click **`demo.bat`** in the repo root. After an
Accepted reading syncs back, confirm it landed locally with **`monitor.bat`**
(or `1_Scripts\bat\warehouse_healthcheck.bat`).

---

## Project Structure

```
EnergoSmart-Automatization/
├── .github/workflows/python-lint.yml   # CI: flake8 lint + pytest
├── 1_Scripts/                          # Data engineering layer (grouped by type)
│   ├── py/                             # Python scripts + tests + requirements + .env
│   │   ├── generate_history_db.py      # Builds SQLite history (150 clients x 24 months)
│   │   ├── generate_invoices.py        # Generates typed test documents (Green/Yellow/Red)
│   │   ├── simulate_clients.py         # Shared PDF/DB helper module (imported above)
│   │   ├── clean.py setup.py setup_env.py send_documents.py generate_bad_reports.py
│   │   └── tests/test_pipeline.py      # pytest suite
│   ├── ps/                             # PowerShell tools + the shared SQL library
│   │   ├── monitor.ps1                 # Control panel / run-history / launch PAD
│   │   ├── healthcheck.ps1             # Warehouse health-check (SQLite ODBC)
│   │   └── sql/                        # *.sql query library (schema, inserts, reports)
│   ├── bat/                            # Double-click wrappers (also run from monitor)
│   │   ├── install.bat                 # Plug & Play installer
│   │   ├── setup_odbc_bridge.bat       # SQLite ODBC driver + DB-path env var
│   │   ├── configure_email.bat         # Email / .env wizard
│   │   ├── build_database.bat          # Build the SQLite warehouse (DB only)
│   │   ├── generate_documents.bat      # Make typed test documents
│   │   ├── send_documents.bat          # Email documents to the inbox
│   │   ├── warehouse_healthcheck.bat   # Warehouse health-check (RPA-synced rows)
│   │   ├── clean_artifacts.bat         # Clean test artifacts / logs / RPA rows
│   │   └── run_tests.bat               # Run pytest
│   └── logs/                           # Monitor run-history (runtime; git-ignored)
├── 2_Database/                         # SQLite database (generated; git-ignored)
├── 3_Test_Documents/                   # Generated docs / AI training set (git-ignored)
├── 4_Power_Platform_Solution/          # Cloud setup guides + flow blueprints
│   ├── 00_SOLUTION_SETUP.md            # START HERE: Solution -> connections -> table
│   ├── SETUP_GUIDE.md                  # Cloud Flow 1 (Email Processor)
│   ├── AI_BUILDER_RETRAIN.md           # Yellow-path anomaly + Client ID/Name retrain
│   └── FLOW_2_STATUS_TRIGGER.md        # Cloud Flow 2 (Status -> Desktop Flow)
├── 5_RPA_Desktop_Flow/                 # Power Automate Desktop (SQLite bridge)
├── 6_Power_BI_Dashboard/               # Power BI report + theme
├── 7_Documentation/                    # Report checklist / screenshots
├── demo.bat                            # Full guided run (front door, repo root)
└── monitor.bat                         # Control panel (front door, repo root)
```

---

## Building the Cloud Layer

The Power Platform side is built manually in the maker portal (it can't be fully
scripted). Step-by-step guides live in `4_Power_Platform_Solution/`:

1. `00_SOLUTION_SETUP.md` — Solution, publisher, connections, Dataverse table
2. `SETUP_GUIDE.md` — Cloud Flow 1 (email intake + AI Builder + branching)
3. `FLOW_2_STATUS_TRIGGER.md` — Cloud Flow 2 (Dataverse trigger → Desktop Flow)

Once complete, export the solution as a managed `.zip` into
`4_Power_Platform_Solution/` for re-import to other environments.

---

## Status

| Component | State |
|---|---|
| Python data layer | ✅ Done (DB generator, report simulator, tests) |
| CI/CD | ✅ Done (lint + tests) |
| Dataverse table `Readings` | ✅ Done |
| AI Builder model | ✅ Done (custom document model, 99%, published) |
| Cloud Flow 1 (Email Processor) | ✅ Done (🟢/🟡/🔴 paths live) |
| Power Apps review UI | ✅ Done (Pending Review queue, Akceptuj/Odrzuć) |
| Cloud Flow 2 (Status → RPA) | ✅ Done (fires on **Added or Modified**, Status = Accepted) |
| Desktop Flow (SQLite bridge) | ✅ Done (PAD → ODBC → SQLite, proven end to end) |
| Power BI dashboard | ⏳ Planned (Step 6) |
