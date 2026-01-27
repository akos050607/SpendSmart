# 💰 SpendSmart - AI-Powered Expense Tracker

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql)
![OpenAI](https://img.shields.io/badge/AI-GPT--4o-green?style=for-the-badge&logo=openai)

**SpendSmart** is a modern, automated expense tracking pipeline that eliminates manual data entry. It uses **Computer Vision (LLMs)** to extract data from receipt images. The data is visualized in a real-time **Streamlit Dashboard**.

## 📸 DEMO

---
[Screencast from 2026-01-27 15-59-13.webm](https://github.com/user-attachments/assets/952399ea-8ae9-4bc2-a732-d695fe853761)
[Screencast from 2026-01-27 16-00-05.webm](https://github.com/user-attachments/assets/dccfa33c-8337-41e8-832b-32ff9d619788)


## 🚀 Features

* **🧾 AI Receipt Scanning:** Upload a photo of any receipt; the system extracts the Merchant, Date, Total Amount, Currency, and Category automatically using GPT-4o / Gemini models.
* **📊 Interactive Dashboard:** Analyze spending habits with Plotly charts (Donut charts, Trend lines) and KPI cards.
* **✍️ Smart Editing:** A dedicated "AI Review" sidebar allows you to correct AI mistakes before finalizing the data.
* **🗄️ Backend:** Data is stored in a structured PostgreSQL database using SQLAlchemy ORM.

---

## 🛠️ Tech Stack

* **Frontend:** Streamlit, Plotly Express
* **Backend:** Python 3.12
* **Database:** PostgreSQL (with `psycopg2` & `SQLAlchemy`)
* **AI/LLM:** OpenRouter API (Accessing GPT-4o-mini / Gemini 2.0 Flash)
* **Image Processing:** Pillow (PIL)

---


## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/yourusername/SpendSmart.git](https://github.com/yourusername/SpendSmart.git)
cd SpendSmart
