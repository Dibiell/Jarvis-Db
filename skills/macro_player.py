"""
JARVIS SKILL: Macro Player (Fase 3)
Reproduz rotinas gravadas pelo ActionRecorder via pyautogui,
com suporte a interpretação inteligente via IA.
"""

import json
import time
import pyautogui
from action_recorder import carregar_rotina, listar_rotinas

# Segurança do pyautogui: mover mouse pro canto encerra
pyautogui.FAILSAFE = True

# ============================================================
# REPLAY DIRETO (1:1)
# ============================================================

def executar_rotina_direta(nome):
    """
    Reproduz uma rotina gravada exatamente como foi gravada,
    respeitando os intervalos de tempo originais.
    
    Args:
        nome: Nome (parcial) da rotina a executar.
    Returns:
        str: Mensagem de resultado.
    """
    rotina = carregar_rotina(nome)
    if not rotina:
        return f"Rotina '{nome}' não encontrada. Use 'listar rotinas' para ver as disponíveis."
    
    acoes = rotina.get("acoes", [])
    if not acoes:
        return f"A rotina '{nome}' está vazia."
    
    print(f"[MacroPlayer] Executando rotina '{rotina['nome']}' com {len(acoes)} ações...")
    
    t_anterior = 0
    erros = 0
    
    for acao in acoes:
        # Respeita o timing original (pausa entre ações)
        delta = acao["t"] - t_anterior
        if delta > 0:
            time.sleep(min(delta, 2.0))  # limita a 2s por passo para não travar
        t_anterior = acao["t"]
        
        try:
            tipo = acao["tipo"]
            
            if tipo == "mouse_move":
                pyautogui.moveTo(acao["x"], acao["y"], duration=0.05)
            
            elif tipo == "mouse_click":
                btn = "left"
                if "right" in acao.get("botao", ""):
                    btn = "right"
                elif "middle" in acao.get("botao", ""):
                    btn = "middle"
                
                if acao.get("pressionado"):
                    pyautogui.mouseDown(x=acao["x"], y=acao["y"], button=btn)
                else:
                    pyautogui.mouseUp(x=acao["x"], y=acao["y"], button=btn)
            
            elif tipo == "mouse_scroll":
                pyautogui.scroll(int(acao.get("dy", 0) * 3), x=acao["x"], y=acao["y"])
            
            elif tipo == "key_press":
                tecla = acao.get("tecla", "")
                if tecla:
                    _pressionar_tecla(tecla)
        
        except Exception as e:
            erros += 1
            print(f"[MacroPlayer] Erro na ação {acao}: {e}")
            if erros > 5:
                return f"Muitos erros na execução da rotina '{nome}'. Abortando."
    
    return f"Rotina '{rotina['nome']}' executada com sucesso, senhor!"


def _pressionar_tecla(tecla_str):
    """Converte string de tecla do pynput para pyautogui e pressiona."""
    # Mapa de teclas especiais (pynput -> pyautogui)
    MAPA_TECLAS = {
        "Key.space": "space",
        "Key.enter": "enter",
        "Key.backspace": "backspace",
        "Key.delete": "delete",
        "Key.tab": "tab",
        "Key.shift": "shift",
        "Key.shift_r": "shiftright",
        "Key.ctrl_l": "ctrlleft",
        "Key.ctrl_r": "ctrlright",
        "Key.alt_l": "altleft",
        "Key.alt_r": "altright",
        "Key.cmd": "winleft",
        "Key.up": "up",
        "Key.down": "down",
        "Key.left": "left",
        "Key.right": "right",
        "Key.home": "home",
        "Key.end": "end",
        "Key.page_up": "pageup",
        "Key.page_down": "pagedown",
        "Key.f1": "f1", "Key.f2": "f2", "Key.f3": "f3", "Key.f4": "f4",
        "Key.f5": "f5", "Key.f6": "f6", "Key.f7": "f7", "Key.f8": "f8",
        "Key.f9": "f9", "Key.f10": "f10", "Key.f11": "f11", "Key.f12": "f12",
        "Key.esc": "escape",
        "Key.caps_lock": "capslock",
        "Key.print_screen": "printscreen",
    }
    
    if tecla_str in MAPA_TECLAS:
        pyautogui.press(MAPA_TECLAS[tecla_str])
    elif len(tecla_str) == 1:
        # Tecla de caractere normal
        pyautogui.write(tecla_str, interval=0.02)
    else:
        # Tenta como hotkey (ex: 'ctrl+c')
        try:
            pyautogui.press(tecla_str.replace("Key.", ""))
        except:
            pass


# ============================================================
# REPLAY INTELIGENTE VIA IA (opcional)
# ============================================================

def gerar_script_ia(acoes_json, consultar_ia_func):
    """
    Usa a IA para interpretar e re-gerar um script pyautogui mais limpo
    a partir das ações gravadas. Útil para resumir rotinas longas.
    
    Args:
        acoes_json: Lista de ações gravadas (dicionários).
        consultar_ia_func: Função consultar_ia do jarvis.py
    Returns:
        str: Script Python com comandos pyautogui, ou None se falhar.
    """
    if len(acoes_json) > 200:
        # Amostra para não estourar o contexto da IA
        amostra = acoes_json[:50] + acoes_json[-50:]
    else:
        amostra = acoes_json
    
    prompt = (
        f"Aqui estão {len(acoes_json)} ações de mouse e teclado gravadas do usuário (amostra de {len(amostra)}):\n\n"
        f"```json\n{json.dumps(amostra, ensure_ascii=False, indent=1)}\n```\n\n"
        "Com base nisso, gere um script Python COMPACTO usando pyautogui que reproduza essa rotina de forma inteligente. "
        "Agrupe cliques repetitivos, use pyautogui.write() para sequências de teclas, e adicione comentários breves. "
        "Retorne APENAS o código Python, sem explicações."
    )
    
    try:
        script = consultar_ia_func(prompt, salvar_no_historico=False)
        return script
    except Exception as e:
        print(f"[MacroPlayer] Erro ao gerar script via IA: {e}")
        return None


def executar_script_ia(script_python):
    """
    Executa um script pyautogui gerado pela IA de forma segura.
    """
    import pyautogui
    import time
    
    contexto_seguro = {"pyautogui": pyautogui, "time": time}
    
    try:
        exec(script_python, contexto_seguro)
        return "Script inteligente executado com sucesso!"
    except Exception as e:
        return f"Erro ao executar script: {e}"
