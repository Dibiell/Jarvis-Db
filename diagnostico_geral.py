try:
    import os
    import sys
    import ctypes
    import traceback
    # Tenta importar dotenv de forma segura
    try:
        from dotenv import load_dotenv
    except ImportError:
        def load_dotenv(): pass
        print("[AVISO] python-dotenv não instalado.")

except Exception as e:
    print(f"Erro crítico na inicialização: {e}")
    input("Pressione ENTER para fechar...")
    sys.exit(1)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def check_env():
    print("\n[1/3] VERIFICANDO AMBIENTE (.env)...")
    load_dotenv()
    tokens = ["HUGGINGFACE_TOKEN", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY"]
    for t in tokens:
        val = os.getenv(t)
        if val:
            print(f"  [OK] {t} carregado ({val[:5]}...)")
        else:
            print(f"  [AVISO] {t} não encontrado!")

def check_dependencies():
    print("\n[2/3] VERIFICANDO DEPENDÊNCIAS CRÍTICAS...")
    try:
        import numpy
        print(f"  [OK] Numpy versão: {numpy.__version__}")
    except Exception as e:
        print(f"  [ERRO] Numpy não encontrado: {e}")

    try:
        import cv2
        print(f"  [OK] OpenCV versão: {cv2.__version__}")
    except Exception as e:
        print(f"  [ERRO] OpenCV não encontrado: {e}")

    try:
        import torch
        print(f"  [OK] PyTorch versão: {torch.__version__}")
        print(f"  [OK] CUDA disponível: {torch.cuda.is_available()}")
    except Exception as e:
        print(f"  [ERRO] PyTorch não encontrado: {e}")

def check_voice():
    print("\n[3/3] VERIFICANDO SISTEMA DE VOZ...")
    try:
        import edge_tts
        print("  [OK] edge-tts (Voz Neural) disponível.")
    except Exception as e:
        print(f"  [ERRO] edge-tts não encontrado: {e}")

    caminho_ref = "jarvis_referencia.wav"
    if not os.path.exists(caminho_ref):
        if os.path.exists("jarvis_referencia.wav.wav"):
            caminho_ref = "jarvis_referencia.wav.wav"
    
    if os.path.exists(caminho_ref):
        print(f"  [OK] Arquivo de referência de voz encontrado: {caminho_ref}")
    else:
        print("  [AVISO] Arquivo de referência (jarvis_referencia.wav) NÃO encontrado! Clonagem falhará.")

if __name__ == "__main__":
    print("="*50)
    print("      DIAGNÓSTICO GERAL J.A.R.V.I.S")
    print("="*50)
    print(f"Status Admin: {'SIM' if is_admin() else 'NÃO'}")
    
    check_env()
    check_dependencies()
    check_voice()
    
    print("\n" + "="*50)
    print("Diagnóstico concluído. Se houver erros [ERRO], execute os instaladores.")
    print("="*50)
    input("\nPressione ENTER para sair...")
