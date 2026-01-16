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

# Csak az AI által elemzett utolsó 10 tétel
def get_ai_expenses(db: Session, limit=10):
    return db.query(Expense)\
             .filter(Expense.source == "AI")\
             .order_by(Expense.id.desc())\
             .limit(limit)\
             .all()

def save_expense(db: Session, data, source="Manual"):
    try:
        new_expense = Expense(
            merchant=data.get('merchant', 'Ismeretlen'),
            total_amount=data.get('total_amount', 0),
            currency=data.get('currency', 'HUF'),
            category=data.get('category', 'Egyéb'),
            date=data.get('date'),
            items=data.get('items', []),
            source=source
        )
        db.add(new_expense)
        db.commit()
        db.refresh(new_expense)
        return True
    except Exception as e:
        st.error(f"Adatbázis hiba: {e}")
        return False

def update_database(db: Session, edited_df: pd.DataFrame):
    try:
        for index, row in edited_df.iterrows():
            expense_id = int(row["ID"])
            record = db.query(Expense).filter(Expense.id == expense_id).first()
            if record:
                record.merchant = row["Bolt"]
                record.total_amount = row["Összeg"]
                record.category = row["Kategória"]
                record.currency = row["Pénznem"]
                record.date = row["Dátum"] # Most már a dátumot is frissítjük!
        db.commit()
        return True
    except Exception as e:
        st.error(f"Hiba a mentésnél: {e}")
        return False

# --- STÍLUS ---
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

# --- OLDALSÁV (Feltöltés) ---
st.sidebar.header("⚡ Gyors Feltöltés")
uploaded_file = st.sidebar.file_uploader("Blokk fotó feltöltése", type=["jpg", "jpeg", "png"], key="uploader")

if uploaded_file is not None:
    st.sidebar.image(uploaded_file, caption="Előnézet", use_container_width=True)
    
    if st.sidebar.button("🚀 Feldolgozás Indítása", type="primary"):
        with st.sidebar.status("🤖 AI Feldolgozás...", expanded=True) as status:
            try:
                # 1. Kép mentése
                temp_filename = "temp_receipt.jpg"
                with open(temp_filename, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # 2. AI Elemzés
                status.write("Kép küldése az AI-nak...")
                extracted_data = extract_receipt_data(temp_filename)
                
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
                
                # 3. Mentés source="AI" jelöléssel
                if extracted_data:
                    status.write("Mentés adatbázisba...")
                    db = next(get_db())
                    
                    if save_expense(db, extracted_data, source="AI"):
                        status.update(label="✅ SIKER! Mentve.", state="complete", expanded=False)
                        time.sleep(1)
                        st.rerun()
                    else:
                        status.update(label="❌ Adatbázis hiba", state="error")
                else:
                    status.update(label="❌ AI hiba: Nem jött adat", state="error")
            except Exception as e:
                status.update(label="❌ Hiba", state="error")
                st.sidebar.error(f"{e}")

# --- ADATOK BETÖLTÉSE ---
db = next(get_db())
all_expenses = get_all_expenses(db)
ai_expenses = get_ai_expenses(db)

# Fő lista DataFrame
df_all = pd.DataFrame()
if all_expenses:
    df_all = pd.DataFrame([{
        "ID": e.id, "Dátum": e.date, "Bolt": e.merchant, 
        "Összeg": float(e.total_amount), "Pénznem": e.currency, "Kategória": e.category
    } for e in all_expenses])

# AI lista DataFrame (Most már minden oszlop benne van!)
df_ai = pd.DataFrame()
if ai_expenses:
    df_ai = pd.DataFrame([{
        "ID": e.id, 
        "Dátum": e.date,          # <--- BEKERÜLT
        "Bolt": e.merchant, 
        "Összeg": float(e.total_amount), 
        "Pénznem": e.currency,    # <--- BEKERÜLT
        "Kategória": e.category,
    } for e in ai_expenses])

# --- LAYOUT: KÉT OSZLOP ---
col_main, col_right = st.columns([2.5, 1.5]) # Kicsit szélesítettem a jobb oldalon (1.2 -> 1.5)

# >>> JOBB OSZLOP: AI NAPLÓ (Részletes) <<<
with col_right:
    st.subheader("🤖 AI Napló (Utolsó 10)")
    st.caption("Itt látod, mit olvasott be a gép. Javítsd, ha tévedett!")
    
    if not df_ai.empty:
        edited_ai = st.data_editor(
            df_ai,
            hide_index=True,
            use_container_width=True,
            column_config={
                "ID": None, # Ezt továbbra is elrejtjük, mert technikai adat
                "Dátum": st.column_config.DateColumn("Dátum", width="small"), # Látható!
                "Pénznem": st.column_config.TextColumn("Deviza", width="small"), # Látható!
                "Bolt": st.column_config.TextColumn("Bolt", width="medium"),
                "Összeg": st.column_config.NumberColumn("Összeg", format="%d"),
                "Kategória": st.column_config.SelectboxColumn(
                    "Kat.",
                    options=["Food", "Travel", "Entertainment", "Utilities", "Other"],
                    width="medium"
                )
            },
            key="ai_editor"
        )
        
        if st.button("Javítások Mentése (AI Sáv)", type="primary"):
            if update_database(db, edited_ai):
                st.toast("✅ Javítva!")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Még nincs AI által feltöltött adat.")

# >>> BAL OSZLOP: STATISZTIKA ÉS TELJES LISTA <<<
with col_main:
    if not df_all.empty:
        # KPI
        c1, c2, c3 = st.columns(3)
        c1.metric("Összes Költés", f"{df_all['Összeg'].sum():,.0f} Ft")
        c2.metric("Tranzakciók", f"{len(df_all)} db")
        c3.metric("Átlag", f"{df_all['Összeg'].mean():,.0f} Ft")
        
        st.markdown("---")

        # Grafikonok
        gc1, gc2 = st.columns(2)
        with gc1:
            fig_pie = px.pie(df_all, values='Összeg', names='Kategória', hole=0.4, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)
        with gc2:
            daily = df_all.groupby("Dátum")["Összeg"].sum().reset_index()
            fig_bar = px.bar(daily, x="Dátum", y="Összeg")
            fig_bar.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=250)
            st.plotly_chart(fig_bar, use_container_width=True)

        st.markdown("---")
        
        # Kereső és Teljes Lista
        st.subheader("🗂️ Teljes Archívum")
        search_term = st.text_input("Keresés:", placeholder="Bolt neve...")
        
        if search_term:
            df_filtered = df_all[df_all["Bolt"].str.contains(search_term, case=False, na=False)]
        else:
            df_filtered = df_all

        st.dataframe(
            df_filtered, 
            hide_index=True, 
            use_container_width=True,
            column_config={"ID": None}
        )

    else:
        st.info("Nincs adat. Tölts fel valamit!")