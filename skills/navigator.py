import asyncio
import os
import sys
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

class Navigator:
    """
    JARVIS SKILL: Navigator (Autonomous Browser)
    Engine: Playwright (Chromium)
    Capability: Advanced web research, interaction, and data extraction.
    """
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    def search_and_extract(self, query: str, deep_dive: bool = False) -> str:
        """
        Performs a search and extracts relevant information with multi-path fallbacks.
        """
        print(f"[Navigator] Iniciando pesquisa de elite para: '{query}'...")
        
        # TENTATIVA 1: Playwright (Alta Fidelidade)
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )
                page = context.new_page()
                
                print("[Navigator] Tentando DuckDuckGo (Playwright)...")
                page.goto(f"https://duckduckgo.com/?q={query.replace(' ', '+')}", timeout=15000)
                page.wait_for_selector("article, .result", timeout=10000)
                
                links = page.query_selector_all("article a, .result__title a")
                valid_links = [l.get_attribute("href") for l in links if l.get_attribute("href") and "http" in l.get_attribute("href")][:3]
                
                if valid_links:
                    content_snippets = []
                    for url in valid_links:
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=12000)
                            text = page.inner_text("body")
                            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 50]
                            content_snippets.append(f"--- FONTE (FDM-1): {url} ---\n" + "\n".join(lines[:10]))
                        except: continue
                    if content_snippets: return "\n\n".join(content_snippets)
            except Exception as e:
                print(f"[Navigator] Falha no Playwright: {e}")
            finally:
                try: browser.close()
                except: pass

        # TENTATIVA 2: Fallback Resiliente (Requests + BS4 + DDG Lite)
        print("[Navigator] Ativando Protocolo de Segurança (Fallback Resiliente)...")
        import requests
        from bs4 import BeautifulSoup
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            snippets = [s.get_text() for s in soup.find_all('a', class_='result__snippet', limit=5)]
            if snippets:
                return "--- PESQUISA RESILIENTE (BACKUP) ---\n" + "\n".join([f"- {s}" for s in snippets])
        except Exception as e:
            return f"Falha total em todos os protocolos de pesquisa: {e}"

        return "Não consegui obter dados úteis nem via Playwright nem via Fallback, senhor."

# Interface para o JARVIS
def pesquisar_navigator(query: str, deep_dive: bool = False) -> str:
    nav = Navigator()
    return nav.search_and_extract(query, deep_dive)

# Interface para o JARVIS
def pesquisar_navigator(query: str, deep_dive: bool = False) -> str:
    nav = Navigator()
    return nav.search_and_extract(query, deep_dive)
