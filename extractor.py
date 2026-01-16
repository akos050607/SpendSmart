import os
import base64
import json
import io
import re
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import streamlit as st  # Important for error output!

load_dotenv()

# Check the key
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("ERROR: API key not provided!")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

def optimize_image(image_path):
    """
    Image optimization:
    - Handle PNG transparency (white background)
    - Resize (max 1024px so the receipt remains readable)
    - Compression
    """
    try:
        with Image.open(image_path) as img:
            # 1. If PNG/WEBP and has transparency, convert to white background RGB
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[3]) # 3rd channel is alpha
                img = background
            else:
                img = img.convert("RGB")
                
            # 2. Resize: max 1024px (kept a bit larger so numbers are readable)
            img.thumbnail((1024, 1024))
            
            # 3. Save to memory
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85) # 85 quality better for OCR
            
            # Debug info
            size_kb = buffered.getbuffer().nbytes / 1024
            print(f"📷 Image optimized: {size_kb:.2f} KB")
            
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        st.error(f"Error during image preparation: {e}")
        return None

def extract_receipt_data(image_path):
    # 1. Load image
    base64_image = optimize_image(image_path)
    if not base64_image:
        return None

    # 2. Prompt (With very strict instructions)
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
        # Debug message to UI
        # st.toast("Sending image to AI...") 

        response = client.chat.completions.create(
            # Recommended free model on OpenRouter for images:
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
            # REMOVED the response_format because Gemini sometimes doesn't like it on OpenRouter
            # response_format={"type": "json_object"} 
        )

        raw_content = response.choices[0].message.content
        print(f"🤖 AI Raw response: {raw_content}") # You can see what it responded in terminal

        # 3. Cleaning (If the AI still puts markdown frame)
        clean_content = raw_content.replace("```json", "").replace("```", "").strip()
        
        # If there is any text left before/after the JSON, extract the { ... } part with regex
        json_match = re.search(r'\{.*\}', clean_content, re.DOTALL)
        if json_match:
            clean_content = json_match.group(0)

        return json.loads(clean_content)

    except json.JSONDecodeError:
        st.error("Error: The AI did not return valid JSON.")
        st.code(raw_content) # Shows what it sent
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        print(f"API Error: {e}")
        return None

if __name__ == "__main__":
    # For testing
    pass