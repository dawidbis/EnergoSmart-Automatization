"""
EnergoSmart - Clean generated test documents.

Removes generated reports / invoices (*.pdf, *.xlsx) from OUTPUT_DIR
(3_Dokumenty_Testowe/). Source code and the database are never touched.

By default this is a DRY RUN (it only lists what would be deleted). Pass --yes
to actually delete. The clean_test_data.bat wrapper asks for confirmation and
then calls this with --yes.

Usage:
    python clean_test_documents.py            # dry run (list only)
    python clean_test_documents.py --yes      # delete all generated docs
    python clean_test_documents.py --type red --yes
"""

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')
PREFIXES = {'green': 'GREEN_', 'yellow': 'YELLOW_', 'red': 'RED_'}


def find_targets(path_type='all'):
    """Return the generated documents matching the requested path type."""
    base = Path(OUTPUT_DIR)
    if not base.exists():
        return []
    targets = []
    for file_path in base.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in ('.pdf', '.xlsx'):
            continue
        if path_type != 'all' and not file_path.name.startswith(PREFIXES[path_type]):
            continue
        targets.append(file_path)
    return sorted(targets)


def main():
    parser = argparse.ArgumentParser(
        description='Delete generated EnergoSmart test documents.')
    parser.add_argument('--type', choices=['green', 'yellow', 'red', 'all'],
                        default='all', help='limit deletion to one path type')
    parser.add_argument('--yes', action='store_true',
                        help='actually delete (default is a dry run)')
    args = parser.parse_args()

    targets = find_targets(args.type)
    if not targets:
        print(f'[OK] Nothing to clean in {OUTPUT_DIR} (type={args.type}).')
        return 0

    print(f'[FOUND] {len(targets)} file(s) in {OUTPUT_DIR} (type={args.type}):')
    for file_path in targets:
        print(f'   - {file_path.name}')

    if not args.yes:
        print('\n[DRY-RUN] Nothing deleted. Re-run with --yes to delete.')
        return 0

    deleted = 0
    for file_path in targets:
        try:
            file_path.unlink()
            deleted += 1
        except OSError as exc:
            print(f'   [WARN] could not delete {file_path.name}: {exc}')
    print(f'\n[OK] Deleted {deleted}/{len(targets)} file(s).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
