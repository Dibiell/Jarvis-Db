"""
JARVIS SKILL: Action Recorder (Fase 2)
Grava ações do usuário (mouse + teclado) e salva como rotinas reutilizáveis.
"""

import json
import os
import datetime
import threading
import time

# Pasta onde as rotinas são salvas
ROTINAS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rotinas")

# ============================================================
# RECORDER
# ============================================================

class ActionRecorder:
    """
    Monitora e grava ações de mouse e teclado usando pynput.
    As gravações são salvas em JSON na pasta 'rotinas/'.
    """

    def __init__(self):
        self.gravando = False
        self.acoes = []
        self.tempo_inicio = None
        self._mouse_listener = None
        self._keyboard_listener = None
        self._ultimo_move = 0  # throttle para mousemove
        
        # Garante que a pasta de rotinas existe
        os.makedirs(ROTINAS_DIR, exist_ok=True)

    def _registrar(self, tipo, dados):
        """Registra uma ação com timestamp relativo ao início da gravação."""
        if not self.gravando:
            return
        agora = time.time()
        timestamp_relativo = round(agora - self.tempo_inicio, 3)
        self.acoes.append({
            "t": timestamp_relativo,
            "tipo": tipo,
            **dados
        })

    # --- Mouse ---
    def _on_move(self, x, y):
        agora = time.time()
        # Throttle: registra movimento apenas a cada 100ms para não encher o JSON
        if agora - self._ultimo_move > 0.1:
            self._registrar("mouse_move", {"x": x, "y": y})
            self._ultimo_move = agora

    def _on_click(self, x, y, button, pressed):
        self._registrar("mouse_click", {
            "x": x, "y": y,
            "botao": str(button),
            "pressionado": pressed
        })

    def _on_scroll(self, x, y, dx, dy):
        self._registrar("mouse_scroll", {"x": x, "y": y, "dx": dx, "dy": dy})

    # --- Teclado ---
    def _on_key_press(self, key):
        try:
            self._registrar("key_press", {"tecla": key.char})
        except AttributeError:
            self._registrar("key_press", {"tecla": str(key)})

    def _on_key_release(self, key):
        try:
            self._registrar("key_release", {"tecla": key.char})
        except AttributeError:
            self._registrar("key_release", {"tecla": str(key)})

    # --- Controle ---
    def iniciar(self):
        """Inicia a gravação de ações."""
        if self.gravando:
            return "Já estou gravando suas ações, senhor."
        
        try:
            from pynput import mouse, keyboard
        except ImportError:
            return "Módulo pynput não instalado. Execute: pip install pynput"
        
        self.acoes = []
        self.gravando = True
        self.tempo_inicio = time.time()
        self._ultimo_move = 0

        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll
        )
        self._keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        
        self._mouse_listener.start()
        self._keyboard_listener.start()

        print("[Recorder] Gravação de ações iniciada.")
        return "Modo de observação ativado. Estou gravando todas as suas ações, senhor."

    def parar(self, nome=None):
        """Para a gravação e salva a rotina com o nome dado."""
        if not self.gravando:
            return "Não estava gravando nenhuma ação, senhor."
        
        self.gravando = False

        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()

        num_acoes = len(self.acoes)
        
        if num_acoes == 0:
            return "Nenhuma ação foi registrada durante a gravação."
        
        # Define o nome do arquivo
        if not nome:
            nome = f"rotina_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Sanitiza o nome para uso como nome de arquivo
        nome_safe = "".join(c if c.isalnum() or c in "_- " else "_" for c in nome).strip().replace(" ", "_")
        
        caminho = os.path.join(ROTINAS_DIR, f"{nome_safe}.json")
        
        rotina_data = {
            "nome": nome,
            "criado_em": datetime.datetime.now().isoformat(),
            "duracao_total": round(time.time() - self.tempo_inicio, 2),
            "num_acoes": num_acoes,
            "acoes": self.acoes
        }
        
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(rotina_data, f, ensure_ascii=False, indent=2)
        
        print(f"[Recorder] Rotina '{nome}' salva com {num_acoes} ações em: {caminho}")
        return f"Rotina '{nome}' memorizada com sucesso! {num_acoes} ações gravadas em {rotina_data['duracao_total']} segundos."

    @property
    def esta_gravando(self):
        return self.gravando


# ============================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================

def listar_rotinas():
    """Lista todas as rotinas gravadas disponíveis."""
    os.makedirs(ROTINAS_DIR, exist_ok=True)
    arquivos = [f for f in os.listdir(ROTINAS_DIR) if f.endswith(".json")]
    
    if not arquivos:
        return "Nenhuma rotina gravada ainda, senhor."
    
    rotinas_info = []
    for arquivo in arquivos:
        try:
            caminho = os.path.join(ROTINAS_DIR, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            rotinas_info.append(f"• {dados.get('nome', arquivo)} — {dados.get('num_acoes', '?')} ações, {dados.get('duracao_total', '?')}s")
        except:
            rotinas_info.append(f"• {arquivo}")
    
    return "Rotinas disponíveis:\n" + "\n".join(rotinas_info)


def carregar_rotina(nome):
    """Carrega uma rotina pelo nome (parcial ou completo)."""
    os.makedirs(ROTINAS_DIR, exist_ok=True)
    arquivos = [f for f in os.listdir(ROTINAS_DIR) if f.endswith(".json")]
    
    nome_lower = nome.lower().replace(" ", "_")
    
    for arquivo in arquivos:
        if nome_lower in arquivo.lower():
            caminho = os.path.join(ROTINAS_DIR, arquivo)
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
    
    return None


# Instância global do recorder (singleton)
recorder = ActionRecorder()
