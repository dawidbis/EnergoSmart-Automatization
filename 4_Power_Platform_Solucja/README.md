# Power Platform Solution: EnergoSmart Automatization

## Architecture Overview

```
[Email with Attachment]
       │
       ▼
[Cloud Flow 1: "EnergoSmart_EmailProcessor"]
  - Trigger: Office 365 (When new email arrives)
  - Parse attachment (Excel or PDF)
  - Call AI Builder for OCR/data extraction
  - Logic: Green/Yellow/Red path
       │
       ├──→ [Green] Auto-Accept (Confidence OK AND deviation <= 40%)
       │         ↓
       │    [Dataverse] Status = "Accepted"
       │         ↓
       │    [Power Automate Desktop] PAD_UpdateSQLDatabase → SQLite
       │       (called from Flow 1's Accept branch; manual accepts in
       │        Power Apps also route here, so both paths sync)
       │
       ├──→ [Yellow] Manual Review (low Confidence OR deviation > 40%)
       │         ↓        |Consumption - MonthlyAvg| / MonthlyAvg  (see AI_BUILDER_RETRAIN.md)
       │    [Dataverse] Status = "Pending Review"
       │         ↓
       │    [Power Apps] User verifies
       │
       └──→ [Red] Auto-Reject (Missing Critical Data)
              ↓
           [Send Email] to Client
```

## Setup Checklist

### Prerequisites
- [ ] M365 environment with Power Automate (Cloud flows)
- [ ] Power Apps (Model-driven app)
- [ ] Dataverse (auto-created with M365)
- [ ] AI Builder (preview license)
- [ ] Desktop Flow Premium (optional, for SQL integration)

### Step 1: Prepare Dataverse Table

1. **Create Table in Dataverse:**
   - Go to Power Apps → Tables → New Table
   - Name: `energosmart_readings`
   
2. **Add Columns:**
   | Column Name | Type | Required | Notes |
   |---|---|---|---|
   | Reading ID | Text | Yes | Unique client submission ID |
   | Client ID | Text | Yes | From database |
   | Client Name | Text | No | Reference |
   | Reading Date | Date/Time | Yes | When reading was taken |
   | Consumption kWh | Decimal | Yes | Energy consumption value |
   | Status | Option Set | Yes | "Pending Review", "Accepted", "Rejected", "Error" |
   | AI Confidence | Decimal | No | Score 0-100% |
   | Anomaly Reason | Text | No | Why anomaly was flagged |
   | Source File URL | Text | No | Link to Excel/PDF |
   | Verified By | Lookup (User) | No | Who verified it |
   | Verified At | Date/Time | No | When verified |

---

## Step 2: Create Cloud Flow 1 - Email Processor

### Flow Name
`EnergoSmart_EmailProcessor_Main`

### Trigger
**Office 365 Outlook** → When a new email arrives (v3)
- Folder: Inbox
- Include Attachments: Yes
- Only with Attachments: Yes

### Action 1: Initialize Variable
- Name: `FileContent`
- Type: String
- Value: (leave empty, will be populated)

### Action 2: For Each Attachment
Loop through `attachments()`

Inside loop:
1. **Get Attachment** (Office 365 Outlook)
   - Location: trigger output folder (from email)
   - File: `item()['Id']`
   - Store as `AttachmentContent`

2. **AI Builder - Analyze Document** (Extract data from image)
   - Document: `AttachmentContent`
   - Model: Use pre-built "Invoice Processing" or custom OCR model
   - Outputs:
     - `AI_ClientID`
     - `AI_Consumption`
     - `AI_Confidence`
     - `AI_Date`

3. **Condition: Check AI Confidence**
   ```
   If: AI_Confidence > 0.85
   AND Consumption > 0
   ```

#### If True (Green Path - Auto-Accept)
   a. **Create Record** (Dataverse)
      - Table: `energosmart_readings`
      - Set columns:
        - Reading ID: `AI_ClientID` + timestamp
        - Client ID: `AI_ClientID`
        - Reading Date: `AI_Date`
        - Consumption kWh: `AI_Consumption`
        - Status: "Accepted"
        - AI Confidence: `AI_Confidence`
        - Source File URL: attachment URL

#### If False (Yellow/Red Path - Needs Review)
   b. **Check if Critical Data Missing**
      ```
      If: AI_ClientID is empty OR AI_Consumption is empty
      ```
      
      - **If True (Red):** Send email to client: "Unreadable document"
      
      - **If False (Yellow):** Create Record (Dataverse)
        - Status: "Pending Review"
        - Anomaly Reason: "AI Confidence low OR Consumption anomaly"
        - AI Confidence: `AI_Confidence`

### Action 3: Send Confirmation Email
Send email back to sender with result summary.

---

## Step 3: Create Dataverse Flow (After Status Change)

### Flow Name
`EnergoSmart_OnReadingAccepted`

### Trigger
**Dataverse** → When a record is created or modified
- Table: `energosmart_readings`
- Change type: Created
- Scope: Organization

### Condition: Check Status
```
If Status = "Accepted"
```

### Action 1: Call Desktop Flow (Cloud flow calling RPA)
**Power Automate Desktop** → Run a desktop flow
- Flow: `PAD_UpdateSQLDatabase` (we'll create this later)
- Parameters:
  - `ClientID`: Reading ID
  - `Consumption`: Consumption kWh value
  - `ReadingDate`: Reading Date

### Action 2: Update Record
Set Status = "Synced" (after Desktop Flow succeeds)

---

## Step 4: Power Apps (Human-in-the-Loop)

Model-Driven App will query:
```sql
SELECT * FROM energosmart_readings WHERE Status = 'Pending Review'
```

Fields shown:
- Client ID, Consumption kWh, Source File (embedded viewer)
- AI Confidence, Anomaly Reason
- Buttons: "Accept" (→ Status = Accepted), "Reject" (→ Status = Rejected)

---

## Implementation Order

### Phase 1 (Today)
- [ ] Create Dataverse table with columns
- [ ] Build Cloud Flow 1 (Email Processor)
- [ ] Test with sample Excel/PDF from `3_Dokumenty_Testowe/`

### Phase 2 (Next)
- [ ] Setup AI Builder model (OCR for PDFs)
- [ ] Create Dataverse Flow (trigger on Status change)
- [ ] Build Power Apps interface

### Phase 3 (Final)
- [ ] Create Desktop Flow (SQL sync)
- [ ] Build Power BI dashboard
- [ ] End-to-end testing

---

## How to Export/Import This Solution

Later, you can export this as a **Managed Solution**:
1. Power Apps → Solutions → New Solution
2. Add: Cloud Flows, Dataverse tables, Apps
3. Export as .zip
4. Import in other environments

For now, we'll build it manually in the UI.

---

## Testing Data

Use files from `3_Dokumenty_Testowe/`:
- PDFs: Meter readings (test OCR)
- Excel: Direct data import (test parsing)

Send them via email to your test inbox and watch the flow execute.
