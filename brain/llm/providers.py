"""
JARVIS BRAIN - Provedores de LLM
Substitui o Groq. Dois provedores:
  - GeminiProvider: pool rotativo de chaves gratuitas (AI Studio)
  - OpenRouterProvider: fallback pago/estável

Ambos expõem a MESMA interface (LLMProvider), aceitando o mesmo formato
de "tools" no padrão OpenAI (o mesmo dict que já existe em TOOLS no
jarvis.py) - a tradução pro formato de cada provedor acontece aqui dentro.
"""

import os
import json
import time
from abc import ABC, abstractmethod


# ============================================================
# CONTRATO COMUM
# ============================================================

class LLMProvider(ABC):
    name = "base"

    @abstractmethod
    def chat(self, messages: list, tools: list | None = None, temperature: float = 0.7) -> dict:
        """
        messages: lista no formato OpenAI [{"role": "...", "content": "..."}]
        tools: lista de tools no formato OpenAI (mesmo formato do TOOLS antigo)

        Retorna sempre um dict padronizado:
        {
            "text": str | None,          # resposta em texto (se houver)
            "tool_calls": [               # lista de chamadas de ferramenta (se houver)
                {"name": str, "arguments": dict, "id": str}
            ],
            "provider": str,              # quem respondeu de fato
            "raw": Any                    # resposta crua, pra debug
        }
        """
        raise NotImplementedError


class AllProvidersFailedError(Exception):
    pass


# ============================================================
# GEMINI (pool rotativo de chaves gratuitas)
# ============================================================

class GeminiProvider(LLMProvider):
    name = "gemini"

    # Erros que indicam "troca de chave e tenta de novo", não "desiste"
    _ERROS_ROTACIONAVEIS = ("RESOURCE_EXHAUSTED", "429", "rate", "quota", "PERMISSION_DENIED", "403")

    def __init__(self, api_keys: list[str], key_names: list[str] | None = None,
                 model: str = "gemini-flash-latest"):
        if not api_keys:
            raise ValueError("GeminiProvider precisa de pelo menos 1 API key.")
        self.api_keys = api_keys
        self.key_names = key_names or [f"key_{i+1}" for i in range(len(api_keys))]
        self.model = model
        self._idx = 0  # aponta pra chave "atual"

    def _proxima_chave(self):
        """Roda o índice pra próxima chave do pool (round-robin)."""
        self._idx = (self._idx + 1) % len(self.api_keys)

    def _client_atual(self):
        from google import genai
        return genai.Client(api_key=self.api_keys[self._idx])

    @staticmethod
    def _tools_openai_para_gemini(tools_openai: list | None):
        """Converte o formato TOOLS (OpenAI) pro formato de Tool do Gemini."""
        if not tools_openai:
            return None
        from google.genai import types

        declaracoes = []
        for t in tools_openai:
            fn = t.get("function", t)  # aceita tanto {"type":"function","function":{...}} quanto já achatado
            declaracoes.append(
                types.FunctionDeclaration(
                    name=fn["name"],
                    description=fn.get("description", ""),
                    parameters=fn.get("parameters", {"type": "object", "properties": {}}),
                )
            )
        return [types.Tool(function_declarations=declaracoes)]

    @staticmethod
    def _mensagens_openai_para_gemini(messages: list):
        """Converte histórico estilo OpenAI (role/content) pro formato Gemini (role/parts),
        separando a mensagem de sistema (Gemini trata system_instruction à parte)."""
        from google.genai import types

        system_instruction = None
        contents = []
        for m in messages:
            role = m.get("role")
            content = m.get("content") or ""
            if role == "system":
                system_instruction = (system_instruction + "\n" + content) if system_instruction else content
                continue
            gemini_role = "model" if role == "assistant" else "user"
            contents.append(types.Content(role=gemini_role, parts=[types.Part(text=content)]))
        return system_instruction, contents

    def chat(self, messages: list, tools: list | None = None, temperature: float = 0.7) -> dict:
        from google.genai import types

        system_instruction, contents = self._mensagens_openai_para_gemini(messages)
        gemini_tools = self._tools_openai_para_gemini(tools)

        tentativas = len(self.api_keys)
        ultimo_erro = None

        for _ in range(tentativas):
            nome_chave = self.key_names[self._idx]
            try:
                client = self._client_atual()
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    tools=gemini_tools,
                )
                resp = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                return self._parse_resposta(resp, nome_chave)

            except Exception as e:
                erro_str = str(e)
                ultimo_erro = e
                rotacionavel = any(marcador in erro_str for marcador in self._ERROS_ROTACIONAVEIS)
                print(f"[Gemini] Falha na chave '{nome_chave}': {erro_str[:200]}"
                      f" -> {'rotacionando' if rotacionavel else 'erro não-rotacionável'}")
                self._proxima_chave()
                if not rotacionavel:
                    # erro que não tem a ver com quota/limite (ex: prompt inválido) -
                    # trocar de chave não vai resolver, mas ainda tentamos 1x na próxima
                    # chave por segurança antes de desistir do Gemini como um todo.
                    continue

        raise AllProvidersFailedError(f"Todas as {len(self.api_keys)} chaves Gemini falharam. Último erro: {ultimo_erro}")

    def _parse_resposta(self, resp, nome_chave: str) -> dict:
        texto = None
        tool_calls = []

        try:
            texto = resp.text
        except Exception:
            texto = None

        candidatos = getattr(resp, "candidates", None) or []
        if candidatos:
            partes = getattr(candidatos[0].content, "parts", None) or []
            for i, parte in enumerate(partes):
                fc = getattr(parte, "function_call", None)
                if fc:
                    tool_calls.append({
                        "id": f"gemini_call_{i}",
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })

        return {
            "text": texto,
            "tool_calls": tool_calls,
            "provider": f"gemini:{nome_chave}",
            "raw": resp,
        }


# ============================================================
# OPENROUTER (fallback)
# ============================================================

class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def __init__(self, api_key: str, model: str = "meta-llama/llama-3.1-70b-instruct"):
        if not api_key:
            raise ValueError("OpenRouterProvider precisa de uma API key.")
        self.api_key = api_key
        self.model = model

    def _client(self):
        from openai import OpenAI
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)

    def chat(self, messages: list, tools: list | None = None, temperature: float = 0.7) -> dict:
        client = self._client()
        kwargs = {"model": self.model, "messages": messages, "temperature": temperature}
        if tools:
            kwargs["tools"] = tools

        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        tool_calls = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {}
            tool_calls.append({"id": tc.id, "name": tc.function.name, "arguments": args})

        return {
            "text": msg.content,
            "tool_calls": tool_calls,
            "provider": f"openrouter:{self.model}",
            "raw": resp,
        }
