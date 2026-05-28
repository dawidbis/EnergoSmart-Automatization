# EnergoSmart Cloud Flow - Step-by-Step Setup Guide

## Part 1: Prepare Dataverse Table (10 min)

### 1.1 Create Table
1. Go to **Power Apps** (make.powerapps.com)
2. Select your environment (default)
3. Left sidebar → **Tables** → **New table**
4. Name: `energosmart_readings`
5. Display name: `EnergoSmart Reading`
6. Plural name: `EnergoSmart Readings`
7. Click **Create**

### 1.2 Add Columns to Table

After table is created, add these columns:

| # | Column Name | Type | Format | Required |
|---|---|---|---|---|
| 1 | Reading ID | Text | Email | Yes |
| 2 | Client ID | Text | Text | Yes |
| 3 | Client Name | Text | Text | No |
| 4 | Reading Date | Date and Time | Date and Time | Yes |
| 5 | Consumption kWh | Decimal | ≥ 2 decimal places | Yes |
| 6 | Month Avg kWh | Decimal | ≥ 2 decimal places | No |
| 7 | Status | Choice | (See below) | Yes |
| 8 | AI Confidence | Decimal | 0-100 | No |
| 9 | Anomaly Reason | Text (Multiple lines) | - | No |
| 10 | Source File URL | Text (URL) | - | No |
| 11 | Verified By | Lookup (User) | - | No |
| 12 | Verified At | Date and Time | Date and Time | No |

**For Status column (Choice), add options:**
- Accepted
- Pending Review
- Rejected
- Error
- Synced

**Click Save** after adding each column.

---

## Part 2: Create Cloud Flow (20 min)

### 2.1 Create Flow
1. Go to **Power Automate** (make.powerautomate.com)
2. **Create** → **Cloud flow** → **Automated cloud flow**
3. Name: `EnergoSmart_EmailProcessor_Main`
4. Trigger: Type `outlook` → select **When a new email arrives (V3)**
5. Click **Create**

### 2.2 Configure Trigger

In the trigger box, set:
- **Folder**: Inbox
- **Include Attachments**: Yes
- **Only with Attachments**: Yes

---

### 2.3 Add Action 1: Initialize Variable

1. Click **New step** → **Initialize variable**
2. Name: `ProcessedCount`
3. Type: `Integer`
4. Value: `0`

---

### 2.4 Add Action 2: Loop Through Attachments

1. **New step** → **Apply to each**
2. In "Select an output from previous steps": `attachments` (from trigger)
3. Rename to: `For Each Attachment`

Inside the loop, add these sub-actions:

#### 2.4.1 Get Attachment Content
1. **New step inside loop** → **Outlook** → **Get attachment (V2)**
2. Folder Path: `Inbox`
3. Item ID: (empty for now, we'll configure later)
4. File: `Id` (from current item)

#### 2.4.2 Call AI Builder
1. **New step** → Search `ai builder`
2. Select **Analyze documents with AI Builder** (or similar)
3. In Document field: `Content` (output from Get attachment)
4. Model: **Try one of these:**
   - "Invoice processing" (pre-built)
   - Or create custom form processing model in Power Apps

**AI Builder outputs should extract:**
- Client ID (from document)
- Consumption (kWh value)
- Reading Date
- Confidence score (0-1 or 0-100)

#### 2.4.3 Parse AI Output (Optional - for structured data)
1. **New step** → **Parse JSON**
2. Content: (output from AI Builder)
3. Schema:
```json
{
  "type": "object",
  "properties": {
    "ClientID": {"type": "string"},
    "Consumption": {"type": "number"},
    "ReadingDate": {"type": "string"},
    "Confidence": {"type": "number"}
  }
}
```

---

### 2.5 Add Action 3: Green/Yellow/Red Path Logic

#### Green Path (Auto-Accept)

1. **New step** → **Condition**
2. Set condition:
   ```
   AND
   - AI Confidence (from parser) is greater than 0.85
   - Consumption is greater than 0
   ```

**If True (Auto-Accept):**
1. **New step** → **Dataverse** → **Create a record**
2. Table: `energosmart_readings`
3. Fill in columns:
   - **Reading ID**: `concat(AI_ClientID, '_', utcNow())`
   - **Client ID**: `AI_ClientID`
   - **Reading Date**: `AI_Date`
   - **Consumption kWh**: `AI_Consumption`
   - **Status**: `Accepted`
   - **AI Confidence**: `multiply(AI_Confidence, 100)` (convert to 0-100)
   - **Source File URL**: attachment content URL

2. **New step** → **Send an email (V2)**
   - To: `From` (email trigger output)
   - Subject: `EnergoSmart: Reading accepted`
   - Body: `Your energy reading has been accepted and is being processed.`

---

#### Yellow/Red Path (Manual Review or Rejection)

**If False (from above condition):**

1. **New step** → **Condition** (nested)
2. Check if critical data missing:
   ```
   OR
   - AI_ClientID is empty
   - AI_Consumption is null
   ```

**If True (Red Path - Auto-Reject):**
1. **New step** → **Send an email (V2)**
   - To: `From`
   - Subject: `EnergoSmart: Document unreadable`
   - Body: `Your document could not be processed. Ensure it contains clear Client ID and consumption reading.`

**If False (Yellow Path - Needs Review):**
1. **New step** → **Create a record** (Dataverse)
   - Table: `energosmart_readings`
   - **Reading ID**: `concat(AI_ClientID, '_', utcNow())`
   - **Status**: `Pending Review`
   - **AI Confidence**: `multiply(AI_Confidence, 100)`
   - **Anomaly Reason**: `"Low AI confidence or potential consumption anomaly - requires manual review"`
   - (other fields as before)

2. **New step** → **Send an email (V2)**
   - Subject: `EnergoSmart: Reading pending review`
   - Body: `Your reading is being verified by our team.`

---

### 2.6 Save Flow

1. Click **Save**
2. Toggle **On** to activate the flow

---

## Part 3: Test the Flow (10 min)

### 3.1 Send Test Email

1. Go to your email inbox
2. Create **new email** to yourself
3. **Attach** one of the test documents from `3_Dokumenty_Testowe/`:
   - `CLIENT_0044_Report_20260528.xlsx` (Excel)
   - OR `CLIENT_0025_MeterReading_20260528.pdf` (PDF)
4. Send email

### 3.2 Monitor Flow Execution

1. Go back to **Power Automate** → Your flow
2. Click **28-day run history** at top
3. You should see your flow trigger
4. Click on run to see **action details**

### 3.3 Check Dataverse Results

1. Go to **Power Apps** → **Tables** → `energosmart_readings`
2. Click **Edit data** or **Data**
3. You should see a new record with:
   - Client ID (extracted)
   - Consumption (extracted)
   - Status (either "Accepted" or "Pending Review")
   - AI Confidence score

---

## Part 4: Next Steps (After Testing)

### What's Working Now:
✅ Emails arrive with attachments
✅ AI extracts data (or shows errors)
✅ Records created in Dataverse
✅ Clients notified

### What's Next:
- [ ] **Power Apps Interface** - create model-driven app to review "Pending Review" records
- [ ] **Desktop Flow (RPA)** - when status = "Accepted", push to SQL database
- [ ] **Power BI** - dashboard showing processing stats

---

## Troubleshooting

### Flow doesn't trigger
- **Check:** Outlook connection authorized? (flow should prompt)
- **Check:** "Only with Attachments" = Yes?

### AI Builder not extracting data
- **Check:** AI Builder model deployed in your environment
- **Option:** Use built-in "Invoice Processing" or create custom form model
- **Fallback:** For Excel, use **"Parse Excel table"** action instead

### Dataverse record not created
- **Check:** Table exists and columns match exactly
- **Check:** All required fields have values
- **Check:** Connection authorized (flow will prompt)

### Email not received
- **Check:** You're using same email address as trigger
- **Check:** Check spam folder

---

## File References
- Flow definition: `Flow_Blueprint_EmailProcessor.json` (reference only)
- Test documents: `../3_Dokumenty_Testowe/CLIENT_*.xlsx` and `*.pdf`
- Database: `../2_Baza_Danych/energosmart_history.db`

---

**Estimated time to complete: 30-40 minutes (first time)**
