-- Flagged anomalies. generate_history_db.py / healthcheck.ps1
SELECT COUNT(*) FROM energosmart_history WHERE anomaly_flag = 1;
