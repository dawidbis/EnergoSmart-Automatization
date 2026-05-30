-- EnergoSmart warehouse schema (executed by generate_history_db.py).
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
);

CREATE INDEX IF NOT EXISTS idx_client_date ON energosmart_history(client_id, reading_date);
CREATE INDEX IF NOT EXISTS idx_anomaly ON energosmart_history(anomaly_flag, status);
