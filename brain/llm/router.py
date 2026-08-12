"""
JARVIS BRAIN - Router de LLM
Ponto único de entrada pra falar com IA no Jarvis. Substitui as funções
consultar_ia / _chamar_provedor_ia_global / _chamar_provedor_ia_core do
jarvis.py antigo, que dependiam do Groq.

Ordem de tentativa: Gemini (pool) -> OpenRouter (fallback).
Se os dois falharem, levanta AllProvidersFailedError - quem chama decide
o que fazer (avisar o usuário por voz, por ex).
"""

import os
from .providers import GeminiProvider, OpenRouterProvider, AllProvidersFailedError


class LLMRouter:
    def __init__(self):
        self.providers: list = []
        self._montar_providers()

    def _montar_providers(self):
        # --- Gemini: pool de chaves via .env ---
        # GEMINI_API_KEYS="chave1,chave2,chave3"
        # GEMINI_API_KEYS_NOMES="Henrique,Laura,Claudio"   (opcional, só pra log)
        chaves_raw = os.getenv("GEMINI_API_KEYS", "")
        chaves = [k.strip() for k in chaves_raw.split(",") if k.strip()]
        nomes_raw = os.getenv("GEMINI_API_KEYS_NOMES", "")
        nomes = [n.strip() for n in nomes_raw.split(",") if n.strip()] or None

        if chaves:
            self.providers.append(GeminiProvider(api_keys=chaves, key_names=nomes))
        else:
            print("[LLMRouter] AVISO: nenhuma GEMINI_API_KEYS configurada no .env.")

        # --- OpenRouter: fallback ---
        or_key = os.getenv("OPENROUTER_API_KEY", "")
        if or_key:
            self.providers.append(OpenRouterProvider(api_key=or_key))
        else:
            print("[LLMRouter] AVISO: nenhuma OPENROUTER_API_KEY configurada (fallback desativado).")

        if not self.providers:
            raise RuntimeError(
                "Nenhum provedor de IA configurado. Preencha GEMINI_API_KEYS e/ou "
                "OPENROUTER_API_KEY no .env."
            )

    def chat(self, messages: list, tools: list | None = None, temperature: float = 0.7) -> dict:
        """
        Tenta cada provedor na ordem (Gemini primeiro, OpenRouter depois).
        Retorna o dict padronizado de LLMProvider.chat().
        """
        erros = []
        for provider in self.providers:
            try:
                resultado = provider.chat(messages, tools=tools, temperature=temperature)
                return resultado
            except AllProvidersFailedError as e:
                erros.append(f"{provider.name}: {e}")
                print(f"[LLMRouter] {provider.name} esgotado, tentando próximo provedor...")
            except Exception as e:
                erros.append(f"{provider.name}: {e}")
                print(f"[LLMRouter] Erro inesperado em {provider.name}: {e}")

        raise AllProvidersFailedError(
            "Todos os provedores de IA falharam:\n" + "\n".join(erros)
        )


# Instância única, importada por quem precisar (ex: brain/core.py)
router = LLMRouter()
