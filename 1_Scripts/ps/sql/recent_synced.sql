-- Most recent RPA-synced rows. healthcheck.ps1 fills {0} with -Recent.
SELECT client_id, reading_date, consumption_kwh, status, inserted_at
FROM energosmart_history
WHERE sector = 'Unknown'
ORDER BY inserted_at DESC
LIMIT {0};
