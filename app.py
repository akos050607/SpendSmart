import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from models import SessionLocal, Expense
from datetime import date
import time
import os
from extractor import extract_receipt_data

# --- PAGE SETTINGS ---
st.set_page_config(page_title="SpendSmart Dashboard", page_icon="💰", layout="wide")

# --- DATABASE FUNCTIONS ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_expenses(db: Session):
    return db.query(Expense).order_by(Expense.date.desc()).all()

# Only the last 10 items analyzed by AI
def get_ai_expenses(db: Session, limit=10):
    return db.query(Expense)\
             .filter(Expense.source == "AI")\
             .order_by(Expense.id.desc())\
             .limit(limit)\
             .all()

def save_expense(db: Session, data, source="Manual"):
    try:
        new_expense = Expense(
            merchant=data.get('merchant', 'Unknown'),
            total_amount=data.get('total_amount', 0),
            currency=data.get('currency', 'HUF'),
            category=data.get('category', 'Other'),
            date=data.get('date'),
            items=data.get('items', []),
            source=source
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

def update_database(db: Session, edited_df: pd.DataFrame):
    try:
        for index, row in edited_df.iterrows():
            expense_id = int(row["ID"])
            record = db.query(Expense).filter(Expense.id == expense_id).first()
            if record:
                record.merchant = row["Store"]
                record.total_amount = row["Amount"]
                record.category = row["Category"]
                record.currency = row["Currency"]
                record.date = row["Date"] # Now updating the date too!
        db.commit()
        return True
    except Exception as e:
        st.error(f"Error during saving: {e}")
        return False

# --- STYLE ---
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5c;
        padding: 10px;
        border-radius: 8px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- MAIN TITLE ---
st.title("💰 SpendSmart Auto-Pilot")

# --- SIDEBAR (Upload) ---
st.sidebar.header("⚡ Quick Upload")
uploaded_file = st.sidebar.file_uploader("Upload receipt photo", type=["jpg", "jpeg", "png"], key="uploader")

if uploaded_file is not None:
    st.sidebar.image(uploaded_file, caption="Preview", use_container_width=True)
    
    if st.sidebar.button("🚀 Start Processing", type="primary"):
        with st.sidebar.status("🤖 AI Processing...", expanded=True) as status:
            try:
                # 1. Save image
                temp_filename = "temp_receipt.jpg"
                with open(temp_filename, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 2. AI Analysis
                status.write("Sending image to AI...")
                extracted_data = extract_receipt_data(temp_filename)
                
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                
                # 3. Save with source="AI" label
                if extracted_data:
                    status.write("Saving to database...")
                    db = next(get_db())
                    
                    if save_expense(db, extracted_data, source="AI"):
                        status.update(label="✅ SUCCESS! Saved.", state="complete", expanded=False)
                        time.sleep(1)
                        st.rerun()
                    else:
                        status.update(label="❌ Database error", state="error")
                else:
                    status.update(label="❌ AI error: No data received", state="error")
            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.sidebar.error(f"{e}")

# --- LOAD DATA ---
db = next(get_db())
all_expenses = get_all_expenses(db)
ai_expenses = get_ai_expenses(db)

# Main list DataFrame
df_all = pd.DataFrame()
if all_expenses:
    df_all = pd.DataFrame([{
        "ID": e.id, "Date": e.date, "Store": e.merchant, 
        "Amount": float(e.total_amount), "Currency": e.currency, "Category": e.category
    } for e in all_expenses])

# AI list DataFrame (Now all columns are included!)
df_ai = pd.DataFrame()
if ai_expenses:
    df_ai = pd.DataFrame([{
        "ID": e.id, 
        "Date": e.date,          # <--- INCLUDED
        "Store": e.merchant, 
        "Amount": float(e.total_amount), 
        "Currency": e.currency,    # <--- INCLUDED
        "Category": e.category,
    } for e in ai_expenses])

# --- LAYOUT: TWO COLUMNS ---
col_main, col_right = st.columns([2.5, 1.5]) # Slightly widened on the right (1.2 -> 1.5)

# >>> RIGHT COLUMN: AI LOG (Detailed) <<<
with col_right:
    st.subheader("🤖 AI Log (Last 10)")
    st.caption("Here you can see what the machine read. Correct it if it made a mistake!")
    
    if not df_ai.empty:
        edited_ai = st.data_editor(
            df_ai,
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None, # Still hide this as it's technical data
                "Date": st.column_config.DateColumn("Date", width="small"), # Visible!
                "Currency": st.column_config.TextColumn("Currency", width="small"), # Visible!
                "Store": st.column_config.TextColumn("Store", width="medium"),
                "Amount": st.column_config.NumberColumn("Amount", format="%d"),
                "Category": st.column_config.SelectboxColumn(
                    "Cat.",
                    options=["Food", "Travel", "Entertainment", "Utilities", "Other"],
                    width="medium"
                )
            },
            key="ai_editor"
        )
        
        if st.button("Save Corrections (AI Section)", type="primary"):
            if update_database(db, edited_ai):
                st.toast("✅ Corrected!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("No data uploaded by AI yet.")

# >>> LEFT COLUMN: STATISTICS AND FULL LIST <<<
with col_main:
    if not df_all.empty:
        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Spending", f"{df_all['Amount'].sum():,.0f} Ft")
        c2.metric("Transactions", f"{len(df_all)} pcs")
        c3.metric("Average", f"{df_all['Amount'].mean():,.0f} Ft")
        
        st.markdown("---")

        # Charts
        gc1, gc2 = st.columns(2)
        with gc1:
            fig_pie = px.pie(df_all, values='Amount', names='Category', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)
        with gc2:
            daily = df_all.groupby("Date")["Amount"].sum().reset_index()
            fig_bar = px.bar(daily, x="Date", y="Amount")
            fig_bar.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=250)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        
        # Search and Full List
        st.subheader("🗂️ Full Archive")
        search_term = st.text_input("Search:", placeholder="Store name...")
        
        if search_term:
            df_filtered = df_all[df_all["Store"].str.contains(search_term, case=False, na=False)]
        else:
            df_filtered = df_all

        st.dataframe(
            df_filtered, 
            hide_index=True, 
            use_container_width=True,
            column_config={"ID": None}
        )

    else:
        st.info("No data. Upload something!")