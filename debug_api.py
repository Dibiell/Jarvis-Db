import sys
import os

# Ensure we are in the right directory
os.chdir(r"c:\Users\souzx\.gemini\antigravity\scratch\jarvis-assistant")

try:
    from openai import OpenAI
    import pyttsx3
    print("[OK] Libraries imported successfully.")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    sys.exit(1)

# API Keys from jarvis.py
OPENAI_API_KEY = "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"

def test_openai():
    print("\n--- Testing OpenAI ---")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Olá, você está funcionando?"}],
            max_tokens=10
        )
        print(f"[OK] OpenAI Response: {response.choices[0].message.content}")
    except Exception as e:
        print(f"[ERROR] OpenAI failed: {e}")

if __name__ == "__main__":
    test_openai()
