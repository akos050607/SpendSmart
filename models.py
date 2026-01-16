from sqlalchemy import create_engine, Column, Integer, String, Float, Date, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Table definition ---
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.now)  # When uploaded
    merchant = Column(String)       # Merchant name (e.g. Tesco)
    date = Column(Date)             # Purchase date
    total_amount = Column(Float)    # Total amount
    currency = Column(String)       # Currency (HUF)
    category = Column(String)       # Category (Food)
    items = Column(JSON, nullable=True)
    source = Column(String, default="Manual")  # Source of the data (Manual, OCR, etc.)