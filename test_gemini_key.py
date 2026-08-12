"""
Script isolado para testar se uma chave do Gemini (AI Studio) funciona de verdade.
Rode este arquivo sozinho ANTES de mexer no jarvis.py.

Instalação necessária (uma vez só):
    pip install google-genai python-dotenv

Uso:
    python test_gemini_key.py
"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Pega a primeira key do pool para testar
keys_raw = os.getenv("GEMINI_API_KEYS", "")
keys = [k.strip() for k in keys_raw.split(",") if k.strip()]

if not keys:
    print("[ERRO] Nenhuma key encontrada em GEMINI_API_KEYS no .env")
    exit(1)

for i, key in enumerate(keys, start=1):
    print(f"\n--- Testando key #{i} ({key[:15]}...) ---")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents="Responda apenas: 'Chave funcionando'"
        )
        print(f"[OK] Resposta: {response.text}")
    except Exception as e:
        print(f"[FALHOU] {type(e).__name__}: {e}")
