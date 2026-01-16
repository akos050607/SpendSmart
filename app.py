import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy.orm import Session
from models import SessionLocal, Expense
from datetime import date
import time
import os
from extractor import extract_receipt_data

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
    # Automatikus mentés jóváhagyás nélkül
    try:
        new_expense = Expense(
            merchant=data.get('merchant', 'Ismeretlen'),
            total_amount=data.get('total_amount', 0),
            currency=data.get('currency', 'HUF'),
            category=data.get('category', 'Egyéb'),
            date=data.get('date'),
            items=data.get('items', [])
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return True
    except Exception as e:
        st.error(f"Adatbázis hiba: {e}")
        return False

def update_database(db: Session, edited_df: pd.DataFrame):
    # Frissítés szerkesztés után
    try:
        for index, row in edited_df.iterrows():
            expense_id = int(row["ID"])
            record = db.query(Expense).filter(Expense.id == expense_id).first()
            if record:
                record.merchant = row["Bolt"]
                record.total_amount = row["Összeg"]
                record.category = row["Kategória"]
                record.currency = row["Pénznem"]
                # Dátumot itt most egyszerűsítve kezeljük, feltételezzük, hogy string marad
                # record.date = ... 
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

# --- STÍLUS (Sötét módhoz optimalizálva) ---
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

# --- FŐ CÍMSOR ---
st.title("💰 SpendSmart Auto-Pilot")

# --- OLDALSÁV (Csak feltöltés) ---
st.sidebar.header("⚡ Gyors Feltöltés")
uploaded_file = st.sidebar.file_uploader("Blokk fotó (Automatikus mentés)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Csak akkor futtatjuk, ha ez egy új fájl (elkerüljük az újrafutást)
    if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != uploaded_file.name:
        st.session_state.last_uploaded_file = uploaded_file.name
        
        with st.sidebar.status("🤖 AI Feldolgozás...", expanded=True) as status:
            # 1. Mentés
            temp_filename = "temp_receipt.jpg"
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 2. Elemzés
            status.write("Kép elemzése...")
            extracted_data = extract_receipt_data(temp_filename)
            os.remove(temp_filename)
            
            # 3. Azonnali Mentés
            if extracted_data:
                status.write("Mentés adatbázisba...")
                db = next(get_db())
                if save_expense(db, extracted_data):
                    status.update(label="✅ Kész! Mentve.", state="complete", expanded=False)
                    time.sleep(1)
                    st.rerun() # Oldal frissítése, hogy látszódjon az új adat
            else:
                status.update(label="❌ Hiba történt", state="error")

# --- ADATOK BETÖLTÉSE ---
db = next(get_db())
expenses = get_all_expenses(db)

if expenses:
    # Pandas DataFrame
    data = [
        {
            "ID": e.id,
            "Dátum": e.date,
            "Bolt": e.merchant,
            "Összeg": float(e.total_amount),
            "Pénznem": e.currency,
            "Kategória": e.category
        } 
        for e in expenses
    ]
    df = pd.DataFrame(data)

    # --- KERESÉS ---
    col_search, _ = st.columns([1, 2])
    search_term = col_search.text_input("🔍 Keresés név alapján...", placeholder="Pl. Tesco")

    if search_term:
        df = df[df["Bolt"].str.contains(search_term, case=False, na=False)]

    # --- KÉT OSZLOPOS ELRENDEZÉS (Bal: Fő, Jobb: Utolsó 10) ---
    col_main, col_right = st.columns([3, 1]) 

    # --- JOBB OSZLOP: Legutóbbi 10 (Hibajavító sarok) ---
    with col_right:
        st.subheader("⏱️ Legutóbbi 10")
        st.caption("Gyors ellenőrzés: Ha hibásat látsz, itt javíthatod.")
        
        # Csak az első 10 sor (mivel dátum szerint csökkenőben van)
        latest_10 = df.head(10)
        
        edited_latest = st.data_editor(
            latest_10,
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None, # Elrejtjük az ID-t, hogy ne foglalja a helyet
                "Dátum": None, # Dátumot is elrejtjük a kompakt nézetben (opcionális)
                "Összeg": st.column_config.NumberColumn(format="%d"),
                "Pénznem": None,
                "Bolt": st.column_config.TextColumn("Bolt", width="small"),
                "Kategória": st.column_config.SelectboxColumn(
                    options=["Food", "Travel", "Entertainment", "Utilities", "Other"],
                    width="small"
                )
            },
            key="latest_editor"
        )
        
        if st.button("Mentés (Jobb sáv)", key="save_right"):
            if update_database(db, edited_latest):
                st.toast("✅ Javítások mentve!")
                time.sleep(1)
                st.rerun()

    # --- BAL OSZLOP: Fő Statisztikák és Teljes Lista ---
    with col_main:
        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Összes Költés", f"{df['Összeg'].sum():,.0f} Ft")
        c2.metric("Tranzakciók", f"{len(df)} db")
        c3.metric("Átlag", f"{df['Összeg'].mean():,.0f} Ft")

        st.markdown("---")

        # Grafikonok
        gc1, gc2 = st.columns(2)
        with gc1:
            fig_pie = px.pie(df, values='Összeg', names='Kategória', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with gc2:
            daily = df.groupby("Dátum")["Összeg"].sum().reset_index()
            fig_bar = px.bar(daily, x="Dátum", y="Összeg")
            fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_bar, use_container_width=True)

        # Teljes szerkeszthető lista
        st.subheader("📜 Teljes Előzmények")
        edited_full = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": st.column_config.NumberColumn(disabled=True),
                "Összeg": st.column_config.NumberColumn(format="%d Ft"),
            },
            key="full_editor"
        )
        
        if st.button("Változások Mentése (Teljes lista)", key="save_main"):
            if update_database(db, edited_full):
                st.toast("✅ Mentve!")
                time.sleep(1)
                st.rerun()

else:
    st.info("Nincs megjeleníthető adat. Tölts fel egy blokkot bal oldalt!")