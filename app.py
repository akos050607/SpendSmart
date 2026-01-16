import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from models import SessionLocal, Expense
from datetime import date
import time
import os
from extractor import extract_receipt_data  # Az AI motorunk importálása

# --- OLDAL BEÁLLÍTÁSOK ---
st.set_page_config(page_title="SpendSmart Dashboard", page_icon="💰", layout="wide")

# --- ADATBÁZIS FÜGGVÉNYEK ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_all_expenses(db: Session):
    return db.query(Expense).order_by(Expense.date.desc()).all()

def save_expense(db: Session, data):
    new_expense = Expense(
        merchant=data.get('merchant', 'Unknown'),
        total_amount=data.get('total_amount', 0),
        currency=data.get('currency', 'HUF'),
        category=data.get('category', 'Other'),
        date=data.get('date'),
        items=data.get('items', [])
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

def update_database(db: Session, edited_df: pd.DataFrame):
    try:
        for index, row in edited_df.iterrows():
            expense_id = int(row["ID"])
            record = db.query(Expense).filter(Expense.id == expense_id).first()
            if record:
                record.merchant = row["Merchant"]
                record.total_amount = row["Amount"]
                record.category = row["Category"]
                record.currency = row["Currency"]
        db.commit()
        return True
    except Exception as e:
        st.error(f"Hiba a mentésnél: {e}")
        return False

def delete_expense(db: Session, expense_id: int):
    record = db.query(Expense).filter(Expense.id == expense_id).first()
    if record:
        db.delete(record)
        db.commit()
        return True
    return False

# --- STÍLUS JAVÍTÁS (DARK MODE KOMPATIBILIS) ---
# Most sötét hátteret adunk a kártyáknak, így olvasható lesz a fehér betű
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #262730; /* Sötétszürke háttér */
        border: 1px solid #464b5c; /* Finom keret */
        padding: 15px;
        border-radius: 10px;
        color: white; /* Fehér szöveg */
    }
    </style>
    """, unsafe_allow_html=True)

# --- OLDALSÁV (Képfeltöltés visszahozása) ---
st.sidebar.header("🧾 Új Kiadás")

# Session state a beolvasott adatoknak
if 'scanned_data' not in st.session_state:
    st.session_state.scanned_data = None

uploaded_file = st.sidebar.file_uploader("📸 Blokk fotó feltöltése", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.sidebar.image(uploaded_file, caption="Feltöltött blokk", use_container_width=True)
    
    if st.sidebar.button("🚀 Elemzés AI-val"):
        with st.spinner("AI dolgozik..."):
            # Ideiglenes mentés
            temp_filename = "temp_receipt.jpg"
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # AI hívása
            extracted_data = extract_receipt_data(temp_filename)
            os.remove(temp_filename) # Törlés
            
            if extracted_data:
                st.session_state.scanned_data = extracted_data
                st.sidebar.success("Sikeres elemzés!")
            else:
                st.sidebar.error("Nem sikerült adatot kinyerni.")

# Ha van beolvasott adat, megjelenítjük az oldalsávban jóváhagyásra
if st.session_state.scanned_data:
    st.sidebar.markdown("---")
    st.sidebar.write("### ✅ Ellenőrzés")
    
    with st.sidebar.form("ai_review_form"):
        scanned = st.session_state.scanned_data
        
        # Form kitöltése az AI adataival
        s_merchant = st.text_input("Bolt", scanned.get('merchant', ''))
        s_amount = st.number_input("Összeg", value=float(scanned.get('total_amount', 0.0)))
        s_date = st.text_input("Dátum (YYYY-MM-DD)", scanned.get('date', str(date.today())))
        s_category = st.selectbox("Kategória", ["Food", "Travel", "Entertainment", "Utilities", "Other"], index=0)
        
        if st.form_submit_button("💾 Mentés az adatbázisba"):
            final_data = {
                "merchant": s_merchant,
                "total_amount": s_amount,
                "date": s_date,
                "currency": "HUF",
                "category": s_category,
                "items": scanned.get('items', [])
            }
            
            db = next(get_db())
            save_expense(db, final_data)
            st.session_state.scanned_data = None # Töröljük a formot
            st.success("Sikeresen mentve!")
            st.rerun()

# --- FŐ CÍMSOR ---
st.title("💰 SpendSmart Vezérlőpult")
st.markdown("Automata költéskövetés AI segítségével")
st.markdown("---")

# Adatbázis lekérdezés
db = next(get_db())
expenses = get_all_expenses(db)

if expenses:
    data = [
        {
            "ID": e.id,
            "Date": e.date,
            "Merchant": e.merchant,
            "Amount": float(e.total_amount),
            "Currency": e.currency,
            "Category": e.category
        } 
        for e in expenses
    ]
    df = pd.DataFrame(data)

    # --- 1. KPI KÁRTYÁK ---
    col1, col2, col3, col4 = st.columns(4)
    total_spent = df["Amount"].sum()
    avg_spent = df["Amount"].mean()
    
    col1.metric("Összes Költés", f"{total_spent:,.0f} Ft")
    col2.metric("Tranzakciók", f"{len(df)} db")
    col3.metric("Átlagos Kosár", f"{avg_spent:,.0f} Ft")
    last_date = df["Date"].iloc[0] if not df.empty else "-"
    col4.metric("Utolsó Vásárlás", str(last_date))

    st.markdown("---")

    # --- 2. VIZUALIZÁCIÓ ---
    c1, c2 = st.columns([1, 2])

    with c1:
        st.subheader("Kategóriák")
        fig_pie = px.pie(
            df, values='Amount', names='Category', hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Napi Trend")
        daily_data = df.groupby("Date")["Amount"].sum().reset_index()
        fig_line = px.bar(daily_data, x="Date", y="Amount")
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("---")

    # --- 3. SZERKESZTHETŐ TÁBLA ---
    st.subheader("📝 Részletes Lista (Szerkeszthető)")
    
    edited_df = st.data_editor(
        df, hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Amount": st.column_config.NumberColumn(format="%d Ft"),
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=["Food", "Travel", "Entertainment", "Utilities", "Other"],
                required=True
            )
        },
        use_container_width=True,
        key="data_editor"
    )

    col_save, col_del = st.columns([1, 4])
    with col_save:
        if st.button("💾 Változások Mentése", type="primary"):
            if update_database(db, edited_df):
                st.success("Sikeres mentés!")
                time.sleep(1)
                st.rerun()

    with st.expander("🗑️ Tétel törlése"):
        del_id = st.number_input("ID törlése:", step=1, min_value=1)
        if st.button("Törlés"):
            if delete_expense(db, del_id):
                st.warning("Törölve.")
                time.sleep(1)
                st.rerun()
else:
    st.info("Még nincs adat. Használd a bal oldali sávot blokk feltöltéséhez!")