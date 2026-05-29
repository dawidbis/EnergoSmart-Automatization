# 6 - Power BI Dashboard

Two-source report that closes the loop: **live operational tracking** from
Dataverse and **whole-company historical analytics** from the local SQLite
warehouse.

| Source | Connector | Mode | Answers |
|---|---|---|---|
| **Dataverse** `Readings` | Dataverse | **DirectQuery** | What's happening *now*: open review queue, status mix, AI accuracy, today's intake |
| **SQLite** `energosmart_history.db` | ODBC (SQLite3 ODBC Driver) | **Import** | Long-term picture: consumption by sector/client, trends, YoY, anomalies |

## Prerequisites

- **Power BI Desktop** (free).
- **SQLite3 ODBC Driver** installed — run `setup.bat` (it's the same driver the RPA uses).
- The warehouse built — run `demo.bat` (or `bat\run_local_pipeline.bat`).
- Access to the Dataverse environment that holds the `Readings` table.

---

## Part 1 - Live tracking (Dataverse, DirectQuery)

1. Power BI Desktop → **Get data** → **Power Platform** → **Dataverse** → **Connect**.
2. Sign in with the same M365 account; pick your **Environment**.
3. Select the **Readings** table → **Load**.
4. When prompted for storage mode choose **DirectQuery** (so the report reflects
   Dataverse in real time — accepts, rejects and syncs show up live).

Columns you'll use: `Status`, `AI Confidence`, `Client ID`, `Consumption kWh`,
`Reading Date`, `Verified At`, `Created On`.

---

## Part 2 - Company analytics (SQLite, Import via ODBC)

1. (Once) Create a **System DSN** *or* use a connection string. Easiest is a DSN:
   **ODBC Data Sources (64-bit)** → **System DSN** → **Add** → *SQLite3 ODBC Driver*
   → Name `EnergoSmart` → Database = full path to
   `2_Baza_Danych\energosmart_history.db` → OK.
2. Power BI Desktop → **Get data** → **ODBC** → pick the **EnergoSmart** DSN
   (or paste `Driver={SQLite3 ODBC Driver};Database=C:\...\energosmart_history.db;`).
3. Select **energosmart_history** → **Load** (storage mode **Import**).
4. In **Power Query**, set types: `reading_date` → Date, `consumption_kwh` /
   `month_avg_kwh` → Decimal, `anomaly_flag` → Whole number. Optionally add a
   **Date** dimension table and mark it as a date table for time intelligence.

> Note: the two sources stay **separate** (different storage modes). Build one
> report page per source rather than relating the tables.

---

## Part 3 - Apply the theme

**View** → **Themes** → **Browse for themes** → select
`6_Power_BI_Dashboard/motyw_energosmart.json`. Green = accepted/good,
amber = pending/review, red = rejected — matching the 🟢/🟡/🔴 flow logic.

---

## Part 4 - Suggested pages

**Page 1 — "Na żywo" (Dataverse / DirectQuery)**
- Cards: *Open queue* (Pending Review), *Accepted today*, *Synced today*, *Avg AI confidence*.
- Donut: **Status** breakdown.
- Column: count by **Status** over **Created On** (by day).
- Table: Pending Review rows (Client ID, Consumption, AI Confidence) for the reviewer.

**Page 2 — "Cała firma" (SQLite / Import)**
- Card: *Total consumption (kWh)*, *Clients*, *Anomaly rate*.
- Bar: **Avg consumption by sector**.
- Line: **Consumption over time** (monthly) with a 3-month moving average.
- Matrix: sector × month consumption; conditional formatting (theme good→bad).
- KPI: **YoY growth**.

---

## Part 5 - DAX measures

**Dataverse page (live):**
```DAX
Open Queue       = CALCULATE ( COUNTROWS ( Readings ), Readings[Status] = "Pending Review" )
Accepted         = CALCULATE ( COUNTROWS ( Readings ), Readings[Status] IN { "Accepted", "Synced" } )
Synced           = CALCULATE ( COUNTROWS ( Readings ), Readings[Status] = "Synced" )
Rejected         = CALCULATE ( COUNTROWS ( Readings ), Readings[Status] = "Rejected" )
Avg AI Confidence = AVERAGE ( Readings[AI Confidence] )
Accepted Today   =
    CALCULATE (
        [Accepted],
        FILTER ( Readings, INT ( Readings[Created On] ) = INT ( TODAY () ) )
    )
```

**SQLite page (historical):**
```DAX
Total Consumption = SUM ( energosmart_history[consumption_kwh] )
Avg Consumption   = AVERAGE ( energosmart_history[consumption_kwh] )
Anomaly Count     = CALCULATE ( COUNTROWS ( energosmart_history ), energosmart_history[anomaly_flag] = 1 )
Anomaly Rate %    = DIVIDE ( [Anomaly Count], COUNTROWS ( energosmart_history ) )

Consumption 3M Moving Avg =
    AVERAGEX (
        DATESINPERIOD ( 'Date'[Date], MAX ( 'Date'[Date] ), -3, MONTH ),
        [Avg Consumption]
    )

Consumption YoY % =
    VAR Curr = [Total Consumption]
    VAR Prior = CALCULATE ( [Total Consumption], DATEADD ( 'Date'[Date], -1, YEAR ) )
    RETURN DIVIDE ( Curr - Prior, Prior )
```

> `Consumption YoY %` and the moving average need a marked **Date** table related
> to `energosmart_history[reading_date]`.

---

## Part 6 - Save

Save the report as `6_Power_BI_Dashboard/EnergoSmart.pbix`. The `.pbix` is large
and git-ignored by convention — keep it local or attach to the project write-up.
