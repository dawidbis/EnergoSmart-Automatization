# 1 - Python Data Engineering Layer

Generates the simulated "billing system" history and the client reports that feed
the cloud pipeline.

## Scripts

### Pipeline / data generation

| Script | Purpose |
|---|---|
| `generate_history_db.py` | Builds the SQLite history DB: 150 business clients across 7 sectors, 24 months of weekly readings (~14.7k rows), with sector-realistic baselines, seasonal variation and flagged anomalies. |
| `simulate_clients.py` | **Shared helper module** — the PDF layout (`EnergyReportPDF`) + DB readers (`fetch_recent_readings`, `get_all_clients`) that `generate_invoices.py` imports. It can still dump per-client reports if run standalone, but the **pipeline no longer calls it**: test documents are generated **only** by `generate_invoices.py`. |

### Operator tools (exercise & observe the flow)

| Script | Wrapper `.bat` | Purpose |
|---|---|---|
| `setup.py` | `setup.bat` | One-time **RPA-bridge setup**: detects the **SQLite3 ODBC Driver** (downloads + installs it silently with elevation if missing) **and** sets the Windows env var **`ENERGOSMART_DB_PATH`** (absolute warehouse path the PAD desktop flow reads). `--check-only` reports driver status only. `install.bat` runs it automatically. |
| `setup_env.py` | `setup_env.bat` | Interactive wizard that writes `.env` (email/SMTP). Pre-fills defaults from any existing `.env`/`.env.example`, infers the SMTP server from your email domain (Gmail / Outlook / Microsoft 365), hides the password, backs up an existing `.env` to `.env.bak`, and can test the SMTP login (`--test`). |
| `generate_invoices.py` | `generate_invoices.bat` | Generates a chosen number of typed test documents split by Cloud Flow path: **GREEN** (valid → auto-accept), **YELLOW** (zero/spike/drop → manual review), **RED** (flyer/blank → auto-reject). Files are named `GREEN_*` / `YELLOW_*` / `RED_*` so the other tools recognise them. |
| `send_documents.py` | `send_documents.bat` | Emails prepared PDFs to the monitored inbox via SMTP. Recognises **typed docs** (`GREEN_/YELLOW_/RED_`) **and pipeline meter readings** (`*_MeterReading_*.pdf`, counted as GREEN). Pick **several / one / all paths** and, per path, a **specific count or `all`** (e.g. `--green 3 --yellow all --red 1`). `--interactive` prompts for everything; also `--delay`, `--subject-prefix`, `--dry-run`. |
| `clean.py` | `clean.bat` | One cleaner for all test artifacts: generated `*.pdf`/`*.xlsx` (`--target files`), the **Microsoft 365** inbox via classic **Outlook COM** (`--target outlook`, since M365 blocks basic-auth IMAP), **Gmail** Sent + bounced-back mail via **IMAP → Trash** (`--target gmail`), the **monitor run-history** (`--target logs`), the **RPA-synced warehouse rows** (`--target rpa`, only `sector='Unknown'` test inserts), or `all`. **Dry run by default**; `--yes` deletes (the `.bat` asks first). Never touches the **seeded history** or source. |
| _(orchestrator)_ | `demo.bat` (repo root) | **Full guided run** for a fresh machine: install → configure email → build DB → generate → send. Calls the `bat\` wrappers in order, asking before each step. |
| `healthcheck.ps1` | `healthcheck.bat` | Read-only **warehouse health-check** (PowerShell + SQLite ODBC, the same driver the RPA uses): totals, anomalies, status breakdown and the most recent **RPA-synced** rows (`sector='Unknown'`). Confirms an Accepted reading reached the local DB. `-Recent N` to list more. |
| `monitor.ps1` | `monitor.bat` | **Control panel / monitor.** Logs every wrapper `.bat` run (start / end / exit code / duration) to `logs/run_history.jsonl`, shows tasks **in progress** + recent history ("what each run did"), reads the SQLite warehouse, and can **launch Power Automate Desktop**. `-Watch` = live read-only dashboard; `-LaunchPad`; `-ClearHistory`. History is cleared by `clean.py --target logs`. |

## Configuration (`.env`)

Easiest path: run **`setup_env.bat`** (or `python setup_env.py`) — an interactive
wizard that fills in the email/SMTP settings for you. Otherwise copy
`.env.example` → `.env` (install.bat does this automatically) and edit by hand.
Variables:

| Variable | Used by | Default |
|---|---|---|
| `DB_PATH` | generate, simulate, generate_invoices, clean (`--target rpa`), setup | `../2_Baza_Danych/energosmart_history.db` |
| `OUTPUT_DIR` | simulate, generate_invoices, send, clean | `../3_Dokumenty_Testowe` |
| `NUM_CLIENTS` | generate | `150` |
| `SMTP_*`, `*_EMAIL` | simulate, send_documents, clean | — |
| `IMAP_SERVER`, `IMAP_PORT`, `IMAP_PASSWORD` | clean (`--target gmail`) | auto-detected / `993` / reuses `SENDER_PASSWORD` |

> **`ENERGOSMART_DB_PATH`** is a **Windows environment variable** (not in `.env`),
> set by `setup.py`. The Power Automate Desktop flow (and `healthcheck.ps1`) read
> it so the warehouse path isn't hard-coded into the RPA flow.
>
> Note: dataset volume scales with `NUM_CLIENTS` and the fixed 24-month window
> (≈ 98 readings per client). Increase `NUM_CLIENTS` for a larger database.

## Run

```bat
python generate_history_db.py                 # 1. build DB (warehouse)
python generate_invoices.py --green 5 --yellow 5 --red 2   # 2. generate test documents
```

Or from the repo root: `bat\run_local_pipeline.bat` (builds the DB) then
`bat\generate_invoices.bat` (or the full `demo.bat`)

### Operator tools

```bat
python setup.py                                            # RPA bridge: ODBC driver + ENERGOSMART_DB_PATH
python setup_env.py                                        # configure .env email (wizard)
python generate_invoices.py --green 5 --yellow 3 --red 2   # make typed docs
python send_documents.py --interactive                     # email: pick paths + counts
python send_documents.py --green 3 --yellow all --red 1    # per-path counts (number or "all")
python send_documents.py --green all --dry-run             # preview only
python clean.py                            # dry run: generated files
python clean.py --yes                      # delete generated files
python clean.py --target outlook           # dry run: M365 inbox (Outlook COM)
python clean.py --target gmail --yes       # Gmail test mail -> Trash
python clean.py --target all --yes         # files + outlook + gmail + logs
powershell -ExecutionPolicy Bypass -File healthcheck.ps1   # warehouse health-check
powershell -ExecutionPolicy Bypass -File monitor.ps1       # control panel (history + PAD)
powershell -ExecutionPolicy Bypass -File monitor.ps1 -Watch  # live read-only dashboard
```

Root entry points: **`demo.bat`** (full guided run) and **`monitor.bat`** (control
panel). The individual wrappers live in **`bat\`**: `install.bat`, `setup.bat`,
`setup_env.bat`, `run_local_pipeline.bat`, `generate_invoices.bat`,
`send_documents.bat`, `run_tests.bat`, `healthcheck.bat`, `clean.bat`
(each prompts interactively).

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

- Runtime: `requirements.txt` (pandas, openpyxl, fpdf2, python-dotenv, requests, pywin32)
- Dev: `requirements-dev.txt` (adds pytest, flake8)
