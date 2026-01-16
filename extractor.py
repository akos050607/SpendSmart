import os
import base64
import json
import io
import re
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import streamlit as st  # Fontos a hibakiíráshoz!

load_dotenv()

# Ellenőrizzük a kulcsot
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("HIBA: Nincs megadva API kulcs!")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

def optimize_image(image_path):
    """
    Kép optimalizálása:
    - PNG átlátszóság kezelése (fehér háttér)
    - Átméretezés (max 1024px, hogy olvasható maradjon a blokk)
    - Tömörítés
    """
    try:
        with Image.open(image_path) as img:
            # 1. Ha PNG/WEBP és van átlátszósága, konvertáljuk fehér hátterű RGB-be
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3]) # 3. csatorna az alpha
                img = background
            else:
                img = img.convert("RGB")
                
            # 2. Átméretezés: max 1024px (kicsit nagyobbat hagytam, hogy a számok olvashatóak legyenek)
            img.thumbnail((1024, 1024))
            
            # 3. Mentés memóriába
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85) # 85-ös minőség jobb OCR-hez
            
            # Debug infó
            size_kb = buffered.getbuffer().nbytes / 1024
            print(f"📷 Kép optimalizálva: {size_kb:.2f} KB")
            
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        st.error(f"Hiba a kép előkészítésekor: {e}")
        return None

def extract_receipt_data(image_path):
    # 1. Kép betöltése
    base64_image = optimize_image(image_path)
    if not base64_image:
        return None

    # 2. Prompt (Nagyon szigorú utasításokkal)
    system_prompt = """
    You are an expense tracking AI. Analyze the receipt image provided.
    Extract the following fields into a valid JSON object:
    - merchant (string): Name of the store.
    - date (string): Format YYYY-MM-DD.
    - total_amount (number): The final numeric total.
    - currency (string): E.g., HUF, USD.
    - category (string): Choose one: Food, Travel, Entertainment, Utilities, Other.
    - items (list): List of item names found.

    IMPORTANT: Return ONLY the raw JSON string. Do not use markdown blocks (```json).
    If values are missing, use null.
    """

    try:
        # Debug üzenet a UI-ra
        # st.toast("Kép küldése az AI-nak...") 

        response = client.chat.completions.create(
            # Javasolt ingyenes modell OpenRouteren képekhez:
            model="openai/gpt-4o-mini", 
            
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract data from this receipt."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            # KIVETTEM a response_format-ot, mert a Gemini néha nem szereti OpenRouteren
            # response_format={"type": "json_object"} 
        )

        raw_content = response.choices[0].message.content
        print(f"🤖 AI Nyers válasz: {raw_content}") # Terminálban látod mit válaszolt

        # 3. Tisztítás (Ha az AI mégis tenne markdown keretet)
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        # Ha esetleg maradt valami szöveg a JSON előtt/után, regex-szel kiszedjük a { ... } részt
        json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
        if json_match:
            clean_content = json_match.group(0)

        return json.loads(clean_content)

    except json.JSONDecodeError:
        st.error("Hiba: Az AI nem érvényes JSON-t küldött vissza.")
        st.code(raw_content) # Megmutatja mit küldött
        return None
    except Exception as e:
        st.error(f"API Hiba: {e}")
        print(f"API Hiba: {e}")
        return None

if __name__ == "__main__":
    # Teszteléshez
    pass