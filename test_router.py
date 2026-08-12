"""
Teste rápido do LLMRouter: manda uma pergunta simples e uma com tool call.
Rodar da raiz do projeto, com o .env já preenchido:
    python test_router.py
"""
from dotenv import load_dotenv
load_dotenv()

from brain.llm.router import router

# Teste 1: conversa simples, sem tools
print("=== Teste 1: conversa simples ===")
resultado = router.chat(messages=[
    {"role": "system", "content": "Você é o Jarvis, um assistente direto e cordial."},
    {"role": "user", "content": "Em uma frase, o que é Python?"}
])
print(f"[{resultado['provider']}] {resultado['text']}")
print()

# Teste 2: com tool call (formato igual ao TOOLS do jarvis.py antigo)
print("=== Teste 2: tool calling ===")
tools = [{
    "type": "function",
    "function": {
        "name": "abrir_aplicativo",
        "description": "Abre um aplicativo no computador do usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "nome_app": {"type": "string", "description": "Nome do app, ex: 'bloco de notas'"}
            },
            "required": ["nome_app"]
        }
    }
}]
resultado = router.chat(messages=[
    {"role": "system", "content": "Você é o Jarvis. Use as ferramentas disponíveis quando fizer sentido."},
    {"role": "user", "content": "Abre o bloco de notas pra mim"}
], tools=tools)
print(f"[{resultado['provider']}] texto: {resultado['text']}")
print(f"tool_calls: {resultado['tool_calls']}")
