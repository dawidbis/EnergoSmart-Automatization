# Cloud Flow 2: EnergoSmart_OnReadingAccepted

## Purpose
Fires when a reading reaches `Status = Accepted` in Dataverse and calls the
**Power Automate Desktop** flow `PAD_UpdateSQLDatabase` (RPA) to insert the
validated reading into the local warehouse `2_Database/energosmart_history.db`.
On success it stamps the Dataverse row back to `Status = Synced`.

> Naming here matches the **actually built** solution (see `../NEXT_STEPS.md`):
> table **`Readings`**, publisher `dbis`, column prefix `db_`. Build the desktop
> flow first (or as a stub) — see `../5_RPA_Desktop_Flow/README.md`.

```
Dataverse row Added/Modified ──► Condition: Status = Accepted ──► Run PAD flow ──► Update row: Synced
```

---

## 1. Create the flow (inside the solution)

1. **Power Automate** → open solution **EnergoSmart System** → **New** →
   **Automation** → **Cloud flow** → **Automated**.
2. Name: `EnergoSmart_OnReadingAccepted`.
3. Trigger: **Dataverse → When a row is added, modified or deleted**. **Create**.

Building it *inside the solution* keeps it in the export `.zip`.

---

## 2. Configure the trigger

In the trigger card:
- **Change type**: `Added or Modified` (tick **both**)
- **Table name**: `Readings`
- **Scope**: `Organization` (any user's edit can trigger it)
- (Optional) **Select columns** / **Filter rows** to narrow firing — leave blank to start.

> Trigger on **Added *and* Modified**. A 🟢 Green reading is **inserted already
> `Accepted`** by Flow 1 — an *Add* event — while a 🟡 Yellow reading is accepted
> later in Power Apps — a *Modify* event. **Modified-only misses every
> auto-accepted row**, so those readings never reach the local SQL warehouse.

---

## 3. Condition — only continue when Accepted

1. **New step** → **Condition**.
2. Left value: the **Status** column from the trigger row (dynamic content).
   - The trigger returns Status as its **option-set value** (an integer), not the
     label. Two robust ways to compare:
     - Use the **Status Value** dynamic-content field if shown, OR
     - compare the label text after a **Get a row by ID**, OR
     - compare against the numeric value of `Accepted` from your choice set.
3. Operator: **is equal to** → **Accepted** (label or its option value).

Everything below goes in the **If yes** branch.

---

## 4. If yes — run the desktop flow (RPA)

1. **New step** → **Run a flow built with Power Automate Desktop**.
2. **Desktop flow**: `PAD_UpdateSQLDatabase`.
3. **Run mode**: **Attended** (student/dev tenant — keep PAD open). Pick **your machine**.
4. Inputs (map from the trigger row):
   | Desktop input | Dataverse field |
   |---|---|
   | `ClientID` | Client ID (`db_clientid`) |
   | `ClientName` | Client Name (`db_clientname`) |
   | `Consumption` | Consumption kWh (`db_consumptionkwh`) |
   | `ReadingDate` | Reading Date (`db_readingdate`) |

> See `../5_RPA_Desktop_Flow/README.md` + `PAD_kod_zrodlowy.txt` for the desktop
> flow itself (ODBC → SQLite `INSERT`).

---

## 5. After success — mark the row Synced

1. **New step** (still in **If yes**) → **Dataverse → Update a row**.
2. **Table**: `Readings`.
3. **Row ID**: the trigger row's unique id (dynamic content).
4. Set columns:
   - **Status** = `Synced`
   - **Verified At** = `utcNow()`

> Setting Status to `Synced` (not back to `Accepted`) prevents a loop: the Synced
> write is itself a *Modify* event that re-fires the trigger, but `Synced` fails
> the Step 3 condition so the run stops cleanly. (Inserting a `Pending Review` row
> likewise fires the *Add* trigger but fails the condition — no action taken.)

---

## 6. Save & turn on

**Save** → toggle **On**.

---

## Testing

1. Keep **Power Automate Desktop** open and signed in (attended runs).
2. In the Power Apps app **Accept** a `Pending Review` reading, or in Dataverse set a
   row's **Status** to `Accepted` manually.
3. Flow 2 fires → desktop-flow action runs → row should flip to **Synced**.
4. Verify the local insert:
   ```bat
   python -c "import sqlite3;c=sqlite3.connect(r'2_Database/energosmart_history.db');print(c.execute(\"SELECT client_id,reading_date,consumption_kwh,status FROM energosmart_history WHERE sector='Unknown' ORDER BY inserted_at DESC LIMIT 5\").fetchall())"
   ```

---

## Common gotchas

| Symptom | Fix |
|---|---|
| Flow loops forever | Final update must set a status that **fails** the condition (use `Synced`). |
| Auto-accepted (Green) rows never sync | Change type was **Modified only** — set it to **Added or Modified** so inserted-as-Accepted rows fire it too. |
| Condition never true | You compared label vs. option value — match types (label↔label or value↔value). |
| Desktop step can't run | Pick **Attended** + your registered machine; keep PAD open. |
| Nothing inserted locally | Check the SQLite ODBC string/DSN and the absolute `.db` path in the PAD flow. |

## Also see
- `../5_RPA_Desktop_Flow/README.md` — desktop flow + ODBC setup
- `00_SOLUTION_SETUP.md` — solution / table / connections
- `SETUP_GUIDE.md` — Cloud Flow 1 (Email Processor)
- `../NEXT_STEPS.md` — roadmap (Step 5 / Step 6)
