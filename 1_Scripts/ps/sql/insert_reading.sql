-- Insert one seeded historical reading (parameterised, used by generate_history_db.py).
INSERT INTO energosmart_history
    (client_id, client_name, sector, reading_date, consumption_kwh,
     month_avg_kwh, anomaly_flag, anomaly_reason, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
