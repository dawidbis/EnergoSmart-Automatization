# 00 - Solution & Connections Setup (START HERE)

This is the **first** thing to do in Power Platform, before building any flow.
Order: **Solution → Publisher → Connections → Table → Flow**

> Why a Solution first? Everything (flows, tables, app) lives inside it, so you can
> export the whole thing as one `.zip` (Managed Solution) and re-import to other
> environments. Building outside a solution = scattered components, painful to export.

---

## Clarification: Connectors

There are TWO unrelated "configs" in this project — don't confuse them:

| Config | Layer | Purpose | Needed for Cloud Flow? |
|---|---|---|---|
| `1_Skrypty_Python/.env` | Local Python | SMTP email + SQLite path for test data | No |
| Power Platform connections | Cloud | Outlook / Dataverse / AI Builder | **Yes** |
| Machine connector (PAD) | Bridge (RPA) | Cloud → local SQLite write | Later (point 5) |

For Cloud Flow 1 you only need the 3 cloud connections. The machine connector
(Power Automate Desktop) is set up later for the SQL sync — **not now**.

---

## Step 1: Create a Publisher (5 min)

A publisher defines the prefix on all your components (e.g. `es_clientid`).
Default publisher works, but a custom one looks professional in a portfolio.

1. Go to **make.powerapps.com**
2. Confirm correct environment (top-right) — use your default/dev environment
3. Left sidebar → **Solutions** → **... (more)** → **Publisher** → **New publisher**
   - Display name: `EnergoSmart`
   - Name: `EnergoSmart`
   - Prefix: `es`  ← components become `es_clientid`, `es_consumption`, etc.
   - Choice value prefix: leave default (e.g. `10000`)
4. **Save**

---

## Step 2: Create the Solution (3 min)

1. Left sidebar → **Solutions** → **New solution**
   - Display name: `EnergoSmart Automatization`
   - Name: `EnergoSmartAutomatization`
   - Publisher: select **EnergoSmart** (from Step 1)
   - Version: `1.0.0.0`
2. **Create**

You're now inside the solution. Everything you add from here lives in it.

---

## Step 3: Set Up Connections (10 min)

Connections authorize the flow to use each service. All cloud — just sign in.

1. Left sidebar → **Connections** → **New connection**
2. Create these three (search each by name, click **Create**, sign in with M365):

   **a) Office 365 Outlook**
   - Search "Office 365 Outlook" → Create → sign in
   - This lets the flow read your inbox + send emails

   **b) Microsoft Dataverse**
   - Search "Microsoft Dataverse" → Create → sign in
   - This lets the flow create/update reading records

   **c) AI Builder** (may appear as "AI Builder" or be built-in)
   - If listed, create it. Otherwise it's available automatically once you
     add an AI Builder action inside a flow.

3. Verify all show **green / Connected** under Connections.

> If AI Builder asks for a license: M365 trials usually include AI Builder
> credits. If not, you can swap the AI step for **"List rows in Excel table"**
> (parses Excel directly, no AI needed) for the Excel path. See SETUP_GUIDE.md.

---

## Step 4: Create the Dataverse Table (INSIDE the solution) (15 min)

> Important: create the table **from inside the solution** (not standalone),
> so it gets the `es_` prefix and is included in the export.

1. With the solution open → **New** → **Table** → **Table (advanced properties)**
   - Display name: `Reading`
   - Plural: `Readings`
   - (Schema name becomes `es_reading`)
2. **Save**, then add columns via **+ New column** for each:

| Display Name | Data Type | Notes |
|---|---|---|
| Client ID | Single line of text | Required |
| Client Name | Single line of text | |
| Reading Date | Date and Time | Required |
| Consumption kWh | Decimal Number | Required, 2 decimals |
| Month Avg kWh | Decimal Number | |
| Status | Choice (local) | Options below |
| AI Confidence | Decimal Number | 0-100 |
| Anomaly Reason | Multiple lines of text | |
| Source File URL | Single line of text (URL) | |
| Verified At | Date and Time | |

   Note: the table already has a primary column "Name" — you can use it as the
   Reading ID, or rename its display name to `Reading ID`.

3. **Status** column → type **Choice** → **New choice** with these options:
   - `Pending Review`
   - `Accepted`
   - `Rejected`
   - `Error`
   - `Synced`

   Set default = `Pending Review`.

4. **Save table**.

---

## Step 5: Build the Cloud Flow (INSIDE the solution)

Now follow **`SETUP_GUIDE.md`** — but create the flow from inside the solution:

- With solution open → **New** → **Automation** → **Cloud flow** → **Automated**
- Then follow SETUP_GUIDE.md from "2.2 Configure Trigger" onward.

This keeps the flow packaged in the solution for later export.

---

## Step 6 (Later): Machine Connector for SQL Bridge

This is point 5 of the architecture — **do it after** Flow 1 + Power Apps work:

- Install **Power Automate Desktop** on this machine
- Sign in with same M365 account → machine auto-registers
- Build `PAD_UpdateSQLDatabase` desktop flow with an **ODBC / SQL** action
  pointing at the local SQLite file (`2_Baza_Danych/energosmart_history.db`)
- Cloud Flow 2 calls this desktop flow (see `FLOW_2_STATUS_TRIGGER.md`)

> SQLite needs an ODBC driver (e.g. "SQLite ODBC Driver" by Ch. Werner) since
> Power Automate has no native SQLite connector. Details in `5_RPA_Desktop_Flow/`.

---

## Export the Solution (when done)

1. Solutions → select **EnergoSmart Automatization** → **Export solution**
2. Choose **Managed** (for distribution) or **Unmanaged** (for editing elsewhere)
3. Download the `.zip` → place in `4_Power_Platform_Solucja/EnergoSmart_Solution.zip`

---

## Order Recap

```
1. Publisher  (es prefix)
2. Solution   (container)
3. Connections (Outlook, Dataverse, AI Builder)  ← cloud only, no machine
4. Table       (es_reading, inside solution)
5. Flow 1      (Email Processor → see SETUP_GUIDE.md)
6. Flow 2      (Status trigger → see FLOW_2_STATUS_TRIGGER.md)
7. Power Apps  (review UI)
8. Machine connector + Desktop Flow  ← SQLite bridge, LAST
```

Next file to open: **`SETUP_GUIDE.md`** (Flow 1 build).
