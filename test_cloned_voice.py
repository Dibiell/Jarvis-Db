import os
import tempfile
import traceback
import sys
import time

print("="*60)
print("   DIAGNÓSTICO ABSOLUTO: CLONAGEM DE VOZ (XTTS-v2)")
print("="*60)

# Setup Environment
os.environ["COQUI_TOS_AGREED"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

project_dir = r"C:\Users\souzx\Downloads\Nova pasta\jarvis-assistant"
os.chdir(project_dir)

caminho_ref = "jarvis_referencia.wav"
if not os.path.exists(caminho_ref) and os.path.exists("jarvis_referencia.wav.wav"):
    caminho_ref = "jarvis_referencia.wav.wav"

if not os.path.exists(caminho_ref):
    print(f"[ERRO FATAL] Arquivo de referencia nao encontrado: {caminho_ref}")
    sys.exit(1)
print(f"[OK] Arquivo de referencia encontrado: {caminho_ref} ({os.path.getsize(caminho_ref)} bytes)")

try:
    import torch
    print(f"[OK] PyTorch version: {torch.__version__}")
    print(f"[OK] CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"      Device: {torch.cuda.get_device_name(0)}")
        
    # Bypass de seguranca universal
    _original_load = torch.load
    def _unsafe_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    torch.load = _unsafe_load
    print("[OK] PyTorch weights_only bypass aplicado.")

    # Workaround para erro do torchcodec / DLL no PyTorch 2.6+
    import torchaudio
    import soundfile as sf
    def _custom_torchaudio_load(filepath, *args, **kwargs):
        data, sr = sf.read(filepath)
        tensor = torch.tensor(data)
        if tensor.ndim == 1:
            tensor = tensor.unsqueeze(0)
        else:
            tensor = tensor.T
        if tensor.dtype == torch.float64:
            tensor = tensor.float()
        return tensor, sr
    torchaudio.load = _custom_torchaudio_load
    print("[OK] Torchaudio load monkeypatch aplicado via soundfile!")
except Exception as e:
    print(f"[AVISO/ERRO] Problema inicializando PyTorch. {e}")

try:
    print("\n[TESTE 1] Importando TTS da Coqui...")
    t0 = time.time()
    from TTS.api import TTS
    print(f"[OK] TTS importado. Tempo: {time.time()-t0:.2f}s")
    
    print("\n[TESTE 2] Carregando modelo XTTS-v2...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    t0 = time.time()
    local_xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
    print(f"[OK] Modelo XTTS-v2 carregado com sucesso no dispositivo '{device}'. Tempo: {time.time()-t0:.2f}s")
    
    print("\n[TESTE 3] Gerando voz clonada...")
    t0 = time.time()
    texto_teste = "Olá, Jarvis. Este é um teste absoluto do sistema de clonagem de voz desenvolvido por você, senhor."
    print(f"      Texto: '{texto_teste}'")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        output_path = tmp_file.name
        
    local_xtts_model.tts_to_file(
        text=texto_teste,
        speaker_wav=caminho_ref,
        language="pt",
        file_path=output_path
    )
    print(f"[SUCESSO ABSOLUTO] Voz gerada e salva em: {output_path}. Tempo: {time.time()-t0:.2f}s")
    
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(output_path)
        pygame.mixer.music.play()
        print("[PLAY] Reproduzindo o audio gerado...")
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
    except Exception as em:
        print(f"[AVISO] Nao foi possivel reproduzir o audio (pygame): {em}")
    
    try:
        os.remove(output_path)
    except:
        pass

except Exception as e:
    print("\n" + "="*60)
    print("[ERRO CRITICO] A CLONAGEM DE VOZ FALHOU!")
    print("="*60)
    traceback.print_exc()
    sys.exit(1)

print("\n[DIAGNOSTICO FINALIZADO COM SUCESSO]")
