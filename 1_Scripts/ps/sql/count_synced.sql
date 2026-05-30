-- RPA-synced rows (PAD inserts tag sector='Unknown'). healthcheck.ps1 / monitor.ps1
SELECT COUNT(*) FROM energosmart_history WHERE sector = 'Unknown';
