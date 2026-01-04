# Role Definition
You are a Senior Full-Stack Developer expert in Python, Streamlit, and Accounting Systems.
We are building a "Cloud-Based Laundry Management System (Web App)" that connects to Google Sheets as the backend database.
The system must be responsive (mobile-friendly for owners, desktop-friendly for staff).

# Core Philosophy: Double-Entry Bookkeeping & Audit Trails
Every financial action (Order Created, Payment Received, Top-up, Expense) must generate a corresponding entry in the `Ledger` sheet.
Every sensitive action (Top-up, Edit Price, Void Order) must record the `OperatorID`.

# 1. System Configuration & Authentication
- **Framework**: Streamlit.
- **Database**: Google Sheets API (use `st.secrets` for credentials, using `gspread` or `streamlit-google-sheets`).
- **Authentication**:
  - Login Page is the only entry point.
  - **Super Admin**: ID `LU-032`, Password `lily5566`.
  - Validate against `Users` sheet.
  - Store session state: `user_id`, `role` (Admin/Staff), `name`.

# 2. Layout & Employee Attendance (Time Clock)
- **Top Bar (Always Visible)**:
  - Display: Current Date/Time (Real-time or update on action).
  - Display: Current Operator Name.
  - **Action**: "Clock Out (刷下班卡)" button -> Records time in `Attendance`.
- **Clock-In Logic**:
  - Upon successful login, check `Attendance` sheet for today.
  - If no record found for this user today, show a prominent "Clock In (刷上班卡)" button/modal.

# 3. Customer & Membership System
- **Search Logic**:
  - Input field to search by `Name` OR `Mobile Phone` OR `Home Phone`.
- **Customer Form**:
  - Fields: Name, Mobile Phone, Home Phone, Address, Important Notes.
  - **Balance Display**: Show current Prepaid Balance (Read-Only).
- **Top-Up Function (儲值)**:
  - Button: "Top Up".
  - **Security**: Only enabled if `Role == 'Admin'` or authorized.
  - **Logic**: Input Amount -> Add to Balance.
  - **Ledger**: Debit Cash, Credit Unearned Revenue (Liability).
  - **Log**: Record in `BalanceHistory` with OperatorID.

# 4. Order Entry & Checkout (The Core)
*Only accessible after selecting a customer.*
- **Step 1: Item Entry**:
  - Input: Service Type (Dry/Wash/Iron), Quantity, Price (Default but editable), Color, Pattern, Defects/Notes.
  - **Tagging Logic**:
    - Generate `OrderID` (e.g., `YYYYMMDD-SEQ`).
    - **CRITICAL**: Generate unique `TagID` for **EACH PIECE**.
    - If user inputs "3 Shirts", generate 3 separate rows in backend: `...-01`, `...-02`, `...-03`.
- **Step 2: Payment Modal**:
  - Show Total Amount.
  - **Payment Methods**:
    1. **Cash**: Status = Paid.
    2. **Unpaid**: Status = Unpaid.
    3. **Deduct Balance**:
       - Calculate `Remaining = Balance - Total`.
       - If `Remaining >= 0`: Status = Paid, Update Customer Balance.
       - If `Remaining < 0`: Deduct ALL Balance (Balance=0), Status = Partially Paid, Show `Outstanding Amount`.
- **Step 3: Printing (Receipt)**:
  - Generate a clean UI view (or HTML block) for printing.
  - **Customer Copy**: Details + Financials (Total, Paid, Old Balance, Deduction, New Balance).
  - **Store Copy**: Order details.

# 5. Inventory & Workflow (Life Cycle)
Create a page "Work Management" with 3 tabs:
1. **In-Process (Inventory)**:
   - List items where Status != "PickedUp".
   - **Action**: Checkbox to mark as "Cleaned/Ready" (批量勾選).
2. **Pickup Verification (銷單)**:
   - Filter by Customer/Phone/Order.
   - Show list of "Ready" items.
   - **Action**: "Confirm Pickup".
   - **Logic**: If Order is `Unpaid` or `Partially Paid`, FORCE payment prompt before allowing pickup.
   - Update Status to "PickedUp".
3. **Consumables**: Simple tracker for store supplies.

# 6. Financial Reporting (Daily Closing)
- **Daily Report Page**:
  - Filter by Date.
  - **Display Metrics**:
    - **Total Orders**: Count & Amount (e.g., "Huang Xiao-Ming: 20 pcs").
    - **Breakdown**: Dry Clean Qty/Amt, Wash Qty/Amt.
    - **Top-Up Total**: Total cash received from deposits.
    - **Voided Orders**: List invalid orders.
    - **Net Cash In Drawer**: Cash Sales + Top-Ups + Balance Dues Collected.

# Data Schema (Google Sheets Structure)
*The code must initialize these headers if sheets are empty.*
1. `Users`: UserID, Password, Role, Name.
2. `Attendance`: UserID, Date, TimeIn, TimeOut.
3. `Customers`: ID, Name, Mobile, HomePhone, Address, Balance, Notes.
4. `Orders`: OrderID, CustomerID, TotalAmount, PaidAmount, PaymentStatus, IsVoid, Date, CreatedBy.
5. `OrderItems`: TagID, OrderID, ItemType, Price, Color, Pattern, Note, Status (In/Cleaned/PickedUp).
6. `BalanceHistory`: CustomerID, ChangeAmount, NewBalance, Type, OperatorID, Date.
7. `Ledger`: Date, Account_Debit, Account_Credit, Amount, Description, ReferenceID.

# Output Requirements
1. Provide the complete `app.py` code.
2. Provide a `requirements.txt` list.
3. Explain how to set up `st.secrets` with the Google Service Account JSON.
