# -*- coding: utf-8 -*-
"""
test_mic.py - Diagnostico completo do microfone e reconhecimento de voz
Execute: venv\Scripts\python.exe test_mic.py
"""
import sys
import speech_recognition as sr

# Forcar saida UTF-8 no terminal Windows
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("  DIAGNOSTICO DE MICROFONE - JARVIS")
print("=" * 60)

# 1. Listar todos os microfones disponiveis
print("\n[1] Microfones disponiveis no sistema:")
mics = sr.Microphone.list_microphone_names()
for i, nome in enumerate(mics):
    marker = "  <-- XC-AMIC (sera usado)" if "xc-amic" in nome.lower() else ""
    print(f"  [{i}] {nome}{marker}")

# 2. Encontrar o microfone XC-AMIC
mic_index = None
for i, nome in enumerate(mics):
    if "xc-amic" in nome.lower():
        mic_index = i
        break

if mic_index is None:
    print("\n[AVISO] XC-AMIC nao encontrado! Usando microfone padrao (None).")
else:
    print(f"\n[OK] XC-AMIC encontrado no indice {mic_index}: {mics[mic_index]}")

print("\n" + "=" * 60)
print("  TESTE DE RECONHECIMENTO DE VOZ")
print("=" * 60)

# 3. Calibrar ruido ambiente
r = sr.Recognizer()

print("\n[2] Calibrando ruido ambiente (2 segundos, fique em silencio)...")
try:
    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source, duration=2)
    print(f"    Energy threshold calibrado: {r.energy_threshold:.0f}")
    if r.energy_threshold > 4000:
        print("    [AVISO] Threshold MUITO ALTO - ambiente muito barulhento!")
    elif r.energy_threshold < 80:
        print("    [AVISO] Threshold muito baixo - microfone pode estar sem sinal.")
    else:
        print("    [OK] Threshold esta dentro do normal.")
except Exception as e:
    print(f"    [ERRO] Microfone inacessivel: {e}")
    sys.exit(1)

# 4. Teste de escuta
input("\n[3] Pressione ENTER e fale algo em voz alta (voce tem 6 segundos)...")
try:
    with sr.Microphone(device_index=mic_index) as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("    Ouvindo agora...")
        audio = r.listen(source, timeout=6, phrase_time_limit=10)
    print("    [OK] Audio capturado!")
except sr.WaitTimeoutError:
    print("    [ERRO] TIMEOUT - nenhum som detectado em 6 segundos.")
    print("    Verifique se o XC-AMIC esta selecionado como entrada padrao no Windows.")
    sys.exit(1)
except Exception as e:
    print(f"    [ERRO] Problema durante escuta: {e}")
    sys.exit(1)

# 5. Reconhecimento
print("\n[4] Enviando audio para o Google Speech Recognition...")
try:
    texto = r.recognize_google(audio, language='pt-BR')
    print(f"    [OK] Reconhecido: \"{texto}\"")
except sr.UnknownValueError:
    print("    [ERRO] Audio capturado, mas o Google nao reconheceu nenhuma fala.")
    print("    Dicas: fale mais alto, mais proxmo ao microfone, ou ambiente muito barulhento.")
except sr.RequestError as e:
    print(f"    [ERRO] Falha na API do Google: {e}")
    print("    Verifique sua conexao com a internet.")

print("\n" + "=" * 60)
print("  FIM DO DIAGNOSTICO")
print("=" * 60)
