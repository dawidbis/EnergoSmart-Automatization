"""
EnergoSmart - clean test artifacts: local files and/or project emails.

One tool for all post-test cleanup (replaces the old clean_test_documents.py +
clean_outlook.py + clean_gmail.py):

  files   - generated reports/invoices (*.pdf, *.xlsx) in OUTPUT_DIR.
  outlook - test emails in the monitored Microsoft 365 inbox, via the local
            classic Outlook app (COM). M365 blocks basic-auth IMAP, so we drive
            the already-signed-in Outlook desktop instead. Needs pywin32 +
            classic Outlook with the account added.
  gmail   - test emails the Gmail sender accumulated (Sent + the rejection
            emails bounced back to Inbox), via IMAP + App Password. Matches are
            moved to Trash (recoverable ~30 days).
  all     - files + outlook + gmail.

Dry run by default; pass --yes to actually delete.

Usage:
    python clean.py                          # dry run, files
    python clean.py --yes                     # delete generated files
    python clean.py --target outlook          # dry run, M365 inbox (Outlook COM)
    python clean.py --target gmail --yes      # move Gmail test mail to Trash
    python clean.py --target all --yes        # everything
"""

import argparse
import imaplib
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / '.env')
except Exception:
    pass

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')
PREFIXES = {'green': 'GREEN_', 'yellow': 'YELLOW_', 'red': 'RED_'}
DEFAULT_SUBJECT = 'EnergoSmart'

OL_FOLDER_INBOX = 6   # olFolderInbox
OL_MAIL_ITEM = 43     # olMail


def cfg(name):
    """Read an .env value, treating example placeholders as unset."""
    value = (os.getenv(name) or '').strip()
    return '' if value.startswith('your-') else value


# --------------------------------------------------------------------------- #
# files
# --------------------------------------------------------------------------- #
def clean_files(path_type, do_delete):
    base = Path(OUTPUT_DIR)
    targets = []
    if base.exists():
        for fp in sorted(base.iterdir()):
            if not fp.is_file() or fp.suffix.lower() not in ('.pdf', '.xlsx'):
                continue
            if path_type != 'all' and not fp.name.startswith(PREFIXES[path_type]):
                continue
            targets.append(fp)
    if not targets:
        print(f'[FILES] nothing to clean in {OUTPUT_DIR} (type={path_type}).')
        return 0
    print(f'[FILES] {len(targets)} file(s) in {OUTPUT_DIR} (type={path_type}):')
    for fp in targets:
        print(f'   - {fp.name}')
    if not do_delete:
        print('[DRY-RUN] no files deleted (use --yes).')
        return 0
    deleted = 0
    for fp in targets:
        try:
            fp.unlink()
            deleted += 1
        except OSError as exc:
            print(f'   [warn] {fp.name}: {exc}')
    print(f'[OK] deleted {deleted}/{len(targets)} file(s).')
    return 0


# --------------------------------------------------------------------------- #
# outlook (Microsoft 365 inbox via classic Outlook COM)
# --------------------------------------------------------------------------- #
def clean_outlook(subject_kw, do_delete):
    try:
        import win32com.client
    except ImportError:
        print('[OUTLOOK] pywin32 not installed (pip install pywin32) - skipping.')
        return 1
    account = cfg('RECIPIENT_EMAIL')
    try:
        ns = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    except Exception as exc:
        print(f'[OUTLOOK] cannot open Outlook (classic Outlook installed?): {exc}')
        return 1
    inbox = None
    if account:
        for store in ns.Stores:
            if account.lower() in (getattr(store, 'DisplayName', '') or '').lower():
                try:
                    inbox = store.GetDefaultFolder(OL_FOLDER_INBOX)
                    break
                except Exception:
                    pass
    if inbox is None:
        inbox = ns.GetDefaultFolder(OL_FOLDER_INBOX)
    try:
        mailbox = inbox.Parent.Name
    except Exception:
        mailbox = '(unknown)'
    print(f"[OUTLOOK] mailbox: {mailbox}   subject~'{subject_kw}'")
    found = []
    for item in inbox.Items:
        try:
            if getattr(item, 'Class', None) != OL_MAIL_ITEM:
                continue
            if subject_kw.lower() in (getattr(item, 'Subject', '') or '').lower():
                found.append(item)
        except Exception:
            continue
    if not found:
        print('[OUTLOOK] nothing matched.')
        return 0
    print(f'[OUTLOOK] {len(found)} message(s):')
    for it in found[:30]:
        try:
            print(f'   - {it.ReceivedTime}  {it.Subject}')
        except Exception:
            print('   - (unreadable item)')
    if len(found) > 30:
        print(f'   ... and {len(found) - 30} more')
    if not do_delete:
        print('[DRY-RUN] nothing deleted (use --yes).')
        return 0
    deleted = 0
    for it in found:
        try:
            it.Delete()
            deleted += 1
        except Exception as exc:
            print(f'   [skip] {exc}')
    print(f'[OK] deleted {deleted} message(s) -> Deleted Items.')
    return 0


# --------------------------------------------------------------------------- #
# gmail (sender mailbox via IMAP + App Password)
# --------------------------------------------------------------------------- #
def _find_special(conn, flag):
    """Find a folder by IMAP special-use flag, e.g. '\\All' (locale-proof)."""
    typ, folders = conn.list()
    if typ != 'OK':
        return None
    for raw in folders:
        line = raw.decode(errors='replace')
        if flag.lower() in line.lower():
            match = re.search(r'"/"\s+(.+)$', line)
            if match:
                return match.group(1).strip()
    return None


def clean_gmail(subject_kw, do_delete):
    user = cfg('SENDER_EMAIL')
    pw = cfg('IMAP_PASSWORD') or cfg('SENDER_PASSWORD')
    server = cfg('IMAP_SERVER') or 'imap.gmail.com'
    if not user or not pw:
        print('[GMAIL] need SENDER_EMAIL + SENDER_PASSWORD (App Password) in .env.')
        return 1
    print(f"[GMAIL] {user} via {server}:993   subject~'{subject_kw}'")
    try:
        conn = imaplib.IMAP4_SSL(server, 993)
        conn.login(user, pw)
    except Exception as exc:
        print(f'[GMAIL] IMAP login failed: {exc}')
        print('        Gmail needs an App Password and IMAP enabled.')
        return 1
    all_mail = _find_special(conn, '\\All') or '"[Gmail]/All Mail"'
    conn.select(all_mail)
    typ, data = conn.search(None, 'SUBJECT', subject_kw)
    ids = data[0].split() if (typ == 'OK' and data and data[0]) else []
    print(f'[GMAIL] {len(ids)} message(s) in All Mail.')
    if not ids:
        conn.logout()
        return 0
    if not do_delete:
        print('[DRY-RUN] nothing changed (use --yes).')
        conn.logout()
        return 0
    moved = 0
    for num in ids:
        try:
            conn.store(num, '+X-GM-LABELS', '\\Trash')
            moved += 1
        except Exception as exc:
            print(f'   [skip] {exc}')
    print(f'[OK] moved {moved} message(s) to Trash (recoverable ~30 days).')
    conn.logout()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Clean EnergoSmart test artifacts (files / outlook / gmail).')
    parser.add_argument('--target', choices=['files', 'outlook', 'gmail', 'all'],
                        default='files', help='what to clean (default: files)')
    parser.add_argument('--type', choices=['green', 'yellow', 'red', 'all'],
                        default='all', help='[files] limit to one path type')
    parser.add_argument('--subject', default=DEFAULT_SUBJECT,
                        help='[email] subject filter (default: EnergoSmart)')
    parser.add_argument('--yes', action='store_true',
                        help='actually delete (default: dry run)')
    args = parser.parse_args()

    rc = 0
    if args.target in ('files', 'all'):
        rc |= clean_files(args.type, args.yes)
    if args.target in ('outlook', 'all'):
        print()
        rc |= clean_outlook(args.subject, args.yes)
    if args.target in ('gmail', 'all'):
        print()
        rc |= clean_gmail(args.subject, args.yes)
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
