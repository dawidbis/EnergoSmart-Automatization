# EnergoSmart — Next Steps

Status snapshot (2026-05-29): **Step 5 RPA bridge live (cloud → local SQLite). Only Power BI (Step 6) remains.**

✅ Python data layer (+ tests, CI, install.bat)
✅ Dataverse table `Readings` (publisher `dbis`, prefix `db_`)
✅ Custom AI Builder model (99%, published) — action **Process documents**
✅ Cloud Flow 1 `EnergoSmart_EmailProcessor` — 3 paths live (🟢 Accepted / 🟡 Pending Review / 🔴 reject email)
✅ Power Apps model-driven app `EnergoSmart - Weryfikacja` — Pending Review queue, form with AI fields, one-click **Akceptuj/Odrzuć** (Power Fx `Patch`)

Key gotchas already solved (reuse the knowledge):
- Power Fx is **Polish locale** → argument separator is `;` (not `,`).
- Choice reference is simply **`Status.Accepted`** / **`Status.Rejected`** (NOT `'Status (Reading)'...`).
- AI numeric values come back as **strings** → wrap in `float(...)`.
- AI output path: `outputs('Process_documents')?['body/responsev2/predictionOutput/labels/<Field>/value']` (and `/confidence`).
- Flow 2 trigger must be **Added *and* Modified** — 🟢 Green rows are inserted already `Accepted` (an *Add* event), so Modified-only never syncs them.

---

## ✅ DONE: Step 5 — RPA bridge to local SQLite (headline technical piece)

When a reading is **Accepted**, Flow 2 pushes it into the local
`energosmart_history.db` via Power Automate Desktop — **proven working end to end**
(verify with `healthcheck.bat`). Build notes kept below for reference / re-import.

### 5a. Cloud Flow 2 — `EnergoSmart_OnReadingAccepted`
1. Power Automate → in solution **EnergoSmart System** → New → Cloud flow → Automated
2. Trigger: **Dataverse → When a row is added, modified or deleted**
   - Table: `Readings`, Change type: **Added or Modified** (both), Scope: **Organization**
   - (Green rows are inserted already `Accepted`, so *Modified* only would skip them.)
3. **Condition**: Status equals **Accepted**
   - (Trigger sends Status as the option value; compare the Status column to Accepted.)
4. If yes → **Run a flow built with Power Automate Desktop** → `PAD_UpdateSQLDatabase`
   - Inputs: Client ID, Consumption kWh, Reading Date (from trigger row)
5. After success → **Update a row**: Status = **Synced**, Verified At = `utcNow()`

> See existing `4_Power_Platform_Solucja/FLOW_2_STATUS_TRIGGER.md`.

### 5b. Power Automate Desktop (the machine connector)
1. Install **Power Automate Desktop**, sign in with the same M365 account (machine auto-registers).
2. Install **SQLite ODBC Driver** (Ch. Werner) — gives an ODBC source for the `.db` file.
   - Create a System DSN pointing at `2_Baza_Danych/energosmart_history.db`, OR use a connection string.
3. New desktop flow `PAD_UpdateSQLDatabase` with **input variables**: ClientID, Consumption, ReadingDate.
4. Actions: **Open SQL connection** (ODBC/SQLite) → **Execute SQL statement**:
   ```sql
   INSERT INTO energosmart_history
     (client_id, client_name, sector, reading_date, consumption_kwh, status, inserted_at)
   VALUES
     ('%ClientID%', '%ClientID%', 'Unknown', '%ReadingDate%', %Consumption%, 'validated', datetime('now'))
   ```
   → **Close SQL connection**.
5. Paste the clean PAD (Robin) code into `5_RPA_Desktop_Flow/PAD_kod_zrodlowy.txt`.

> Student tenant note: desktop flows usually run **attended** here. Keep PAD open when testing Flow 2.

---

## Step 6 — Power BI dashboard
1. Power BI Desktop.
2. Source A — **Dataverse** (this environment, `Readings`) → **DirectQuery**: open queue count, status breakdown, avg AI confidence (operational "today").
3. Source B — **SQLite** via ODBC (`energosmart_history.db`) → **Import**: historical consumption by sector/client, DAX measures (YoY growth, moving average).
4. Apply theme → save `6_Power_BI_Dashboard/motyw_energosmart.json` and the `.pbix`.

---

## Optional enhancements (portfolio polish)
- **Real anomaly detection** (true 🟡 for value spikes): add a `MonthlyAvg` field to the AI model (re-tag + retrain + republish), then in Flow 1 compare `float(Consumption) vs float(MonthlyAvg)` — deviation > X% → Pending Review. Current flow only flags low-confidence / non-positive.
- **Excel + jpg/png** attachment paths in Flow 1 (currently PDF-only; Form type = pdf).
- **Attachment preview** in the app: save the email attachment to a Dataverse File column / SharePoint and show it on the form so the verifier sees the source document.
- **Button visibility**: show Akceptuj/Odrzuć only when Status = Pending Review (`Visible` = `Self.Selected.Item.Status = Status.'Pending Review'`).
- Dedupe the two manual `Hotel_99` test rows.

---

## Housekeeping
- **Export solution**: Solutions → EnergoSmart System → Export → Managed → save to `4_Power_Platform_Solucja/EnergoSmart_Solution.zip`.
- ~~git push~~ — done; local `main` is in sync with `origin/main`.
- Update root `README.md` status table as layers complete.
