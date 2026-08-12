from mcp.server.fastmcp import FastMCP
import os
import sys

# Adiciona o diretório atual ao path para importar skills
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from skills.screen_vision import ver_tela_jarvis

# Inicializa o FastMCP
mcp = FastMCP("JARVIS-FDM1")

@mcp.tool()
async def analyze_screen(prompt: str = "Descreva detalhadamente o que está na tela", monitor_index: int = 0):
    """
    Usa o pipeline FDM-1 para analisar um monitor específico.
    monitor_index: 1 para o principal, 2 para o secundário, etc. (0 captura todos).
    """
    # Prompt técnico inspirado pelo ScreenAI para melhor compreensão de UI
    prompt_tecnico = (
        "Analise a tela com foco em Interface de Usuário (UI).\n"
        "Identifique: Janelas ativas, botões, campos de entrada, ícones e textos importantes.\n"
        f"Contexto do usuário: {prompt}"
    )
    
    print(f"[MCP] Analisando monitor {monitor_index}...")
    resultado = ver_tela_jarvis(
        pergunta=prompt_tecnico
    )
    return resultado

@mcp.tool()
async def list_monitors():
    """
    Lista todos os monitores detectados e seus tamanhos.
    """
    import mss
    with mss.mss() as sct:
        return str(sct.monitors)

@mcp.tool()
async def take_screenshot(monitor_index: int = 1):
    """
    Captura e retorna o caminho de um screenshot do monitor especificado.
    """
    from skills.screen_vision import capturar_tela
    path = capturar_tela(monitor_index=monitor_index)
    return f"Screenshot salvo em: {path}"

@mcp.tool()
async def read_system_health():
    """
    Retorna métricas de saúde do sistema (CPU, RAM, Disco).
    """
    import psutil
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    return f"CPU: {cpu}%, RAM: {ram}%, Disco: {disk}%"

if __name__ == "__main__":
    # Roda o servidor MCP no modo stdio (padrão para Claude Desktop e outros clientes)
    mcp.run()
