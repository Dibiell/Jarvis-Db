import requests
from bs4 import BeautifulSoup
import urllib.parse
import json

def pesquisar_na_web(termo_de_busca: str) -> str:
    """
    Realiza uma pesquisa na web de forma invisível/em background usando DuckDuckGo Lite 
    (para evitar captchas ou bloqueios de scraping simples) e extrai os melhores resultados.
    Útil para responder perguntas recentes, extrair informações factuais ou dar contexto à IA.
    
    Args:
        termo_de_busca: O que o usuário deseja pesquisar.
    """
    print(f"[BrowserAgent] Pesquisando na web por: '{termo_de_busca}'...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Usamos duckduckgo html version que é friendly para scraping
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(termo_de_busca)}"
        response = requests.get(url, headers=headers, timeout=10)
        
        # O DuckDuckGo às vezes retorna 202 (Accepted) se estiver processando. Tratamos como falha para ir ao fallback.
        if response.status_code != 200:
            print(f"[BrowserAgent] Status {response.status_code} no DuckDuckGo. Tentando fallback...")
            return _pesquisar_google_fallback(termo_de_busca)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        resultados = []
        for a in soup.find_all('a', class_='result__snippet', limit=4):
             texto = a.get_text(strip=True)
             if texto:
                 resultados.append(texto)
                 
        if not resultados:
            # Tenta fallback para o google (embora haja mais chance de captcha)
            return _pesquisar_google_fallback(termo_de_busca)
            
        resposta = "\n".join([f"- {r}" for r in resultados])
        return f"Resultados da pesquisa para '{termo_de_busca}':\n{resposta}"
        
    except Exception as e:
        return f"Falha ao executar a pesquisa na web: {str(e)}"

def _pesquisar_google_fallback(termo: str) -> str:
    """Tenta um scraper super básico do google case duckduckgo falhe."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        url = f"https://www.google.com/search?q={urllib.parse.quote(termo)}&hl=pt-BR"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return "Nenhum resultado encontrado. Pesquisa bloqueada."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        snippets = []
        # Tenta pegar os text-blocks de destaque (Knowledge Box, etc)
        destaque = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
        if destaque:
            snippets.append(f"Destaque: {destaque.get_text(strip=True)}")
            
        for g in soup.find_all('div', class_='BNeawe s3v9rd AP7Wnd', limit=3):
            t = g.get_text(strip=True)
            if t and t not in snippets:
                snippets.append(t)
                
        if snippets:
             resposta = "\n".join([f"- {r}" for r in snippets[:3]])
             return f"Resultados principais do Google para '{termo}':\n{resposta}"
             
        return "Nenhum resumo em texto pôde ser extraído da busca."
    except Exception as e:
        return f"Erro de pesquisa: {str(e)}"
