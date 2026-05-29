"""
EnergoSmart - interactive .env setup wizard.

Walks you through configuring 1_Skrypty_Python/.env (mainly the email/SMTP
settings the operator tools need to send test documents). It pre-fills sensible
defaults from any existing .env or from .env.example, infers the SMTP server
from your email domain, hides the password while typing, and can test the SMTP
login before saving.

The RPA bridge's ENERGOSMART_DB_PATH env var is set separately by setup.py.

Usage:
    python setup_env.py              # interactive wizard
    python setup_env.py --test       # also try an SMTP login at the end
"""

import argparse
import shutil
import smtplib
import ssl
from collections import OrderedDict
from getpass import getpass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENV_PATH = HERE / '.env'
EXAMPLE_PATH = HERE / '.env.example'
BACKUP_PATH = HERE / '.env.bak'

# Values shipped in .env.example are placeholders, not real settings.
PLACEHOLDERS = {
    'your-email@gmail.com',
    'your-app-password',
    'your-test-inbox@gmail.com',
}

DEFAULTS = OrderedDict([
    ('SMTP_SERVER', 'smtp.gmail.com'),
    ('SMTP_PORT', '587'),
    ('SENDER_EMAIL', ''),
    ('SENDER_PASSWORD', ''),
    ('RECIPIENT_EMAIL', ''),
    ('DB_PATH', '../2_Baza_Danych/energosmart_history.db'),
    ('NUM_RECORDS', '500000'),
    ('NUM_CLIENTS', '150'),
    ('ANOMALY_THRESHOLD_PERCENT', '30'),
])

PROVIDER_HINTS = {
    'gmail': ('Gmail requires an App Password (with 2-Step Verification on): '
              'https://myaccount.google.com/apppasswords'),
    'outlook': ('Outlook.com may require an App Password: '
                'account.microsoft.com -> Security -> Advanced security.'),
    'office365': ('Microsoft 365 / school accounts: SMTP AUTH must be enabled '
                  'for the mailbox (admin setting) and you usually need an App '
                  'Password if MFA is on.'),
}


def clean(value):
    """Treat example placeholders as 'unset'."""
    value = (value or '').strip()
    if value in PLACEHOLDERS or value.startswith('your-'):
        return ''
    return value


def read_env_file(path):
    """Parse a KEY=VALUE file into an OrderedDict, ignoring comments/blanks."""
    data = OrderedDict()
    if not path.exists():
        return data
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        data[key.strip()] = value.strip()
    return data


def load_current():
    """Merge defaults < .env.example < .env so the newest wins."""
    merged = OrderedDict(DEFAULTS)
    for source in (EXAMPLE_PATH, ENV_PATH):
        for key, value in read_env_file(source).items():
            merged[key] = value
    return merged


def guess_smtp(email):
    """Infer (server, port, provider-key) from the email domain."""
    domain = email.split('@')[-1].lower() if '@' in email else ''
    if domain in ('gmail.com', 'googlemail.com'):
        return 'smtp.gmail.com', '587', 'gmail'
    if domain in ('outlook.com', 'hotmail.com', 'live.com', 'msn.com'):
        return 'smtp-mail.outlook.com', '587', 'outlook'
    if domain:
        # Org / edu mailboxes are overwhelmingly Microsoft 365.
        return 'smtp.office365.com', '587', 'office365'
    return 'smtp.gmail.com', '587', 'gmail'


def ask(prompt, default=''):
    """Prompt with a shown default; Enter keeps it. EOF keeps the default too."""
    suffix = f' [{default}]' if default else ''
    try:
        answer = input(f'{prompt}{suffix}: ').strip()
    except EOFError:
        print()
        return default
    return answer or default


def ask_password(current):
    """Hidden password prompt; blank keeps the existing one if present."""
    keep = ' (Enter to keep current)' if current else ''
    try:
        entered = getpass(f'  SMTP password / app password{keep}: ').strip()
    except EOFError:
        print()
        return current
    return entered or current


def confirm(prompt, default=True):
    suffix = ' (Y/n)' if default else ' (y/N)'
    try:
        answer = input(f'{prompt}{suffix}: ').strip().lower()
    except EOFError:
        print()
        return default
    if not answer:
        return default
    return answer in ('y', 'yes', 't', 'tak')


def test_smtp(cfg):
    """Open a real SMTP session and log in, to validate the settings."""
    server, port = cfg['SMTP_SERVER'], int(cfg['SMTP_PORT'])
    print(f'\n[TEST] Connecting to {server}:{port} ...')
    context = ssl.create_default_context()
    try:
        if port == 465:
            conn = smtplib.SMTP_SSL(server, port, context=context, timeout=20)
        else:
            conn = smtplib.SMTP(server, port, timeout=20)
            conn.starttls(context=context)
        try:
            conn.login(cfg['SENDER_EMAIL'], cfg['SENDER_PASSWORD'])
        finally:
            conn.quit()
    except Exception as exc:
        print(f'[FAIL] SMTP login failed: {exc}')
        return False
    print('[OK] SMTP login succeeded - credentials work.')
    return True


def write_env(cfg):
    """Write a tidy .env, backing up any existing one first."""
    if ENV_PATH.exists():
        shutil.copy2(ENV_PATH, BACKUP_PATH)
        print(f'[OK] Backed up existing .env -> {BACKUP_PATH.name}')

    known = set(DEFAULTS)
    lines = [
        '# Email Configuration (SMTP) - used by send_documents.py',
        f"SMTP_SERVER={cfg['SMTP_SERVER']}",
        f"SMTP_PORT={cfg['SMTP_PORT']}",
        f"SENDER_EMAIL={cfg['SENDER_EMAIL']}",
        f"SENDER_PASSWORD={cfg['SENDER_PASSWORD']}",
        f"RECIPIENT_EMAIL={cfg['RECIPIENT_EMAIL']}",
        '',
        '# Database Configuration',
        f"DB_PATH={cfg['DB_PATH']}",
        '',
        '# Data Generation',
        f"NUM_RECORDS={cfg['NUM_RECORDS']}",
        f"NUM_CLIENTS={cfg['NUM_CLIENTS']}",
        f"ANOMALY_THRESHOLD_PERCENT={cfg['ANOMALY_THRESHOLD_PERCENT']}",
    ]
    extra = [(k, v) for k, v in cfg.items() if k not in known]
    if extra:
        lines.append('')
        lines.append('# Other')
        lines.extend(f'{k}={v}' for k, v in extra)

    ENV_PATH.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'[OK] Wrote {ENV_PATH}')


def run_wizard(do_test):
    cfg = load_current()
    # Only a real, previously-saved .env should override the domain-inferred
    # SMTP server/port (the .env.example ships a non-placeholder gmail server).
    saved = read_env_file(ENV_PATH)

    print('=' * 44)
    print('  EnergoSmart - .env setup wizard')
    print('=' * 44)
    print('Press Enter to keep the value shown in [brackets].\n')

    # 1. Sender email - everything else keys off this.
    sender = ask('Your sending email address', clean(cfg.get('SENDER_EMAIL')))
    cfg['SENDER_EMAIL'] = sender

    # 2. SMTP server/port, inferred from the domain.
    guess_server, guess_port, provider = guess_smtp(sender)
    cur_server = clean(saved.get('SMTP_SERVER')) or guess_server
    cur_port = saved.get('SMTP_PORT') or guess_port
    hint = PROVIDER_HINTS.get(provider)
    if hint:
        print(f'  -> {hint}')
    cfg['SMTP_SERVER'] = ask('  SMTP server', cur_server)
    cfg['SMTP_PORT'] = ask('  SMTP port (587 STARTTLS / 465 SSL)', cur_port)

    # 3. Password (hidden).
    cfg['SENDER_PASSWORD'] = ask_password(clean(cfg.get('SENDER_PASSWORD')))

    # 4. Recipient = the inbox Cloud Flow 1 watches (defaults to sender).
    cur_recipient = clean(cfg.get('RECIPIENT_EMAIL')) or sender
    cfg['RECIPIENT_EMAIL'] = ask(
        'Monitored inbox (where test docs are sent)', cur_recipient)

    # Summary.
    print('\n--- Summary ---')
    print(f"  SMTP_SERVER     = {cfg['SMTP_SERVER']}")
    print(f"  SMTP_PORT       = {cfg['SMTP_PORT']}")
    print(f"  SENDER_EMAIL    = {cfg['SENDER_EMAIL'] or '(not set)'}")
    print(f"  SENDER_PASSWORD = {'********' if cfg['SENDER_PASSWORD'] else '(not set)'}")
    print(f"  RECIPIENT_EMAIL = {cfg['RECIPIENT_EMAIL'] or '(not set)'}")

    missing = [k for k in ('SENDER_EMAIL', 'SENDER_PASSWORD', 'RECIPIENT_EMAIL')
               if not cfg[k]]
    if missing:
        print('  [WARN] Still empty: ' + ', '.join(missing) +
              ' - sending will not work until these are set.')

    if not confirm('\nSave these settings to .env?', default=True):
        print('[ABORT] Nothing written.')
        return 1

    write_env(cfg)

    if (do_test or confirm('Test the SMTP login now?', default=False)):
        if missing:
            print('[SKIP] Cannot test - email/password not fully set.')
        else:
            test_smtp(cfg)

    print('\nNext: python send_documents.py --type all --count 1 --dry-run')
    return 0


def parse_args():
    parser = argparse.ArgumentParser(
        description='Interactive .env setup wizard for EnergoSmart.')
    parser.add_argument('--test', action='store_true',
                        help='test the SMTP login after saving')
    return parser.parse_args()


def main():
    args = parse_args()
    return run_wizard(args.test)


if __name__ == '__main__':
    raise SystemExit(main())
