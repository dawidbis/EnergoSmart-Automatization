-- Reference: the INSERT the Power Automate Desktop flow (PAD_UpdateSQLDatabase)
-- runs over ODBC when a reading is Accepted. %X% are PAD input variables.
-- Source of truth lives in 5_RPA_Desktop_Flow/PAD_kod_zrodlowy.txt.
INSERT OR REPLACE INTO energosmart_history
    (client_id, client_name, sector, reading_date, consumption_kwh, status, inserted_at)
VALUES
    ('%ClientID%', '%ClientName%', 'Unknown', date('%ReadingDate%'), %Consumption%, 'validated', datetime('now'));
