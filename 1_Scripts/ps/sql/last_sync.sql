-- Timestamp of the most recent RPA sync. monitor.ps1
SELECT MAX(inserted_at) FROM energosmart_history WHERE sector = 'Unknown';
