-- List RPA-synced rows (param: sector marker). clean.py --target rpa
SELECT client_id, reading_date, consumption_kwh, status
FROM energosmart_history
WHERE sector = ?
ORDER BY inserted_at DESC;
