"""
JARVIS BRAIN - Núcleo (o loop observa -> age -> reobserva)

Isso substitui o "planeja tudo de uma vez e executa cego" do
sequence_executor.py antigo. Aqui a IA decide UM passo por vez, o passo
executa de verdade, o resultado volta pra IA, e só aí ela decide o
próximo passo - igual o padrão do UseJarvis/Antigravity que
pesquisamos.

LIMITAÇÃO CONHECIDA (v1): o LLMRouter.chat() hoje não tem um "papel"
formal de resultado-de-ferramenta (function_response) pros provedores -
aqui a gente simula isso mandando o resultado como uma mensagem de
usuário descrevendo o que aconteceu. Funciona bem na prática, mas é uma
simplificação. Se no futuro precisarmos de mais precisão, dá pra evoluir
o router pra aceitar role="tool" de verdade.
"""

import json
from brain.llm.router import router as llm_router
from brain.tools import desktop, browser


MAX_PASSOS = 12

FRASES_DESATIVAR_MOUSE = (
    "sem usar o mouse", "sem mouse", "não use o mouse", "nao use o mouse",
    "sem usar mouse", "não usar o mouse", "nao usar o mouse",
)

TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "abrir_aplicativo",
        "description": "Abre um programa no computador (ex: bloco de notas, calculadora, chrome).",
        "parameters": {"type": "object", "properties": {
            "nome_app": {"type": "string"}
        }, "required": ["nome_app"]}
    }},
    {"type": "function", "function": {
        "name": "digitar_no_app_ativo",
        "description": "Digita um texto na janela de aplicativo nativo que estiver em foco agora.",
        "parameters": {"type": "object", "properties": {
            "texto": {"type": "string"}
        }, "required": ["texto"]}
    }},
    {"type": "function", "function": {
        "name": "listar_janelas",
        "description": "Lista as janelas de aplicativos abertas no momento, pra saber o estado atual do PC.",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "navegar",
        "description": "Abre/navega o navegador pra uma URL (ex: google.com, translate.google.com).",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}
        }, "required": ["url"]}
    }},
    {"type": "function", "function": {
        "name": "ler_elementos_visiveis",
        "description": "Lê os botões/campos/links visíveis na página atual do navegador, pra saber em que clicar ou digitar.",
        "parameters": {"type": "object", "properties": {}}
    }},
    {"type": "function", "function": {
        "name": "clicar_elemento",
        "description": "Clica num elemento da página atual do navegador, identificado pelo texto dele.",
        "parameters": {"type": "object", "properties": {
            "texto_do_elemento": {"type": "string"}
        }, "required": ["texto_do_elemento"]}
    }},
    {"type": "function", "function": {
        "name": "digitar_no_elemento",
        "description": "Digita texto num campo da página atual do navegador (identificado por placeholder/label).",
        "parameters": {"type": "object", "properties": {
            "texto_do_elemento": {"type": "string"},
            "texto_a_digitar": {"type": "string"}
        }, "required": ["texto_do_elemento", "texto_a_digitar"]}
    }},
    {"type": "function", "function": {
        "name": "tarefa_concluida",
        "description": "Chame isso quando a tarefa pedida pelo usuário já foi cumprida por completo.",
        "parameters": {"type": "object", "properties": {
            "resumo": {"type": "string", "description": "Resumo curto do que foi feito"}
        }, "required": ["resumo"]}
    }},
]

TOOL_DISPATCH = {
    "abrir_aplicativo": lambda args: desktop.abrir_aplicativo(args["nome_app"]),
    "digitar_no_app_ativo": lambda args: desktop.digitar_no_app_ativo(args["texto"]),
    "listar_janelas": lambda args: desktop.listar_janelas(),
    "navegar": lambda args: browser.navegar(args["url"]),
    "ler_elementos_visiveis": lambda args: browser.ler_elementos_visiveis(),
    "clicar_elemento": lambda args: browser.clicar_elemento(args["texto_do_elemento"]),
    "digitar_no_elemento": lambda args: browser.digitar_no_elemento(
        args["texto_do_elemento"], args["texto_a_digitar"]
    ),
}

SYSTEM_PROMPT = """Você é o Jarvis, executando tarefas no computador do usuário passo a passo.

Regras importantes:
- NUNCA descreva em texto que vai usar uma ferramenta (ex: escrever "vou
  abrir o bloco de notas"). Sempre CHAME a ferramenta de verdade através
  da função disponível. Texto puro só é aceitável na resposta FINAL,
  depois de já ter chamado tarefa_concluida.
- Decida e execute UM passo por vez. Nunca assuma que um passo anterior
  funcionou sem ver o resultado dele.
- Depois de cada ferramenta que você chama, o resultado real volta pra
  você antes do próximo passo - use isso pra ajustar o plano se algo
  deu diferente do esperado.
- Quando for escrever um texto sobre algum assunto (ex: "escreva sobre
  a Segunda Guerra Mundial"), gere você mesmo esse conteúdo dentro do
  parâmetro de texto da ferramenta de digitação - não peça confirmação.
- Quando a tarefa pedida estiver 100% concluída, chame a ferramenta
  tarefa_concluida com um resumo curto do que foi feito.
- Se uma ferramenta falhar, tente entender o motivo pelo resultado e
  ajuste (ex: tentar de novo, abrir a janela certa primeiro, etc.) em
  vez de simplesmente desistir.
"""


def executar_comando(comando_usuario: str, log_callback=None) -> str:
    """
    Executa um comando de voz/texto multi-etapa, retornando o resumo
    final. log_callback (opcional) recebe uma string a cada passo, pra
    exibir na UI/log em tempo real.
    """
    def log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    # Modo mouse real é ligado por padrão - só desliga se o próprio
    # comando pedir explicitamente (voltando a ligar depois, pro próximo
    # comando não ficar "preso" no modo sem mouse por engano)
    comando_lower = comando_usuario.lower()
    pediu_sem_mouse = any(frase in comando_lower for frase in FRASES_DESATIVAR_MOUSE)
    browser.definir_modo_mouse(not pediu_sem_mouse)
    if pediu_sem_mouse:
        log("[Config] Mouse real desativado pra este comando (clique sintético).")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": comando_usuario},
    ]

    for passo in range(1, MAX_PASSOS + 1):
        resultado = llm_router.chat(messages=messages, tools=TOOLS_SCHEMA)
        log(f"[Passo {passo}] (respondido por: {resultado['provider']})")

        if not resultado["tool_calls"]:
            # IA respondeu só com texto, sem chamar ferramenta - considera final
            log(f"[Passo {passo}] Resposta final sem ferramenta: {resultado['text']}")
            return resultado["text"] or "Terminei, mas não tenho um resumo pra dar."

        chamada = resultado["tool_calls"][0]  # um passo por vez, de propósito
        nome_ferramenta = chamada["name"]
        args = chamada["arguments"]

        if nome_ferramenta == "tarefa_concluida":
            resumo = args.get("resumo", "Tarefa concluída.")
            log(f"[Passo {passo}] Tarefa concluída: {resumo}")
            return resumo

        log(f"[Passo {passo}] Executando: {nome_ferramenta}({args})")

        funcao = TOOL_DISPATCH.get(nome_ferramenta)
        if funcao is None:
            resultado_execucao = {"sucesso": False, "mensagem": f"Ferramenta desconhecida: {nome_ferramenta}"}
        else:
            try:
                resultado_execucao = funcao(args)
            except Exception as e:
                resultado_execucao = {"sucesso": False, "mensagem": f"Erro ao executar: {e}"}

        log(f"[Passo {passo}] Resultado: {resultado_execucao}")

        # Registra só o RESULTADO real de volta na conversa - de propósito
        # sem simular uma fala do assistente tipo "vou usar X(...)", porque
        # isso ensina o modelo (por imitação do próprio histórico) a apenas
        # ESCREVER que vai chamar a ferramenta em vez de chamar de verdade.
        messages.append({
            "role": "user",
            "content": (
                f"[SISTEMA] Resultado da ferramenta '{nome_ferramenta}' que você acabou de chamar: "
                f"{json.dumps(resultado_execucao, ensure_ascii=False)}. "
                f"Continue a tarefa chamando a PRÓXIMA ferramenta necessária (não apenas descreva em texto)."
            )
        })

    log("[Aviso] Limite de passos atingido sem a IA sinalizar conclusão.")
    return "Não consegui terminar a tarefa dentro do limite de passos - pode ter ficado parcialmente feita."
