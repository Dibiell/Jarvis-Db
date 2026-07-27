"""
JARVIS SKILL: Sequence Executor
Interpretador de ordens sequenciais "passo a passo" com auxílio de visão computacional.
Permite seguir roteiros exatos do usuário e resolver bloqueios técnicos.
"""

import time
import pyautogui
import os
import sys
from screen_vision import ver_tela_jarvis
from camera_vision import ver_camera_jarvis

# Segurança
pyautogui.FAILSAFE = True

class ContextoAgente:
    """Armazena informações trocadas entre agentes (clipboard interno)."""
    def __init__(self):
        self.dados = {}

    def salvar(self, chave, valor):
        self.dados[chave.lower()] = valor

    def recuperar(self, chave):
        return self.dados.get(chave.lower(), "")

contexto_global = ContextoAgente()

def executar_passo_a_passo(ordens, consultar_ia_func, cliente_groq=None, deepseek_client=None):
    """
    Executa uma lista de ordens sequenciais.
    
    Args:
        ordens: Lista de strings com as ordens ou uma string única descrevendo o plano.
        consultar_ia_func: Função para processar raciocínio.
    """
    if isinstance(ordens, str):
        # Se for uma string única, pede pra IA quebrar em passos técnicos
        prompt_quebra = (
            f"Transforme esta sequência de ordens em uma lista JSON de passos técnicos: '{ordens}'.\n"
            "Cada passo deve ter 'tipo' (abrir, clicar, digitar, esperar, usar_contexto, pesquisar_solucao) e 'valor'.\n"
            "Responda APENAS o JSON."
        )
        passos_raw = consultar_ia_func(prompt_quebra, salvar_no_historico=False)
        try:
            import json
            # Limpeza de markdown se houver
            if "```json" in passos_raw:
                passos_raw = passos_raw.split("```json")[1].split("```")[0].strip()
            elif "```" in passos_raw:
                passos_raw = passos_raw.split("```")[1].split("```")[0].strip()
            passos = json.loads(passos_raw)
        except Exception as e:
            return f"Erro ao interpretar passos: {e}"
    else:
        passos = ordens

    log_execucao = []
    
    for i, passo in enumerate(passos):
        if not isinstance(passo, dict):
            print(f"[Executor] Pulo de passo inválido (não é objeto): {passo}")
            log_execucao.append(f"Passo {i+1} ignorado: formato inválido.")
            continue
            
        tipo = passo.get("tipo", "").lower()
        valor = passo.get("valor", "")
        
        print(f"[Executor] Passo {i+1}: {tipo} -> {valor}")
        
        try:
            if tipo == "abrir":
                import webbrowser
                webbrowser.open(valor)
                log_execucao.append(f"Abri: {valor}")
                time.sleep(3) # Tempo de carga inicial
                
            elif tipo == "clicar":
                # Tenta localizar o elemento visualmente
                print(f"[Executor] Tentando localizar '{valor}' na tela...")
                analise = ver_tela_jarvis(f"Quais são as coordenadas (x, y) aproximadas do elemento ou texto '{valor}'? Responda no formato (x, y) apenas.", cliente_groq, deepseek_client)
                
                # Extrai coordenadas simples (x, y) da string
                import re
                coord_match = re.search(r'\((\d+),\s*(\d+)\)', analise)
                if coord_match:
                    x, y = int(coord_match.group(1)), int(coord_match.group(2))
                    pyautogui.click(x, y)
                    log_execucao.append(f"Cliquei em '{valor}' em ({x}, {y})")
                else:
                    # Fallback: se não achar coordenada, tenta mover o mouse e clicar cegamente ou usar atalhos (tab)
                    log_execucao.append(f"Erro: Não localizei '{valor}' visualmente. Sugiro conferir a tela.")
                    # Aqui entra a lógica de "Pesquisar Solução" se falhar
                    passo_extra = {"tipo": "pesquizar_solucao", "valor": f"como clicar em {valor} usando pyautogui"}
                    # (Poderia inserir na fila aqui)
            
            elif tipo == "digitar":
                # Verifica se o valor refere-se a contexto de outro agente
                if "contexto:" in valor.lower():
                    chave = valor.split("contexto:")[1].strip()
                    valor_real = contexto_global.recuperar(chave)
                    if not valor_real:
                        log_execucao.append(f"Aviso: Contexto '{chave}' está vazio.")
                    pyautogui.write(valor_real, interval=0.05)
                else:
                    pyautogui.write(valor, interval=0.05)
                log_execucao.append(f"Digitei: {valor}")
                
            elif tipo == "atalho":
                # Executa atalhos como 'ctrl', 't' ou 'enter'
                teclas = [t.strip() for t in valor.split("+")]
                pyautogui.hotkey(*teclas)
                log_execucao.append(f"Atalho executado: {valor}")

            elif tipo == "esperar":
                t = int(valor) if str(valor).isdigit() else 2
                time.sleep(t)
                log_execucao.append(f"Esperei {t}s")

            elif tipo == "pesquisar_solucao":
                # Autonomia de pesquisa
                from browser_agent import pesquisar_na_web
                res = pesquisar_na_web(valor)
                log_execucao.append(f"Pesquisa de solução para '{valor}': {res[:100]}...")
        
        except Exception as e:
            log_execucao.append(f"Erro no passo {i+1}: {e}")
            break
            
    return "\n".join(log_execucao)
