# 1 - Python Data Engineering Layer

Generates the simulated "billing system" history and the client reports that feed
the cloud pipeline.

## Scripts

| Script | Purpose |
|---|---|
| `generate_history_db.py` | Builds the SQLite history DB: 150 business clients across 7 sectors, 24 months of weekly readings (~14.7k rows), with sector-realistic baselines, seasonal variation and flagged anomalies. |
| `simulate_clients.py` | Reads the DB and produces per-client **Excel** and **PDF** reports into `3_Dokumenty_Testowe/`, randomly injecting consumption anomalies (spike / drop / noise) to exercise the AI + review paths. |

## Configuration (`.env`)

Copy `.env.example` → `.env` (install.bat does this automatically). Variables:

| Variable | Used by | Default |
|---|---|---|
| `DB_PATH` | both | `../2_Baza_Danych/energosmart_history.db` |
| `OUTPUT_DIR` | simulate | `../3_Dokumenty_Testowe` |
| `NUM_CLIENTS` | generate | `150` |
| `SMTP_*`, `*_EMAIL` | simulate (email send) | — |

> Note: dataset volume scales with `NUM_CLIENTS` and the fixed 24-month window
> (≈ 98 readings per client). Increase `NUM_CLIENTS` for a larger database.

## Run

```bat
python generate_history_db.py   # 1. build DB
python simulate_clients.py      # 2. build reports
```

Or from the repo root: `run_local_pipeline.bat`

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
