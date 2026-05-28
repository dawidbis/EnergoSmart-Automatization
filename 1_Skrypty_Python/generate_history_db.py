"""
EnergoSmart Historical Database Generator
Generates a realistic SQLite database with energy consumption records.
Simulates historical data for 150 business clients over 24 months.
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv('DB_PATH', '../2_Baza_Danych/energosmart_history.db')
NUM_RECORDS = int(os.getenv('NUM_RECORDS', 500000))
NUM_CLIENTS = int(os.getenv('NUM_CLIENTS', 150))

SECTOR_TEMPLATES = {
    'Fabryka Chemiczna': {'min': 5000, 'max': 25000, 'variance': 0.15},
    'Galeria Handlowa': {'min': 3000, 'max': 12000, 'variance': 0.10},
    'Biurowiec': {'min': 1000, 'max': 5000, 'variance': 0.08},
    'Hala Logistyczna': {'min': 8000, 'max': 30000, 'variance': 0.12},
    'Data Center': {'min': 15000, 'max': 50000, 'variance': 0.05},
    'Szpital': {'min': 4000, 'max': 15000, 'variance': 0.10},
    'Hotel': {'min': 2000, 'max': 8000, 'variance': 0.12},
}

def generate_clients():
    """Generate realistic client profiles"""
    clients = []
    for i in range(NUM_CLIENTS):
        sector = random.choice(list(SECTOR_TEMPLATES.keys()))
        template = SECTOR_TEMPLATES[sector]
        client = {
            'id': f'CLIENT_{i+1:04d}',
            'name': f'{sector.replace(" ", "")}_{i+1}',
            'sector': sector,
            'baseline': random.uniform(template['min'], template['max']),
            'variance': template['variance'],
        }
        clients.append(client)
    return clients

def generate_consumption(baseline, variance, month_factor=1.0):
    """Generate realistic consumption with seasonal variation"""
    seasonal = random.uniform(0.85, 1.15)
    noise = random.gauss(1.0, variance)
    return baseline * seasonal * month_factor * noise

def init_database():
    """Create database schema"""
    os.makedirs(Path(DB_PATH).parent, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS energosmart_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            client_name TEXT NOT NULL,
            sector TEXT NOT NULL,
            reading_date DATE NOT NULL,
            consumption_kwh REAL NOT NULL,
            month_avg_kwh REAL,
            anomaly_flag INTEGER DEFAULT 0,
            anomaly_reason TEXT,
            status TEXT DEFAULT 'validated',
            inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(client_id, reading_date)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_client_date ON energosmart_history(client_id, reading_date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_anomaly ON energosmart_history(anomaly_flag, status)')

    conn.commit()
    return conn

def populate_database(conn, clients):
    """Populate database with 24 months of historical data"""
    cursor = conn.cursor()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)

    total = len(clients) * 24
    inserted = 0

    for client in clients:
        current_date = start_date
        monthly_readings = []

        while current_date < end_date:
            # 4 readings per month (weekly approximation)
            for week in range(4):
                reading_date = current_date + timedelta(days=week*7)
                if reading_date >= end_date:
                    break

                consumption = generate_consumption(
                    client['baseline'],
                    client['variance'],
                    month_factor=1.0
                )
                consumption = max(0, consumption)

                monthly_readings.append({
                    'date': reading_date,
                    'consumption': consumption,
                })

            # Calculate monthly average for anomaly detection
            if monthly_readings:
                month_avg = sum(r['consumption'] for r in monthly_readings) / len(monthly_readings)

                # Insert with anomaly detection
                for reading in monthly_readings:
                    deviation = abs(reading['consumption'] - month_avg) / month_avg
                    anomaly_flag = 1 if deviation > 0.40 else 0

                    try:
                        cursor.execute('''
                            INSERT INTO energosmart_history
                            (client_id, client_name, sector, reading_date, consumption_kwh,
                             month_avg_kwh, anomaly_flag, anomaly_reason, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            client['id'],
                            client['name'],
                            client['sector'],
                            reading['date'].date(),
                            reading['consumption'],
                            month_avg,
                            anomaly_flag,
                            'High deviation from monthly average' if anomaly_flag else None,
                            'validated'
                        ))
                        inserted += 1
                    except sqlite3.IntegrityError:
                        pass

            monthly_readings = []
            current_date += timedelta(days=30)

    conn.commit()
    print(f'[OK] Inserted {inserted} records into {DB_PATH}')

    # Print statistics
    cursor.execute('SELECT COUNT(*) FROM energosmart_history')
    total_records = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM energosmart_history WHERE anomaly_flag = 1')
    anomalies = cursor.fetchone()[0]

    print(f'  Total records: {total_records:,}')
    print(f'  Anomalies detected: {anomalies:,} ({100*anomalies/total_records:.2f}%)')
    print(f'  Clients: {len(clients)}')
    print(f'  Time span: 24 months')

if __name__ == '__main__':
    print('Generating EnergoSmart historical database...')
    clients = generate_clients()
    print(f'[OK] Generated {len(clients)} client profiles')

    conn = init_database()
    print(f'[OK] Database schema initialized at {DB_PATH}')

    populate_database(conn, clients)
    conn.close()

    print('\n[SUCCESS] Database generation complete!')
