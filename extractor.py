import os
import base64
import json
import io
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

def optimize_image(image_path):
    """
    1. Megnyitja a képet (bármi is a formátuma: png, webp, jpg).
    2. Átméretezi max 768 pixelre (ez bőven elég blokk olvasáshoz).
    3. Átkonvertálja tömörített JPG-be.
    """
    with Image.open(image_path) as img:
        # Ha PNG/átlátszó, konvertáljuk fehér hátterű RGB-be
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Átméretezés: a hosszabbik oldal legyen max 768px
        img.thumbnail((768, 768))
        
        # Mentés memóriába JPG-ként
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=70) # 70-es minőség elég szöveghez
        
        # Ellenőrzés: írjuk ki a méretet byte-ban (debug)
        size_kb = buffered.getbuffer().nbytes / 1024
        print(f"--- Kép optimalizálva: {size_kb:.2f} KB ---")
        
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

def extract_receipt_data(image_path):
    # 1. Kép előkészítése (itt történik a varázslat)
    try:
        base64_image = optimize_image(image_path)
    except Exception as e:
        print(f"Kép hiba: {e}")
        return None

    system_prompt = """
    Extract receipt fields into JSON: merchant, date, total_amount, currency, items.
    """

    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract data."},
                        {
                            "type": "image_url",
                            "image_url": {
                                # FONTOS: Most már biztosan JPEG-et küldünk
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high" 
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        return json.loads(content)

    except Exception as e:
        print(f"API Hiba: {e}")
        return None

if __name__ == "__main__":
    # Cseréld ki a fájlnevet a sajátodra!
    # Fontos: Használd a képernyőképen lévő fájlt tesztnek
    print("Feldolgozás indítása...")
    # data = extract_receipt_data("image_2e69f3.png") 
    # print(json.dumps(data, indent=2))