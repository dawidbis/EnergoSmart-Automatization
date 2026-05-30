-- Distinct clients in the warehouse. simulate_clients.py
SELECT DISTINCT client_id, client_name
FROM energosmart_history
ORDER BY client_id;
