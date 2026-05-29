"""
EnergoSmart - guided end-to-end demo runner.

One script that walks through the whole local pipeline in order and asks before
each step, so you can drive a full test run (data -> documents -> email -> cloud
-> warehouse check) without remembering every command. Each step is optional:
answer Y to run it, n to skip, or q to quit.

Steps:
  1. RPA-bridge setup     (setup.py)            - SQLite ODBC driver + DB env var
  2. Email / SMTP config  (setup_env.py)        - .env wizard
  3. Build history DB     (generate_history_db.py)
  4. Generate documents   (generate_invoices.py / simulate_clients.py)
  5. Send documents       (send_documents.py --interactive)
  6. -- cloud runs: Flow 1 -> AI -> Dataverse -> review -> Flow 2 -> PAD --
  7. Warehouse health-check (healthcheck.ps1)   - confirm RPA-synced rows
  8. Clean up             (clean.py)            - optional

Usage:
    python run_demo.py        (or double-click run_demo.bat from the repo root)
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def banner(text):
    line = '=' * 60
    print(f'\n{line}\n  {text}\n{line}')


def ask(question, default=True):
    """Return True/False, or raise SystemExit on 'q'. Enter keeps the default."""
    suffix = ' [Y/n/q]' if default else ' [y/N/q]'
    try:
        answer = input(f'{question}{suffix} ').strip().lower()
    except EOFError:
        print()
        return default
    if answer in ('q', 'quit', 'exit'):
        print('\n[QUIT] Stopping the demo runner.')
        raise SystemExit(0)
    if not answer:
        return default
    return answer in ('y', 'yes', 't', 'tak')


def prompt(text, default=''):
    suffix = f' [{default}]' if default else ''
    try:
        answer = input(f'{text}{suffix}: ').strip()
    except EOFError:
        print()
        return default
    return answer or default


def run_py(script, *args):
    """Run a sibling python script in 1_Skrypty_Python and return its exit code."""
    rc = subprocess.call([PY, str(HERE / script), *map(str, args)], cwd=str(HERE))
    if rc != 0:
        print(f'[WARN] {script} exited with code {rc}.')
    return rc


def run_ps(script, *args):
    """Run a PowerShell script in 1_Skrypty_Python and return its exit code."""
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
           '-File', str(HERE / script), *map(str, args)]
    try:
        return subprocess.call(cmd, cwd=str(HERE))
    except FileNotFoundError:
        print('[WARN] PowerShell not found - skipping health-check.')
        return 1


def step_setup():
    if not ask('STEP 1/8  Set up the RPA bridge (SQLite ODBC driver + '
               'ENERGOSMART_DB_PATH)?', default=False):
        return
    run_py('setup.py')


def step_env():
    if not ask('STEP 2/8  Configure email / SMTP (.env wizard)?', default=False):
        return
    run_py('setup_env.py')


def step_build_db():
    if not ask('STEP 3/8  Build the SQLite history database?', default=True):
        return
    run_py('generate_history_db.py')


def step_generate():
    if not ask('STEP 4/8  Generate test documents?', default=True):
        return
    kind = prompt('   Which? typed Green/Yellow/Red (t) or pipeline readings (p)',
                  't').lower()
    if kind.startswith('p'):
        run_py('simulate_clients.py')
        return
    green = prompt('   How many GREEN (auto-accept)', '3')
    yellow = prompt('   How many YELLOW (review)', '2')
    red = prompt('   How many RED (reject)', '1')
    run_py('generate_invoices.py', '--green', green, '--yellow', yellow,
           '--red', red)


def step_send():
    if not ask('STEP 5/8  Email the documents to the monitored inbox?',
               default=True):
        return
    run_py('send_documents.py', '--interactive')


def step_cloud_pause():
    banner('STEP 6/8  Cloud processing (manual)')
    print('Now the cloud side runs on its own:')
    print('  Email -> Flow 1 -> AI Builder -> Dataverse (status)')
    print('        -> Power Apps review (Yellow) / auto-accept (Green)')
    print('        -> Flow 2 (Added or Modified, Status=Accepted)')
    print('        -> Power Automate Desktop -> local SQLite (Synced)')
    print('Keep Power Automate Desktop open for attended runs.')
    try:
        input('\nPress Enter once a reading has been Accepted & synced ...')
    except EOFError:
        print()


def step_healthcheck():
    if not ask('STEP 7/8  Run the warehouse health-check (verify synced rows)?',
               default=True):
        return
    run_ps('healthcheck.ps1')


def step_clean():
    if not ask('STEP 8/8  Clean up generated test files now?', default=False):
        return
    run_py('clean.py')                       # dry run first (lists files)
    if ask('   Delete the files listed above?', default=False):
        run_py('clean.py', '--yes')


def main():
    banner('EnergoSmart - guided demo runner')
    print('Answer Y to run a step, n to skip, q to quit at any prompt.')
    for step in (step_setup, step_env, step_build_db, step_generate,
                 step_send, step_cloud_pause, step_healthcheck, step_clean):
        step()
    banner('Demo run finished')
    print('Tip: re-run any single piece via its own .bat in the repo root.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
