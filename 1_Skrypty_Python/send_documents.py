"""
EnergoSmart - Test-document sender.

Emails prepared documents from OUTPUT_DIR (3_Dokumenty_Testowe/) to the
monitored inbox so they flow into Cloud Flow 1 (Email Processor).

Two sources of PDFs are recognised and sorted into the three Cloud-Flow paths:
  * typed docs from generate_invoices.py  -> GREEN_* / YELLOW_* / RED_*
  * pipeline docs from simulate_clients.py -> CLIENT_*_MeterReading_*.pdf
    (valid readings -> counted as the GREEN / auto-accept path)
  * legacy bad reports                     -> BAD_*  (RED / reject path)

You can send several / one / all paths at once, and for each chosen path send a
specific number of documents or "all" of them.

SMTP settings come from .env:
    SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL

Usage:
    python send_documents.py --interactive            # guided prompts
    python send_documents.py --green 3 --yellow all   # per-path counts
    python send_documents.py --green all --red 2 --dry-run
    python send_documents.py --type all --count 1     # legacy: 1 per path
    python send_documents.py --type yellow --count 2
"""

import argparse
import mimetypes
import os
import random
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')
SMTP_SERVER = os.getenv('SMTP_SERVER', '')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
RECIPIENT_EMAIL = os.getenv('RECIPIENT_EMAIL', '')

PATHS = ('green', 'yellow', 'red')


def classify(name):
    """Map a PDF filename to a Cloud-Flow path, or None if not sendable.

    GREEN  = valid readings the AI should auto-accept: typed GREEN_* docs and
             the pipeline's CLIENT_*_MeterReading_*.pdf meter readings.
    YELLOW = typed review-path docs (zero / spike / drop).
    RED    = reject-path docs: typed RED_* and legacy BAD_* reports.
    """
    upper = name.upper()
    if upper.startswith('GREEN_'):
        return 'green'
    if upper.startswith('YELLOW_'):
        return 'yellow'
    if upper.startswith('RED_') or upper.startswith('BAD_'):
        return 'red'
    if '_METERREADING_' in upper:          # pipeline meter readings = valid
        return 'green'
    return None                            # .xlsx reports / unknown -> skip


def scan(output_dir):
    """Group every classifiable PDF in OUTPUT_DIR into {path: [Path, ...]}."""
    buckets = {p: [] for p in PATHS}
    base = Path(output_dir)
    if base.exists():
        for fp in sorted(base.glob('*.pdf')):
            path = classify(fp.name)
            if path:
                buckets[path].append(fp)
    return buckets


def pick(files, count):
    """Choose `count` files (or all of them if count == 'all' or too few)."""
    if count == 'all' or count >= len(files):
        return list(files)
    return sorted(random.sample(files, count))


def select(buckets, spec):
    """Build {path: [chosen files]} from a {path: count_or_'all'} spec."""
    chosen = {}
    for path, count in spec.items():
        files = pick(buckets.get(path, []), count)
        if files:
            chosen[path] = files
    return chosen


def build_message(file_path, subject_prefix):
    """Build an email with the document attached."""
    msg = EmailMessage()
    msg['Subject'] = f'{subject_prefix}: {file_path.name}'
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content(
        'Automated EnergoSmart test submission.\n'
        f'Attached document: {file_path.name}\n'
    )
    ctype, _ = mimetypes.guess_type(str(file_path))
    maintype, subtype = (ctype or 'application/octet-stream').split('/', 1)
    with open(file_path, 'rb') as handle:
        msg.add_attachment(handle.read(), maintype=maintype, subtype=subtype,
                           filename=file_path.name)
    return msg


def send_all(files, subject_prefix, delay):
    """Open one SMTP session and send each document, with progress + delay."""
    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
    else:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls(context=context)
    sent = 0
    try:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        total = len(files)
        for i, file_path in enumerate(files, 1):
            server.send_message(build_message(file_path, subject_prefix))
            sent += 1
            print(f'  [SENT {i}/{total}] {file_path.name}')
            if delay and i < total:
                time.sleep(delay)
    finally:
        server.quit()
    return sent


def missing_config():
    """Return the list of required SMTP settings that are not set."""
    required = {
        'SMTP_SERVER': SMTP_SERVER,
        'SENDER_EMAIL': SENDER_EMAIL,
        'SENDER_PASSWORD': SENDER_PASSWORD,
        'RECIPIENT_EMAIL': RECIPIENT_EMAIL,
    }
    return [name for name, value in required.items() if not value]


# --------------------------------------------------------------------------- #
# CLI parsing + interactive mode
# --------------------------------------------------------------------------- #
def count_value(raw):
    """argparse type: a non-negative int, or the literal "all"."""
    text = str(raw).strip().lower()
    if text in ('all', '*'):
        return 'all'
    try:
        number = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'expected a number or "all", got "{raw}"')
    if number < 0:
        raise argparse.ArgumentTypeError('count must be >= 0 or "all"')
    return number


def resolve_spec(args):
    """Turn CLI args into a {path: count_or_'all'} spec.

    Per-path flags (--green/--yellow/--red) win; otherwise fall back to the
    legacy --type/--count pair (--type all => that count for every path).
    """
    per_path = {p: getattr(args, p) for p in PATHS if getattr(args, p) is not None}
    if per_path:
        return per_path
    if args.type == 'all':
        return {p: args.count for p in PATHS}
    return {args.type: args.count}


def prompt(text, default=''):
    suffix = f' [{default}]' if default else ''
    try:
        answer = input(f'{text}{suffix}: ').strip()
    except EOFError:
        print()
        return default
    return answer or default


def interactive(buckets):
    """Ask which paths and how many of each, plus delay / dry-run."""
    print('Available documents in', OUTPUT_DIR)
    for path in PATHS:
        print(f'   {path.upper():<7} {len(buckets[path])}')
    print()

    raw = prompt('Paths to send (green/yellow/red, comma-separated, or "all")',
                 'all')
    tokens = [t.strip().lower() for t in raw.replace(',', ' ').split()]
    if 'all' in tokens or not tokens:
        selected = [p for p in PATHS if buckets[p]]
    else:
        selected = [p for p in PATHS if p in tokens and buckets[p]]
    if not selected:
        return None, 0.0, False

    spec = {}
    for path in selected:
        available = len(buckets[path])
        raw_count = prompt(f'  How many {path.upper()}? (number or "all", '
                           f'available {available})', 'all')
        spec[path] = count_value(raw_count)

    delay = float(prompt('Delay between emails (seconds)', '0') or 0)
    dry = prompt('Dry run (list only, do NOT send)? (y/N)', 'n').lower() \
        in ('y', 'yes', 't', 'tak')
    return spec, delay, dry


def parse_args():
    parser = argparse.ArgumentParser(
        description='Email prepared EnergoSmart test documents.')
    parser.add_argument('--interactive', action='store_true',
                        help='guided prompts (which paths, how many of each)')
    parser.add_argument('--green', type=count_value, default=None,
                        help='how many GREEN docs to send (number or "all")')
    parser.add_argument('--yellow', type=count_value, default=None,
                        help='how many YELLOW docs to send (number or "all")')
    parser.add_argument('--red', type=count_value, default=None,
                        help='how many RED docs to send (number or "all")')
    parser.add_argument('--type', choices=['green', 'yellow', 'red', 'all'],
                        default='all', help='[legacy] single path (or all)')
    parser.add_argument('--count', type=count_value, default=1,
                        help='[legacy] how many per path (number or "all")')
    parser.add_argument('--delay', type=float, default=0.0,
                        help='seconds to wait between emails')
    parser.add_argument('--subject-prefix', default='EnergoSmart Reading',
                        help='email subject prefix')
    parser.add_argument('--dry-run', action='store_true',
                        help='list what would be sent, do not connect to SMTP')
    return parser.parse_args()


def main():
    args = parse_args()
    buckets = scan(OUTPUT_DIR)

    if args.interactive:
        spec, delay, dry_run = interactive(buckets)
        subject_prefix = args.subject_prefix
    else:
        spec = resolve_spec(args)
        delay, dry_run, subject_prefix = args.delay, args.dry_run, args.subject_prefix

    chosen = select(buckets, spec) if spec else {}
    flat = [fp for path in PATHS if path in chosen for fp in chosen[path]]
    if not flat:
        print(f'[ERROR] No matching documents found in {OUTPUT_DIR}.')
        print('   Generate some first:')
        print('     python generate_invoices.py --green 5 --yellow 3 --red 2')
        print('     python simulate_clients.py   (pipeline meter readings)')
        return 1

    print(f'\n[PLAN] {len(flat)} document(s) '
          f'-> {RECIPIENT_EMAIL or "(recipient not set)"}')
    for path in PATHS:
        if path in chosen:
            print(f'   {path.upper():<7} ({len(chosen[path])}):')
            for fp in chosen[path]:
                print(f'      - {fp.name}')

    if dry_run:
        print('\n[DRY-RUN] Nothing sent. Remove --dry-run to send for real.')
        return 0

    missing = missing_config()
    if missing:
        print('\n[ERROR] Missing SMTP settings in .env: ' + ', '.join(missing))
        print('   Run setup_env.bat (or edit 1_Skrypty_Python\\.env).')
        return 1

    print(f'\n[SEND] Connecting to {SMTP_SERVER}:{SMTP_PORT} ...')
    try:
        sent = send_all(flat, subject_prefix, delay)
    except Exception as exc:
        print(f'[ERROR] Sending failed: {exc}')
        return 1
    print(f'\n[OK] Sent {sent}/{len(flat)} document(s) to {RECIPIENT_EMAIL}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
