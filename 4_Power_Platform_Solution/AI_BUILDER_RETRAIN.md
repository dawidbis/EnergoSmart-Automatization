# Retraining AI Builder so the Yellow path means something

**Goal:** make 🟡 *Pending Review* fire on a **real consumption anomaly**, not just
low OCR confidence. The model already reads `Consumption`; we add **`MonthlyAvg`**
as a second extracted field, then Cloud Flow 1 compares the two:

```
deviation = |Consumption - MonthlyAvg| / MonthlyAvg
deviation > 0.40   ->  🟡 Pending Review   (genuine spike / drop / zero)
deviation <= 0.40  ->  🟢 Accepted         (reading in the normal band)
```

The `0.40` threshold is the project-wide anomaly rule — it matches
`generate_history_db.py` (`anomaly_flag`) and `generate_invoices.py`
(`ANOMALY_THRESHOLD`). The test documents are built so the colour is
deterministic: **GREEN** docs sit within ~±8 % of the printed Monthly Avg,
**YELLOW** docs deviate by ≥ 45 %.

> **Also fixed here: Client ID vs Client Name.** Older documents printed only a
> single `Client:` line (the company string), so the model had nothing to map to
> a real ID and the company name leaked into the Dataverse **Client ID** column.
> Documents now print **two distinct fields** — `Client ID:` (a contract number
> like `UM-2024-0044`, the warehouse join key) and `Client Name:` (the company,
> e.g. `Polnord Group Sp. z o.o.`). Tag them as two separate fields below.

## Fields the model must extract

| AI Builder field | Document line | Dataverse column |
|---|---|---|
| `ClientID` | `Client ID:` (e.g. `UM-2024-0044`) | Client ID |
| `ClientName` | `Client Name:` (company) | Client Name |
| `Consumption` | `Consumption (kWh):` | Consumption kWh |
| `MonthlyAvg` | `Monthly Avg (kWh):` | Month Avg kWh |
| `ReadingDate` | `Reading Date:` | Reading Date |

> The **Client ID** value must equal the warehouse `client_id` (`UM-2024-####`),
> or the reading won't join to the 24 months of history in SQLite / Power BI.

---

## 1. Make fresh training / test documents

Every meter-reading PDF already prints both **Consumption (kWh)** and
**Monthly Avg (kWh)** (see `simulate_clients.write_meter_pdf`). Generate a clean,
labelled set:

```bat
cd 1_Scripts
python generate_invoices.py --green 8 --yellow 8 --red 4
```

- `GREEN_*` — Consumption ≈ Monthly Avg (normal)
- `YELLOW_zero_* / YELLOW_spike_* / YELLOW_drop_*` — Consumption far from Monthly Avg
- `RED_*` — no usable fields (flyer / blank)

Use a good spread of **GREEN + YELLOW** PDFs as the training collection so the
model learns to locate the Monthly Avg cell in both the normal and the anomalous
layouts (the cell is in the same place — only the number differs).

---

## 2. Add the `MonthlyAvg` field to the model + retrain

In **Power Apps → AI Builder → Models → (your document-processing model) → Edit**:

1. **Fields**: make sure the model has all five fields from the table above. Add
   the missing ones — **`MonthlyAvg`** and **`ClientName`** — next to the existing
   `ClientID`, `Consumption`, `ReadingDate`.
2. **Collections / tagging**: open each training document and (re)draw the tag
   boxes so every field maps to its own line — crucially **`ClientID` over the
   `Client ID:` value and `ClientName` over the `Client Name:` value** (the old
   model tagged the company name as the ID), plus `MonthlyAvg` over the
   **Monthly Avg (kWh)** value. Re-tag the whole collection so every doc has all
   five fields.
3. Add the new `YELLOW_*` PDFs to the collection and tag them too (same field
   positions — just anomalous values).
4. **Train** → wait for it to finish → check the per-field accuracy for
   `MonthlyAvg` is high.
5. **Publish** (republish) the model so the new field is available to flows.

> Tip: keep ≥ 5 documents per layout. Mixing GREEN and YELLOW examples teaches
> the model the field *position*, not the value, so it reads spikes correctly.

---

## 3. Wire the anomaly check into Cloud Flow 1

After the **Process documents** (AI Builder) action, add three **Compose**
actions, then branch on a **Condition**. AI numbers come back as **strings**, so
wrap every value in `float(...)` (see `../NEXT_STEPS.md` gotchas). These are
Power Automate **workflow expressions** (comma-separated) — *not* Power Fx, so no
Polish-locale `;` here.

> **Guard with `empty()`, not `coalesce()`.** The Compose actions run for *every*
> document, including 🔴 Red ones (a flyer has no Consumption). A missing field
> comes back as an **empty string `''`**, which `coalesce` does *not* replace
> (it only swaps `null`), so `float('')` throws *InvalidTemplate*. `empty()`
> catches both `null` and `''`, so default it to `'0'` before `float`.

**Compose `Consumption`:**
```
float(if(empty(outputs('Process_documents')?['body/responsev2/predictionOutput/labels/Consumption/value']), '0', outputs('Process_documents')?['body/responsev2/predictionOutput/labels/Consumption/value']))
```

**Compose `MonthlyAvg`:**
```
float(if(empty(outputs('Process_documents')?['body/responsev2/predictionOutput/labels/MonthlyAvg/value']), '0', outputs('Process_documents')?['body/responsev2/predictionOutput/labels/MonthlyAvg/value']))
```

**Compose `Deviation`** (WDL has no `abs`; `max(a-b, b-a)` gives `|a-b|`, and we
guard divide-by-zero):
```
if(greater(outputs('MonthlyAvg'), 0), div(max(sub(outputs('Consumption'), outputs('MonthlyAvg')), sub(outputs('MonthlyAvg'), outputs('Consumption'))), outputs('MonthlyAvg')), 1)
```

**Condition — 🟢 Green (auto-accept)** — all must be true:

| Left | Operator | Right |
|---|---|---|
| `float(.../Consumption/confidence)` | is greater than or equal to | `0.8` |
| `outputs('Consumption')` | is greater than | `0` |
| `outputs('Deviation')` | is less than or equal to | `0.4` |

- **If yes → 🟢** create the Dataverse row `Status = Accepted` — mapping **Client
  ID** ← `ClientID/value` and **Client Name** ← `ClientName/value` (plain text, no
  `float`) so the ID and company land in their own columns — then invoke
  `PAD_UpdateSQLDatabase` directly, passing **both** ClientID and ClientName (the
  accepted reading syncs to SQLite with the real company name).
- **If no →** nested **Condition**: is the data even readable?
  - `outputs('Consumption')` ≤ `0` **AND** ClientID empty → **🔴 Red**: send the
    rejection email, create no row.
  - otherwise → **🟡 Yellow**: create the row `Status = Pending Review` and set
    **Anomaly Reason** = an expression that names the cause, e.g.
    ```
    if(greater(outputs('Deviation'), 0.4), concat('Consumption deviates ', string(mul(outputs('Deviation'), 100)), '% from monthly average'), 'Low AI confidence')
    ```

> So Yellow now fires for two distinct, explainable reasons: **a real anomaly**
> (deviation > 40 %) *or* low extraction confidence — and the reviewer sees which.

---

## 4. Verify end to end

1. `python generate_invoices.py --green 2 --yellow 2 --red 1`
2. `python send_documents.py --green 2 --yellow 2 --red 1` (or `--interactive`)
3. Watch Flow 1 run history:
   - GREEN → `Accepted` (and PAD pushes it to SQLite),
   - YELLOW → `Pending Review` with an Anomaly Reason naming the deviation,
   - RED → rejection email, no row.
4. `warehouse_healthcheck.bat` / the SQLite query in `FLOW_2_STATUS_TRIGGER.md` to confirm
   accepted rows landed in the warehouse.

## Also see
- `SETUP_GUIDE.md` — full Cloud Flow 1 build (Green/Yellow/Red).
- `../1_Scripts/py/generate_invoices.py` — typed-document generator (threshold).
- `../NEXT_STEPS.md` — roadmap + expression gotchas.
