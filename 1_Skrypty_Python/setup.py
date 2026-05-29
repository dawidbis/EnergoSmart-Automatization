"""
EnergoSmart - one-time machine setup for the RPA bridge (Windows).

The Power Automate Desktop -> local SQLite bridge needs two things on this
machine, both handled here (this replaces the old setup_odbc.py):

  1. The "SQLite3 ODBC Driver" (Ch. Werner) registered (64-bit). If missing,
     it's downloaded and installed silently with elevation - accept the UAC
     prompt (a system ODBC driver writes to HKLM, so admin rights are required).
  2. The ENERGOSMART_DB_PATH environment variable, pointing at the warehouse
     (resolved from DB_PATH in .env). The PAD desktop flow reads it via a
     "Get Windows environment variable" action, so the .db path isn't
     hard-coded into the flow.

install.bat runs this automatically. The .env email/SMTP wizard is separate
(setup_env.py).

Usage:
    python setup.py               # ensure driver + set ENERGOSMART_DB_PATH
    python setup.py --check-only  # report driver status only (no install / no env var)
"""

import argparse
import subprocess
import tempfile
import urllib.request
import winreg
from pathlib import Path

HERE = Path(__file__).resolve().parent

DRIVER_NAME = 'SQLite3 ODBC Driver'
INSTALLER_URL = 'http://www.ch-werner.de/sqliteodbc/sqliteodbc_w64.exe'
DRIVERS_KEY = r'SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers'

DB_PATH_ENV_VAR = 'ENERGOSMART_DB_PATH'
DEFAULT_DB_PATH = '../2_Baza_Danych/energosmart_history.db'


# --------------------------------------------------------------------------- #
# ENERGOSMART_DB_PATH env var (read by the PAD desktop flow)
# --------------------------------------------------------------------------- #
def read_db_path():
    """DB_PATH from .env (relative), or the default."""
    env = HERE / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('DB_PATH=') and '=' in line:
                val = line.split('=', 1)[1].strip()
                if val and not val.startswith('your-'):
                    return val
    return DEFAULT_DB_PATH


def set_db_path_env_var():
    """Persist ENERGOSMART_DB_PATH (user scope) as an absolute path."""
    abs_path = str((HERE / read_db_path()).resolve())
    try:
        result = subprocess.run(['setx', DB_PATH_ENV_VAR, abs_path],
                                capture_output=True, text=True)
    except OSError as exc:
        print(f'[WARN] could not set {DB_PATH_ENV_VAR}: {exc}')
        return False
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        print(f'[WARN] setx failed: {detail}')
        return False
    print(f'[OK] {DB_PATH_ENV_VAR} = {abs_path}')
    print('     (restart Power Automate Desktop so it picks up the new value)')
    return True


# --------------------------------------------------------------------------- #
# SQLite ODBC driver
# --------------------------------------------------------------------------- #
def driver_installed(name=DRIVER_NAME):
    """True if the named ODBC driver is registered in the 64-bit view."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, DRIVERS_KEY, 0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    except FileNotFoundError:
        return False
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value).strip().lower() == 'installed'
    except FileNotFoundError:
        return False
    finally:
        winreg.CloseKey(key)


def download_installer(dest):
    req = urllib.request.Request(
        INSTALLER_URL, headers={'User-Agent': 'EnergoSmart-setup/1.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    Path(dest).write_bytes(data)
    return len(data)


def install_silent(exe):
    """Run the installer silently and elevated (UAC), waiting for it to finish."""
    ps = (
        "try { Start-Process -FilePath '%s' -ArgumentList '/S' "
        "-Verb RunAs -Wait -PassThru | Out-Null; exit 0 } "
        "catch { Write-Error $_; exit 5 }" % exe
    )
    result = subprocess.run(
        ['powershell', '-NoProfile', '-NonInteractive', '-Command', ps],
        capture_output=True, text=True)
    if result.returncode != 0 and result.stderr:
        print('   ' + result.stderr.strip().splitlines()[-1])
    return result.returncode


def ensure_driver(check_only):
    if driver_installed():
        print(f'[OK] "{DRIVER_NAME}" is already installed.')
        return 0
    print(f'[MISSING] "{DRIVER_NAME}" is not registered (64-bit).')
    if check_only:
        print(f'   Install it from: {INSTALLER_URL}')
        return 1
    exe = Path(tempfile.gettempdir()) / 'sqliteodbc_w64.exe'
    print(f'[..] Downloading installer from {INSTALLER_URL} ...')
    try:
        size = download_installer(exe)
    except Exception as exc:
        print(f'[ERROR] Download failed: {exc}')
        print(f'   Install manually from: {INSTALLER_URL}')
        return 1
    if size < 500_000:
        print(f'[ERROR] Downloaded file looks too small ({size} bytes).')
        return 1
    print(f'[OK] Downloaded {size:,} bytes -> {exe}')
    print('[..] Running the installer (accept the UAC prompt) ...')
    install_silent(str(exe))
    try:
        exe.unlink()
    except OSError:
        pass
    if driver_installed():
        print(f'[OK] "{DRIVER_NAME}" installed successfully.')
        return 0
    print('[ERROR] Driver still not detected after install.')
    print(f'   Install manually from: {INSTALLER_URL}')
    return 1


def main():
    parser = argparse.ArgumentParser(
        description='Set up the RPA bridge: SQLite ODBC driver + DB path env var.')
    parser.add_argument('--check-only', action='store_true',
                        help='only report driver status (no install, no env var)')
    args = parser.parse_args()

    rc = ensure_driver(args.check_only)
    if not args.check_only:
        print()
        set_db_path_env_var()
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
