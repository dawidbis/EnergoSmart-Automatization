"""
EnergoSmart Client Report Simulator
Generates monthly energy consumption reports and simulates client submissions.
Creates Excel files and optionally sends via email.
Demonstrates: data extraction, anomaly injection, realistic document generation.
"""

import sqlite3
import random
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
from fpdf import FPDF
from fpdf.enums import XPos, YPos

load_dotenv()

DB_PATH = os.getenv('DB_PATH', '../../2_Database/energosmart_history.db')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '../../3_Test_Documents')
ANOMALY_INJECTION_RATE = 0.15

# Shared SQL library lives with the PowerShell tooling (1_Scripts/ps/sql).
SQL_DIR = Path(__file__).resolve().parent.parent / 'ps' / 'sql'


def load_sql(name):
    """Read a query from the shared .sql library (1_Scripts/ps/sql)."""
    return (SQL_DIR / f'{name}.sql').read_text(encoding='utf-8')

class EnergyReportPDF(FPDF):
    """Custom PDF for energy meter readings"""

    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'EnergoSmart - Monthly Energy Report', border=0, align='C',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', '', 10)
        self.cell(0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d")}', border=0,
                  align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', border=0, align='C')

def fetch_recent_readings(client_id, num_months=6):
    """Fetch recent readings for a client"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(load_sql('fetch_recent_readings'), (client_id, num_months * 4))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def generate_excel_report(client_id, readings):
    """Generate Excel file with energy readings"""
    if not readings:
        return None

    df = pd.DataFrame(readings)
    df['reading_date'] = pd.to_datetime(df['reading_date'])
    df = df.sort_values('reading_date')

    filename = f"{OUTPUT_DIR}/{client_id}_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Readings', index=False)

        # Add summary sheet
        summary = pd.DataFrame({
            'Metric': ['Total Readings', 'Average Consumption (kWh)', 'Peak (kWh)', 'Min (kWh)'],
            'Value': [
                len(df),
                f"{df['consumption_kwh'].mean():.2f}",
                f"{df['consumption_kwh'].max():.2f}",
                f"{df['consumption_kwh'].min():.2f}",
            ]
        })
        summary.to_excel(writer, sheet_name='Summary', index=False)

    return filename

def generate_pdf_report(client_id, readings):
    """Generate PDF meter reading (simulates scanned form)"""
    if not readings:
        return None

    filename = f"{OUTPUT_DIR}/{client_id}_MeterReading_{datetime.now().strftime('%Y%m%d')}.pdf"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    pdf = EnergyReportPDF()
    pdf.add_page()
    pdf.set_font('Helvetica', '', 10)

    # Client info
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 8, f"Client ID: {readings[0]['client_id']}", border=0,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Client Name: {readings[0]['client_name']}", border=0,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 8, f"Sector: {readings[0]['sector']}", border=0,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 10)
    pdf.ln(3)

    # Readings table
    latest = readings[0]
    pdf.cell(70, 8, 'Reading Date:', 1)
    pdf.cell(0, 8, str(latest['reading_date']), border=1,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(70, 8, 'Consumption (kWh):', 1)
    pdf.cell(0, 8, f"{latest['consumption_kwh']:.2f}", border=1,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(70, 8, 'Monthly Avg (kWh):', 1)
    pdf.cell(0, 8, f"{latest['month_avg_kwh']:.2f}", border=1,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(0, 8, 'Previous Readings (Reference)', border=0,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('Helvetica', '', 9)

    for i, reading in enumerate(readings[1:6]):
        pdf.cell(60, 7, str(reading['reading_date']), 1)
        pdf.cell(0, 7, f"{reading['consumption_kwh']:.2f}", border=1,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.output(filename)
    return filename

def get_all_clients():
    """Fetch all unique clients from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(load_sql('get_all_clients'))
    clients = cursor.fetchall()
    conn.close()
    return clients

def inject_anomaly(readings):
    """Modify readings to simulate anomalies (for testing AI)"""
    if not readings:
        return readings

    anomaly_type = random.choice(['spike', 'drop', 'noise'])
    modified = readings.copy()
    target = modified[0].copy()

    if anomaly_type == 'spike':
        target['consumption_kwh'] *= random.uniform(2.5, 4.0)
        target['anomaly_type'] = 'spike'
    elif anomaly_type == 'drop':
        target['consumption_kwh'] *= random.uniform(0.2, 0.5)
        target['anomaly_type'] = 'drop'
    else:
        target['consumption_kwh'] *= random.uniform(0.5, 1.5)
        target['anomaly_type'] = 'noise'

    modified[0] = target
    return modified

def generate_test_documents(num_reports=20):
    """Generate sample reports for testing"""
    print(f'Generating {num_reports} test reports...')

    all_clients = get_all_clients()
    selected_clients = random.sample(all_clients, min(num_reports, len(all_clients)))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generated = []

    for client_id, client_name in selected_clients:
        readings = fetch_recent_readings(client_id, num_months=6)

        # Inject anomaly sometimes
        if random.random() < ANOMALY_INJECTION_RATE:
            readings = inject_anomaly(readings)

        if readings:
            # Random choice: Excel or PDF
            if random.choice([True, False]):
                file = generate_excel_report(client_id, readings)
                doc_type = 'Excel'
            else:
                file = generate_pdf_report(client_id, readings)
                doc_type = 'PDF'

            generated.append({
                'client_id': client_id,
                'file': file,
                'type': doc_type,
                'anomaly': readings[0].get('anomaly_type', None)
            })
            print(f'  [OK] {client_id} ({doc_type})', end='')
            if readings[0].get('anomaly_type'):
                print(f' [ANOMALY: {readings[0]["anomaly_type"]}]')
            else:
                print()

    return generated

def summarize_generation():
    """Print summary of generated documents"""
    docs = []
    for file in Path(OUTPUT_DIR).glob('*'):
        if file.is_file() and file.suffix in ['.xlsx', '.pdf']:
            docs.append(file.name)

    print(f'\n[SUMMARY] Generated {len(docs)} test documents in {OUTPUT_DIR}')
    for doc in sorted(docs)[:10]:
        print(f'   - {doc}')
    if len(docs) > 10:
        print(f'   ... and {len(docs) - 10} more')

if __name__ == '__main__':
    print('[START] EnergoSmart Client Report Simulator\n')

    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f'[ERROR] Database not found at {DB_PATH}')
        print('   Run: python generate_history_db.py')
        exit(1)

    generated = generate_test_documents(num_reports=20)
    summarize_generation()

    print('\n[SUCCESS] Report generation complete!')
    print('These documents are ready for Power Automate + AI Builder testing.')
