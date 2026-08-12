"""
JARVIS BRAIN - Ferramentas de Desktop
Controla apps nativos (Notepad, etc.) via árvore de acessibilidade do
Windows (pywinauto, backend UIA), não via coordenada de pixel chutada.
Isso é o equivalente Python do que o sidecar do UseJarvis faz com UIA/COM.

pyautogui só entra como último recurso (ex: tirar screenshot, atalho
de teclado simples) - não pra clicar/digitar em elementos.
"""

import os
import subprocess
import time

# Guarda a referência da última janela que o PRÓPRIO Jarvis abriu, pra
# conseguir mirar nela especificamente depois - não na "janela ativa",
# que pode ser qualquer coisa que você esteja usando ao mesmo tempo
# (isso já causou o Jarvis colar texto no SEU bloco de notas por engano).
_ultima_janela_jarvis = None

# Aliases dos apps mais comuns - manda pro Windows Search se não achar
ALIASES_APPS = {
    "bloco de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "explorador de arquivos": "explorer.exe",
    "paint": "mspaint.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
}


def abrir_aplicativo(nome_app: str) -> dict:
    """
    Abre um aplicativo pelo nome. Retorna o resultado da ação -
    quem chama (o loop do agente) decide o que fazer com isso.
    """
    nome_normalizado = nome_app.strip().lower()
    executavel = ALIASES_APPS.get(nome_normalizado)

    try:
        if executavel:
            subprocess.Popen(executavel, shell=True)
        else:
            # Não conhece o alias - tenta abrir direto pelo nome via Windows Run
            subprocess.Popen(f'start "" "{nome_app}"', shell=True)

        time.sleep(1.2)  # dá tempo da janela abrir antes do próximo passo

        # Guarda qual janela é essa, assumindo que ela puxou o foco ao
        # abrir (comportamento padrão do Windows pra apps novos)
        global _ultima_janela_jarvis
        try:
            from pywinauto import Desktop
            _ultima_janela_jarvis = Desktop(backend="uia").window(active_only=True)
        except Exception:
            _ultima_janela_jarvis = None

        return {"sucesso": True, "mensagem": f"'{nome_app}' foi solicitado a abrir."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao abrir '{nome_app}': {e}"}


def digitar_no_app_ativo(texto: str) -> dict:
    """
    Digita texto colando via área de transferência (Ctrl+V). Sempre que
    possível, mira especificamente na janela que o PRÓPRIO Jarvis abriu
    por último (guardada em _ultima_janela_jarvis) - não na "janela
    ativa" genérica, pra não colar por engano em algo que você mesmo
    esteja usando ao mesmo tempo.
    """
    try:
        import pyperclip
        from pywinauto import Desktop

        global _ultima_janela_jarvis
        janela = None

        if _ultima_janela_jarvis is not None:
            try:
                _ultima_janela_jarvis.set_focus()
                janela = _ultima_janela_jarvis
            except Exception:
                janela = None  # a janela guardada não existe mais (foi fechada, etc.)

        if janela is None:
            print("[Desktop] AVISO: não sei qual janela o Jarvis abriu por último - "
                  "usando a janela ativa agora (risco de digitar em algo seu por engano).")
            janela = Desktop(backend="uia").window(active_only=True)

        conteudo_anterior = None
        try:
            conteudo_anterior = pyperclip.paste()
        except Exception:
            pass

        pyperclip.copy(texto)
        janela.type_keys("^v", pause=0.05)  # Ctrl+V

        if conteudo_anterior is not None:
            pyperclip.copy(conteudo_anterior)

        return {"sucesso": True, "mensagem": f"Texto colado na janela '{janela.window_text()}'."}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao digitar: {e}"}


def listar_janelas() -> dict:
    """Lista as janelas abertas no momento - usado pelo agente pra 'observar' o estado do PC."""
    try:
        from pywinauto import Desktop

        janelas = Desktop(backend="uia").windows()
        titulos = [w.window_text() for w in janelas if w.window_text().strip()]
        return {"sucesso": True, "janelas": titulos}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao listar janelas: {e}"}


def tirar_screenshot(caminho: str) -> dict:
    """Tira um print da tela inteira - usado como evidência/verificação depois de cada ação."""
    try:
        import mss

        with mss.mss() as sct:
            sct.shot(output=caminho)
        return {"sucesso": True, "caminho": caminho}
    except Exception as e:
        return {"sucesso": False, "mensagem": f"Falha ao capturar tela: {e}"}
