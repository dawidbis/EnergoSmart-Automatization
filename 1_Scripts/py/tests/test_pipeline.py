"""
Integration + unit tests for the EnergoSmart local data layer.

Integration tests run the real scripts as subprocesses against a temporary
database / output directory, so they validate the actual Plug & Play entry
points (the same commands install.bat / build_database.bat invoke).
"""

import os
import sys
import sqlite3
import subprocess
import importlib
from pathlib import Path

import pytest

# 1_Scripts directory (parent of this tests/ folder)
SCRIPT_DIR = Path(__file__).resolve().parent.parent

EXPECTED_COLUMNS = {
    "client_id", "client_name", "sector", "reading_date",
    "consumption_kwh", "month_avg_kwh", "anomaly_flag", "status",
}


def _run_script(name, env, cwd=SCRIPT_DIR):
    return subprocess.run(
        [sys.executable, name],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


# --------------------------------------------------------------------------
# Integration tests (subprocess - real entry points)
# --------------------------------------------------------------------------

def test_generate_db_creates_valid_schema(tmp_path):
    """generate_history_db.py builds a SQLite DB with the expected schema + rows."""
    db_file = tmp_path / "test_history.db"
    env = os.environ.copy()
    env["DB_PATH"] = str(db_file)
    env["NUM_CLIENTS"] = "5"

    result = _run_script("generate_history_db.py", env)
    assert result.returncode == 0, result.stderr

    assert db_file.exists(), "Database file was not created"

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='energosmart_history'"
    )
    assert cur.fetchone() is not None, "energosmart_history table missing"

    cur.execute("PRAGMA table_info(energosmart_history)")
    columns = {row[1] for row in cur.fetchall()}
    assert EXPECTED_COLUMNS.issubset(columns), f"Missing columns: {EXPECTED_COLUMNS - columns}"

    cur.execute("SELECT COUNT(*) FROM energosmart_history")
    assert cur.fetchone()[0] > 0, "No rows inserted"

    conn.close()


def test_simulate_creates_documents(tmp_path):
    """simulate_clients.py reads the DB and produces Excel/PDF reports."""
    db_file = tmp_path / "test_history.db"
    out_dir = tmp_path / "docs"
    env = os.environ.copy()
    env["DB_PATH"] = str(db_file)
    env["OUTPUT_DIR"] = str(out_dir)
    env["NUM_CLIENTS"] = "5"

    gen = _run_script("generate_history_db.py", env)
    assert gen.returncode == 0, gen.stderr

    sim = _run_script("simulate_clients.py", env)
    assert sim.returncode == 0, sim.stderr

    files = list(out_dir.glob("*"))
    assert any(f.suffix in (".pdf", ".xlsx") for f in files), "No report documents generated"


def test_simulate_fails_without_database(tmp_path):
    """simulate_clients.py should exit non-zero if the DB is missing."""
    env = os.environ.copy()
    env["DB_PATH"] = str(tmp_path / "does_not_exist.db")
    env["OUTPUT_DIR"] = str(tmp_path / "docs")

    sim = _run_script("simulate_clients.py", env)
    assert sim.returncode != 0, "Expected non-zero exit when DB is missing"


# --------------------------------------------------------------------------
# Unit tests (direct import of pure helpers)
# --------------------------------------------------------------------------

def test_generate_consumption_is_positive():
    sys.path.insert(0, str(SCRIPT_DIR))
    mod = importlib.import_module("generate_history_db")
    # tight variance keeps the gaussian noise well above zero
    for _ in range(100):
        assert mod.generate_consumption(1000, 0.01) > 0


def test_generate_clients_profiles(monkeypatch):
    monkeypatch.setenv("NUM_CLIENTS", "4")
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.modules.pop("generate_history_db", None)  # force re-read of env global
    mod = importlib.import_module("generate_history_db")

    clients = mod.generate_clients()
    assert len(clients) == 4
    required = {"id", "name", "sector", "baseline", "variance"}
    assert required <= set(clients[0].keys())
    assert clients[0]["sector"] in mod.SECTOR_TEMPLATES
