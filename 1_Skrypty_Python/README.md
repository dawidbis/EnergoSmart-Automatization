# 1 - Python Data Engineering Layer

Generates the simulated "billing system" history and the client reports that feed
the cloud pipeline.

## Scripts

### Pipeline / data generation

| Script | Purpose |
|---|---|
| `generate_history_db.py` | Builds the SQLite history DB: 150 business clients across 7 sectors, 24 months of weekly readings (~14.7k rows), with sector-realistic baselines, seasonal variation and flagged anomalies. |
| `simulate_clients.py` | Reads the DB and produces per-client **Excel** and **PDF** reports into `3_Dokumenty_Testowe/`, randomly injecting consumption anomalies (spike / drop / noise) to exercise the AI + review paths. |

### Operator tools (exercise & observe the flow)

| Script | Wrapper `.bat` | Purpose |
|---|---|---|
| `generate_invoices.py` | `generate_invoices.bat` | Generates a chosen number of typed test documents split by Cloud Flow path: **GREEN** (valid → auto-accept), **YELLOW** (zero/spike/drop → manual review), **RED** (flyer/blank → auto-reject). Files are named `GREEN_*` / `YELLOW_*` / `RED_*` so the other tools recognise them. |
| `send_documents.py` | `send_documents.bat` | Emails a chosen number and type (`green`/`yellow`/`red`/`all`) of the prepared PDFs to the monitored inbox via SMTP. Supports `--delay`, custom `--subject-prefix`, and `--dry-run` (list only). |
| `monitor_company.py` | `monitor.bat` | Read-only live dashboard: counts documents in the inbox by path, reads the SQLite warehouse (totals, anomalies, status breakdown, RPA-synced rows) and draws the end-to-end flow. `--watch` refreshes on an interval. |
| `clean_test_documents.py` | `clean_test_data.bat` | Removes generated `*.pdf` / `*.xlsx` from `3_Dokumenty_Testowe/`. **Dry run by default**; pass `--yes` (the `.bat` asks for confirmation) to actually delete. Never touches the DB or source. |

## Configuration (`.env`)

Copy `.env.example` → `.env` (install.bat does this automatically). Variables:

| Variable | Used by | Default |
|---|---|---|
| `DB_PATH` | generate, simulate, generate_invoices, monitor | `../2_Baza_Danych/energosmart_history.db` |
| `OUTPUT_DIR` | simulate, generate_invoices, send, monitor, clean | `../3_Dokumenty_Testowe` |
| `NUM_CLIENTS` | generate | `150` |
| `SMTP_*`, `*_EMAIL` | simulate, send_documents | — |

> Note: dataset volume scales with `NUM_CLIENTS` and the fixed 24-month window
> (≈ 98 readings per client). Increase `NUM_CLIENTS` for a larger database.

## Run

```bat
python generate_history_db.py   # 1. build DB
python simulate_clients.py      # 2. build reports
```

Or from the repo root: `run_local_pipeline.bat`

### Operator tools

```bat
python generate_invoices.py --green 5 --yellow 3 --red 2   # make typed docs
python send_documents.py --type yellow --count 2           # email them
python send_documents.py --type all --count 1 --dry-run    # preview only
python monitor_company.py --watch --interval 3             # live dashboard
python clean_test_documents.py            # dry run (list what would be deleted)
python clean_test_documents.py --yes      # actually delete generated docs
```

Or from the repo root, double-click: `generate_invoices.bat`, `send_documents.bat`,
`monitor.bat`, `clean_test_data.bat` (each prompts interactively).

## Tests

```bat
python -m pytest tests -v
```

`tests/test_pipeline.py` covers:
- DB schema + row generation (subprocess against a temp DB)
- Excel/PDF document generation
- Failure path when the DB is missing
- Unit tests for consumption + client-profile generation

## Dependencies

- Runtime: `requirements.txt` (pandas, openpyxl, fpdf2, python-dotenv, requests)
- Dev: `requirements-dev.txt` (adds pytest, flake8)
