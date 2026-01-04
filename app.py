import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- CONFIGURATION & DATABASE CONNECTION ---
st.set_page_config(page_title="Laundry Cloud ERP", layout="wide")

def get_gsheet_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_info = st.secrets["connections_gsheets"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    # Replace with your actual Sheet Name
    return client.open("Laundry_Management_DB")

client = get_gsheet_client()

def get_sheet_data(sheet_name):
    sheet = client.worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records()), sheet

# --- INITIALIZE SESSION STATE ---
if 'user' not in st.session_state:
    st.session_state.user = None
if 'customer' not in st.session_state:
    st.session_state.customer = None
if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- ACCOUNTING HELPERS ---
def add_ledger_entry(debit, credit, amount, desc, ref_id):
    _, sheet = get_sheet_data("Ledger")
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        debit, credit, amount, desc, ref_id
    ])

def update_customer_balance(cust_id, amount_change, op_id, type_str):
    df, sheet = get_sheet_data("Customers")
    idx = df[df['ID'] == cust_id].index[0]
    old_balance = float(df.at[idx, 'Balance'])
    new_balance = old_balance + amount_change
    
    # Update Sheet
    sheet.update_cell(idx + 2, 6, new_balance) # Col 6 is Balance
    
    # Audit Trail
    _, hist_sheet = get_sheet_data("BalanceHistory")
    hist_sheet.append_row([
        cust_id, amount_change, new_balance, type_str, op_id, datetime.now().isoformat()
    ])
    return new_balance

# --- AUTHENTICATION ---
def login_page():
    st.title("🧺 Laundry Cloud ERP")
    with st.form("login_form"):
        u_id = st.text_input("Operator ID")
        u_pw = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Hardcoded Super Admin check
            if u_id == "LU-032" and u_pw == "lily5566":
                st.session_state.user = {"id": u_id, "name": "Super Admin", "role": "Admin"}
                st.rerun()
            
            # Sheet Check
            users_df, _ = get_sheet_data("Users")
            match = users_df[(users_df['UserID'] == u_id) & (users_df['Password'] == str(u_pw))]
            if not match.empty:
                user_data = match.iloc[0]
                st.session_state.user = {"id": u_id, "name": user_data['Name'], "role": user_data['Role']}
                st.rerun()
            else:
                st.error("Invalid Credentials")

if st.session_state.user is None:
    login_page()
    st.stop()

# --- TOP BAR & ATTENDANCE ---
st.sidebar.title(f"👤 {st.session_state.user['name']}")
st.sidebar.write(f"Role: {st.session_state.user['role']}")

def handle_attendance():
    _, sheet = get_sheet_data("Attendance")
    if st.button("🕒 Clock In (刷上班卡)"):
        sheet.append_row([st.session_state.user['id'], datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M:%S"), ""])
        st.success("Clocked In!")

    if st.button("🚪 Clock Out (刷下班卡)"):
        df = pd.DataFrame(sheet.get_all_records())
        today = datetime.now().strftime("%Y-%m-%d")
        mask = (df['UserID'] == st.session_state.user['id']) & (df['Date'] == today) & (df['TimeOut'] == "")
        if any(mask):
            row_idx = df[mask].index[0] + 2
            sheet.update_cell(row_idx, 4, datetime.now().strftime("%H:%M:%S"))
            st.session_state.user = None
            st.rerun()

# --- NAVIGATION ---
menu = ["New Order", "Work Management", "Customer System", "Financial Reports"]
choice = st.sidebar.radio("Navigation", menu)

# --- PAGE: CUSTOMER SYSTEM ---
if choice == "Customer System":
    st.header("👥 Customer Management")
    
    # Search
    search_q = st.text_input("Search (Name/Phone)")
    cust_df, cust_sheet = get_sheet_data("Customers")
    
    if search_q:
        results = cust_df[cust_df['Name'].str.contains(search_q) | cust_df['Mobile'].astype(str).str.contains(search_q)]
        st.dataframe(results)
        if not results.empty:
            if st.button("Select Customer"):
                st.session_state.customer = results.iloc[0].to_dict()
                st.success(f"Selected: {st.session_state.customer['Name']}")

    # Top-Up (Admin Only)
    if st.session_state.customer and st.session_state.user['role'] == 'Admin':
        st.subheader(f"Top-Up for {st.session_state.customer['Name']}")
        amount = st.number_input("Amount", min_value=0)
        if st.button("Confirm Top-Up"):
            new_bal = update_customer_balance(st.session_state.customer['ID'], amount, st.session_state.user['id'], "TopUp")
            add_ledger_entry("Cash", "Unearned Revenue", amount, f"Top up: {st.session_state.customer['ID']}", "TOPUP")
            st.success(f"New Balance: ${new_bal}")

# --- PAGE: NEW ORDER ---
elif choice == "New Order":
    if not st.session_state.customer:
        st.warning("Please select a customer first in Customer System.")
    else:
        st.header(f"New Order: {st.session_state.customer['Name']}")
        st.info(f"Current Balance: ${st.session_state.customer['Balance']}")

        with st.form("item_entry"):
            col1, col2, col3 = st.columns(3)
            i_type = col1.selectbox("Service", ["Dry Clean", "Wash & Fold", "Ironing"])
            i_qty = col2.number_input("Qty", min_value=1, value=1)
            i_price = col3.number_input("Price per Unit", min_value=0.0, value=10.0)
            i_color = col1.text_input("Color")
            i_pattern = col2.text_input("Pattern")
            i_note = col3.text_input("Defects/Notes")
            
            if st.form_submit_button("Add to Cart"):
                st.session_state.cart.append({
                    "Type": i_type, "Qty": i_qty, "Price": i_price,
                    "Color": i_color, "Pattern": i_pattern, "Note": i_note
                })

        if st.session_state.cart:
            st.table(st.session_state.cart)
            total = sum(item['Qty'] * item['Price'] for item in st.session_state.cart)
            st.subheader(f"Total: ${total}")

            if st.button("Proceed to Payment"):
                order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                # Logic: Payment
                payment_method = st.radio("Method", ["Cash", "Deduct Balance"])
                status = "Paid"
                
                if payment_method == "Deduct Balance":
                    bal = float(st.session_state.customer['Balance'])
                    if bal >= total:
                        update_customer_balance(st.session_state.customer['ID'], -total, st.session_state.user['id'], "Order")
                        add_ledger_entry("Unearned Revenue", "Laundry Revenue", total, f"Order {order_id}", order_id)
                    else:
                        st.error("Insufficient Balance!")
                        st.stop()
                else:
                    add_ledger_entry("Cash", "Laundry Revenue", total, f"Order {order_id}", order_id)

                # Save Order
                _, o_sheet = get_sheet_data("Orders")
                o_sheet.append_row([order_id, st.session_state.customer['ID'], total, total, "Paid", "No", datetime.now().isoformat(), st.session_state.user['id']])
                
                # Save Individual Items (Tagging)
                _, item_sheet = get_sheet_data("OrderItems")
                for item in st.session_state.cart:
                    for i in range(item['Qty']):
                        tag_id = f"{order_id}-{i+1:02d}"
                        item_sheet.append_row([tag_id, order_id, item['Type'], item['Price'], item['Color'], item['Pattern'], item['Note'], "In"])
                
                st.success("Order Created! Printing Receipt...")
                st.session_state.cart = []
                st.balloons()

# --- PAGE: WORK MANAGEMENT ---
elif choice == "Work Management":
    tab1, tab2 = st.tabs(["Inventory (In-Process)", "Pickup (销单)"])
    
    with tab1:
        items_df, item_sheet = get_sheet_data("OrderItems")
        pending = items_df[items_df['Status'] == "In"]
        st.write("Items currently in shop:")
        edited_df = st.data_editor(pending)
        if st.button("Update Status to Ready"):
            # Simplified logic: Update all to Cleaned for this demo
            st.info("In a full system, we would map the row indices back to GSheets to update specific items.")

    with tab2:
        search_pickup = st.text_input("Customer Name for Pickup")
        if search_pickup:
            # Join logic would go here
            st.write("Searching for items ready for pickup...")

# --- PAGE: FINANCIAL REPORTS ---
elif choice == "Financial Reports":
    st.header("📊 Daily Closing Report")
    ledger_df, _ = get_sheet_data("Ledger")
    ledger_df['Date'] = pd.to_datetime(ledger_df['Date'])
    
    today = datetime.now().date()
    daily = ledger_df[ledger_df['Date'].dt.date == today]
    
    col1, col2 = st.columns(2)
    col1.metric("Total Revenue Today", f"${daily[daily['Account_Credit'] == 'Laundry Revenue']['Amount'].sum()}")
    col2.metric("Cash Inflow (Sales + Top-ups)", f"${daily[daily['Account_Debit'] == 'Cash']['Amount'].sum()}")
    
    st.subheader("Transaction Log")
    st.dataframe(daily)

handle_attendance()
