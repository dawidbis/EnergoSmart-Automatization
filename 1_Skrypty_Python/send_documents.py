"""
EnergoSmart - Test-document sender.

Emails prepared documents from OUTPUT_DIR (3_Dokumenty_Testowe/) to the
monitored inbox so they flow into Cloud Flow 1 (Email Processor). You choose
how many and which path type to send, plus a few options.

SMTP settings come from .env:
    SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL

Usage:
    python send_documents.py --type green --count 3
    python send_documents.py --type all --count 5 --delay 2
    python send_documents.py --type red --count 1 --dry-run
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

PREFIXES = {'green': 'GREEN_', 'yellow': 'YELLOW_', 'red': 'RED_'}


def select_files(path_type, count):
    """Pick up to `count` PDFs of the requested path type from OUTPUT_DIR."""
    base = Path(OUTPUT_DIR)
    if not base.exists():
        return []
    if path_type == 'all':
        prefixes = tuple(PREFIXES.values())
    else:
        prefixes = (PREFIXES[path_type],)
    files = sorted(f for f in base.glob('*.pdf') if f.name.startswith(prefixes))
    if count >= len(files):
        return files
    return sorted(random.sample(files, count))


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


def parse_args():
    parser = argparse.ArgumentParser(
        description='Email prepared EnergoSmart test documents.')
    parser.add_argument('--type', choices=['green', 'yellow', 'red', 'all'],
                        default='all', help='which path type to send')
    parser.add_argument('--count', type=int, default=1, help='how many to send')
    parser.add_argument('--delay', type=float, default=0.0,
                        help='seconds to wait between emails')
    parser.add_argument('--subject-prefix', default='EnergoSmart Reading',
                        help='email subject prefix')
    parser.add_argument('--dry-run', action='store_true',
                        help='list what would be sent, do not connect to SMTP')
    return parser.parse_args()


def main():
    args = parse_args()
    files = select_files(args.type, args.count)
    if not files:
        print(f'[ERROR] No {args.type.upper()} documents found in {OUTPUT_DIR}.')
        print('   Generate some first: python generate_invoices.py --each 3')
        return 1

    print(f'[PLAN] {len(files)} document(s) of type "{args.type}" '
          f'-> {RECIPIENT_EMAIL or "(recipient not set)"}')
    for file_path in files:
        print(f'   - {file_path.name}')

    if args.dry_run:
        print('\n[DRY-RUN] Nothing sent. Remove --dry-run to send for real.')
        return 0

    missing = missing_config()
    if missing:
        print('\n[ERROR] Missing SMTP settings in .env: ' + ', '.join(missing))
        print('   Edit 1_Skrypty_Python\\.env (see .env.example).')
        return 1

    print(f'\n[SEND] Connecting to {SMTP_SERVER}:{SMTP_PORT} ...')
    try:
        sent = send_all(files, args.subject_prefix, args.delay)
    except Exception as exc:
        print(f'[ERROR] Sending failed: {exc}')
        return 1
    print(f'\n[OK] Sent {sent}/{len(files)} document(s) to {RECIPIENT_EMAIL}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
