import os
import requests
from huggingface_hub import InferenceClient
import base64

# Try to find token from actual jarvis.py if it was there
HF_TOKEN = "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"
MODEL = "microsoft/Florence-2-large"

print(f"Testing model: {MODEL}")
client = InferenceClient(token=HF_TOKEN)

def test_hf():
    try:
        # Dummy transparent pixel
        dummy_png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==")
        
        print("Sending image_to_text request to HF...")
        # Note: InferenceClient.image_to_text expect bytes or path
        response = client.image_to_text(dummy_png, model=MODEL)
        print(f"Response (image_to_text): {response}")
    except Exception as e:
        print(f"HuggingFace image_to_text Error: {e}")
        
    try:
        # Some models require specific headers or tasks. Let's try a direct POST just to see the HTTP error code.
        print("\nSending direct POST to HF API...")
        api_url = f"https://api-inference.huggingface.co/models/{MODEL}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        
        response = requests.post(api_url, headers=headers, data=dummy_png)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
    except Exception as e:
        print(f"Direct POST Error: {e}")

if __name__ == "__main__":
    test_hf()
