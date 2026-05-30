"""
EnergoSmart - Typed test-document (invoice / meter-reading) generator.

Generates a user-specified number of text-layer PDF documents, split by the
Cloud Flow decision paths so you can exercise every branch end-to-end:

  GREEN  - valid reading, Client ID present, Consumption near the Monthly Avg
           -> Cloud Flow auto-accepts (Status = Accepted)
  YELLOW - valid meter-reading layout but Consumption deviates from Monthly Avg
           by more than ANOMALY_THRESHOLD (zero / spike / drop)
           -> Cloud Flow routes to manual review (Status = Pending Review)
  RED    - missing critical data (no Client ID, e.g. a promo flyer)
           -> Cloud Flow auto-rejects (sends rejection email)

The Green/Yellow split mirrors the anomaly rule the (retrained) AI Builder model
+ Cloud Flow 1 apply downstream: extract both Consumption and Monthly Avg, then
flag |Consumption - MonthlyAvg| / MonthlyAvg > ANOMALY_THRESHOLD for review. The
same 0.40 threshold is used by generate_history_db.py's anomaly_flag.

Reuses the PDF layout + DB helpers from simulate_clients.py, so GREEN/YELLOW
documents look exactly like the AI Builder training documents.

Usage:
    python generate_invoices.py --green 5 --yellow 3 --red 2
    python generate_invoices.py --each 4
Output files are named <PATH>_*.pdf in OUTPUT_DIR (GREEN_*, YELLOW_*, RED_*)
so send_documents.py and monitor_company.py can recognise them.
"""

import argparse
import os
import random

from dotenv import load_dotenv

from simulate_clients import (
    EnergyReportPDF,
    fetch_recent_readings,
    get_all_clients,
)

load_dotenv()

DB_PATH = os.getenv('DB_PATH', '../2_Baza_Danych/energosmart_history.db')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../3_Dokumenty_Testowe')

# Deviation of Consumption from the Monthly Avg above which a reading is an
# anomaly (-> Yellow / Pending Review). Matches generate_history_db.py.
ANOMALY_THRESHOLD = float(os.getenv('ANOMALY_THRESHOLD', '0.40'))

YELLOW_KINDS = ('zero', 'spike', 'drop')


def _history_rows(readings, limit=4):
    """Build (date, consumption) reference rows from the older readings."""
    return [(r['reading_date'], r['consumption_kwh']) for r in readings[1:1 + limit]]


def write_meter_pdf(path, client_name, sector, reading_date,
                    consumption, month_avg, history):
    """Write a meter-reading PDF matching the AI Builder training layout."""
    pdf = EnergyReportPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"Client: {client_name}", 0, 1)
    pdf.cell(0, 8, f"Sector: {sector}", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.ln(3)
    pdf.cell(70, 8, 'Reading Date:', 1)
    pdf.cell(0, 8, str(reading_date), 1, 1)
    pdf.cell(70, 8, 'Consumption (kWh):', 1)
    pdf.cell(0, 8, f"{consumption:.2f}", 1, 1)
    pdf.cell(70, 8, 'Monthly Avg (kWh):', 1)
    pdf.cell(0, 8, f"{month_avg:.2f}", 1, 1)
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 8, 'Previous Readings (Reference)', 0, 1)
    pdf.set_font('Arial', '', 9)
    for date_value, value in history:
        pdf.cell(60, 7, str(date_value), 1)
        pdf.cell(0, 7, f"{value:.2f}", 1, 1)
    pdf.output(path)
    return path


def make_green(clients, index):
    """A clean reading, Consumption near the Monthly Avg -> auto-accept (Green)."""
    client_id, _ = random.choice(clients)
    readings = fetch_recent_readings(client_id, num_months=6)
    if not readings:
        return None
    latest = readings[0]
    month_avg = latest.get('month_avg_kwh') or latest['consumption_kwh']
    # Keep Consumption comfortably inside the anomaly band (~+/-8%) so Flow 1's
    # |Consumption - MonthlyAvg| / MonthlyAvg check stays well under the threshold.
    consumption = month_avg * random.uniform(0.92, 1.08)
    path = os.path.join(OUTPUT_DIR, f"GREEN_{client_id}_{index:02d}.pdf")
    return write_meter_pdf(
        path, latest['client_name'], latest['sector'], latest['reading_date'],
        consumption, month_avg, _history_rows(readings),
    )


def make_yellow(clients, index, kind=None):
    """Consumption far from the Monthly Avg (> threshold) -> manual review (Yellow)."""
    client_id, _ = random.choice(clients)
    readings = fetch_recent_readings(client_id, num_months=6)
    if not readings:
        return None
    latest = readings[0]
    month_avg = latest.get('month_avg_kwh') or latest['consumption_kwh']
    kind = kind or random.choice(YELLOW_KINDS)
    # Each kind deviates from month_avg by clearly more than ANOMALY_THRESHOLD,
    # so the retrained model + Flow 1 anomaly check route it to Pending Review.
    over = 1 + ANOMALY_THRESHOLD + random.uniform(0.2, 1.6)   # >= 1.6x  (spike)
    under = 1 - ANOMALY_THRESHOLD - random.uniform(0.05, 0.2)  # <= 0.55x (drop)
    if kind == 'zero':
        consumption = 0.0
    elif kind == 'spike':
        consumption = month_avg * over
    else:  # drop
        consumption = month_avg * under
    path = os.path.join(OUTPUT_DIR, f"YELLOW_{kind}_{client_id}_{index:02d}.pdf")
    return write_meter_pdf(
        path, latest['client_name'], latest['sector'], latest['reading_date'],
        consumption, month_avg, _history_rows(readings),
    )


def make_red(index, kind=None):
    """Document with no usable reading fields -> auto-reject (Red path)."""
    kind = kind or random.choice(('flyer', 'blank'))
    pdf = EnergyReportPDF()
    pdf.add_page()
    if kind == 'flyer':
        pdf.set_font('Arial', 'B', 20)
        pdf.ln(20)
        pdf.cell(0, 15, 'MEGA PROMOCJA WIOSENNA!', 0, 1, 'C')
        pdf.set_font('Arial', '', 14)
        pdf.ln(5)
        pdf.cell(0, 10, 'Tylko teraz: panele fotowoltaiczne -40%', 0, 1, 'C')
        pdf.cell(0, 10, 'Zadzwon i odbierz darmowa wycene!', 0, 1, 'C')
        pdf.ln(10)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 8,
                       'Oferta ograniczona czasowo. Promocja nie laczy sie z '
                       'innymi rabatami. Skontaktuj sie z naszym doradca.')
    else:  # blank / unreadable - no Client ID, no Consumption
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Notatka wewnetrzna', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 8,
                       'Dokument bez pol odczytu - brak identyfikatora klienta '
                       'oraz wartosci zuzycia. Powinien trafic na sciezke '
                       'odrzucenia (Red).')
    path = os.path.join(OUTPUT_DIR, f"RED_{kind}_{index:02d}.pdf")
    pdf.output(path)
    return path


def generate_all(clients, green, yellow, red):
    """Run the three generation loops and return a {path: count} tally."""
    made = {'green': 0, 'yellow': 0, 'red': 0}
    for i in range(1, green + 1):
        path = make_green(clients, i)
        if path:
            made['green'] += 1
            print(f'  [GREEN]  {os.path.basename(path)}')
    for i in range(1, yellow + 1):
        path = make_yellow(clients, i)
        if path:
            made['yellow'] += 1
            print(f'  [YELLOW] {os.path.basename(path)}')
    for i in range(1, red + 1):
        path = make_red(i)
        if path:
            made['red'] += 1
            print(f'  [RED]    {os.path.basename(path)}')
    return made


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate typed EnergoSmart test documents (Green/Yellow/Red).')
    parser.add_argument('--green', type=int, default=0,
                        help='number of valid, auto-accept documents')
    parser.add_argument('--yellow', type=int, default=0,
                        help='number of review-path documents (zero/spike/drop)')
    parser.add_argument('--red', type=int, default=0,
                        help='number of reject-path documents (flyer/blank)')
    parser.add_argument('--each', type=int, default=0,
                        help='shortcut: set green = yellow = red to this value')
    return parser.parse_args()


def main():
    args = parse_args()
    green = args.green or args.each
    yellow = args.yellow or args.each
    red = args.red or args.each
    if green + yellow + red <= 0:
        print('[ERROR] Nothing to generate. Use --green/--yellow/--red or --each N.')
        return 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    clients = []
    if green or yellow:
        if not os.path.exists(DB_PATH):
            print(f'[ERROR] Database not found at {DB_PATH}')
            print('   Run: python generate_history_db.py')
            return 1
        clients = get_all_clients()
        if not clients:
            print('[ERROR] No clients in the database.')
            return 1

    print(f'[START] Generating {green} GREEN, {yellow} YELLOW, {red} RED documents...')
    made = generate_all(clients, green, yellow, red)

    total = sum(made.values())
    print(f'\n[OK] Generated {total} document(s) in {OUTPUT_DIR}')
    print(f'     GREEN={made["green"]}  YELLOW={made["yellow"]}  RED={made["red"]}')
    print('Next: send_documents.py (email them) or monitor_company.py (watch the flow).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
