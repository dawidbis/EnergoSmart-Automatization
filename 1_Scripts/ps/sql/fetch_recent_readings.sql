-- Most recent readings for one client (params: client_id, limit). simulate_clients.py
SELECT client_id, client_name, sector, reading_date, consumption_kwh, month_avg_kwh
FROM energosmart_history
WHERE client_id = ?
ORDER BY reading_date DESC
LIMIT ?;
