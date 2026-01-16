from extractor import extract_receipt_data
import json

# Change this to your image filename!
image_file = "image.jpg" 

print(f"Processing {image_file} with OpenRouter AI...")
result = extract_receipt_data(image_file)

if result:
    print("\n✅ Success! Extracted Data:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
else:
    print("\n❌ Failed to extract data.")