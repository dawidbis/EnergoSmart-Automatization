-- Delete RPA-synced rows (param: sector marker). clean.py --target rpa
DELETE FROM energosmart_history WHERE sector = ?;
