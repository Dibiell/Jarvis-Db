import os
from dotenv import load_dotenv

def test_env():
    load_dotenv()
    print("--- Teste de Ambiente JARVIS ---")
    tokens = [
        "HUGGINGFACE_TOKEN",
        "OPENROUTER_API_KEY",
        "DEEPSEEK_API_KEY"
    ]
    for token in tokens:
        val = os.getenv(token)
        if val:
            print(f"[OK] {token} carregado (inicia com {val[:5]}...)")
        else:
            print(f"[ERRO] {token} NÃO encontrado!")

if __name__ == "__main__":
    test_env()
