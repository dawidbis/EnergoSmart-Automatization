-- Row counts per status. healthcheck.ps1
SELECT status, COUNT(*) AS readings
FROM energosmart_history
GROUP BY status
ORDER BY readings DESC;
