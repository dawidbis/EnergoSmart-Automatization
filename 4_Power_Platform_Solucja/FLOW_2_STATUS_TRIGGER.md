# Cloud Flow 2: EnergoSmart_OnReadingAccepted

## Purpose
Triggered when a reading is accepted in Dataverse. Calls Desktop Flow (RPA) to insert data into SQL database.

## Setup

### 1. Create Flow

1. **Power Automate** → **Create** → **Cloud flow** → **Automated cloud flow**
2. Name: `EnergoSmart_OnReadingAccepted`
3. Trigger: **Dataverse** → **When a record is created** (search "dataverse")
4. Click **Create**

### 2. Configure Trigger

In trigger box:
- **Table**: `energosmart_readings` (select from dropdown)
- **Scope**: `Organization` (allows any user to trigger)

---

## 3. Add Condition: Check Status

1. **New step** → **Condition**
2. Set:
   ```
   If [Status] equals Accepted
   ```
   (Select Status column from dynamic content)

---

## 4. If True: Call Desktop Flow

**Inside the "If True" branch:**

1. **New step** → **Power Automate Desktop** → **Run a desktop flow**
2. Select Desktop Flow: `PAD_UpdateSQLDatabase` (create this later in Power Automate Desktop)
3. Pass these inputs:
   - **ClientID**: `Reading ID` (from record)
   - **Consumption**: `Consumption kWh` (from record)
   - **ReadingDate**: `Reading Date` (from record)
   - **SourceFile**: `Source File URL` (from record)

### Alternative: If Desktop Flow doesn't exist yet

You can **skip Desktop Flow** and just call SQL directly:

1. **New step** → **SQL Server** → **Execute a SQL query**
2. Server: (your local server or Azure SQL)
3. Database: `energosmart_history`
4. Query:
   ```sql
   INSERT INTO energosmart_history 
   (client_id, reading_date, consumption_kwh, month_avg_kwh, status, inserted_at)
   VALUES 
   (@client_id, @date, @consumption, NULL, 'validated', GETDATE())
   ```
5. Parameters:
   - `@client_id` = Reading ID
   - `@date` = Reading Date
   - `@consumption` = Consumption kWh

---

## 5. Add Step: Update Record Status

After Desktop Flow succeeds:

1. **New step** → **Dataverse** → **Update a record**
2. Table: `energosmart_readings`
3. Row ID: `Record ID` (from trigger)
4. Set columns:
   - **Status**: `Synced`
   - **Verified At**: `utcNow()`

---

## 6. Save & Activate

Click **Save** → Toggle **On**

---

## Testing

1. Go to Dataverse → `energosmart_readings`
2. Create manual record with:
   - Client ID: `CLIENT_0025`
   - Consumption kWh: `12345.67`
   - Status: `Pending Review`
3. Change Status to `Accepted`
4. Flow should trigger automatically
5. Check if record Status changed to `Synced`

---

## Next: Power Apps Interface

Once both flows work, create Power Apps model-driven app:
- View records with Status = "Pending Review"
- Show attachment preview
- Button to change status (which triggers Flow 2)

## Also See

- `README.md` - Architecture overview
- `SETUP_GUIDE.md` - Flow 1 (Email Processor) setup
