"""
Agente Especialista de Conexão com NotebookLM
Utiliza Selenium para se conectar à interface do Jarvis (via porta de depuração do WebView2)
e automatizar interações no painel do NotebookLM, tudo de forma visível para o usuário!
"""
import time
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    pass # Serão instalados caso o usuário ative esse módulo ativamente

def interagir_com_notebooklm(comando: str, conteudo: str = "") -> str:
    """
    Controla o mini-navegador (iframe do NotebookLM) embutido no Jarvis.
    """
    print(f"[NotebookLM Agent] Conectando-se ao Cérebro do J.A.R.V.I.S (Porta 9222)...")
    
    # 1. Configurações para conectar a uma instância ChromeDriver (WebView2 debugging port)
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        # A biblioteca do selenium se conectará à interface já aberta
        driver = webdriver.Chrome(options=chrome_options)
        
        # 2. Muda o foco para o Iframe do NotebookLM (já que o Jarvis tem a janela principal)
        print("[NotebookLM Agent] Procurando Iframe do NotebookLM na interface...")
        espera = WebDriverWait(driver, 5)
        
        # Garante que começa do conteúdo principal da aba
        driver.switch_to.default_content()
        
        # Encontra o iframe mágico que o Jarvis carrega
        try:
            iframe = espera.until(EC.presence_of_element_located((By.ID, "notebook-webview")))
            driver.switch_to.frame(iframe)
            print("[NotebookLM Agent] Iframe acessado com sucesso!")
        except Exception:
            return f"Erro: O painel do NotebookLM não foi encontrado no DOM principal do Jarvis."
        
        # Se o usuário não estiver logado no Google, o NotebookLM vai pedir login.
        # Nesse caso, apenas pedimos para ele fazer isso manualmente na interface.
        if "accounts.google.com" in driver.current_url.lower() or "sign in" in driver.page_source.lower():
            return "STATUS: Bloqueado pelo Google Auth. Por favor, clique na mini-aba do NotebookLM e faça login manualmente primeiro."
            
        print(f"[NotebookLM Agent] Executando comando visível: '{comando}'")
        
        # Exemplo de fluxo básico:
        if "criar projeto" in comando.lower():
            try:
                 new_notebook_btn = espera.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'New Notebook')]")))
                 new_notebook_btn.click()
                 time.sleep(2)
                 return "Notebook criado com sucesso!"
            except Exception as e:
                 return f"Falha ao clicar em 'New Notebook': {e}"
        
        elif "adicionar fonte" in comando.lower():
            if not conteudo:
                return "Erro: Sem conteúdo para adicionar."
            return f"Simular digitação de conteúdo no Notebook ({len(conteudo)} caracteres)..."
            
        else:
             return "Comando desconhecido."
             
    except ImportError:
        return "Erro Crítico: Selenium não instalado. Instale com pip install selenium"
    except Exception as e:
         print(f"[NotebookLM Agent] Falha Crítica: {e}")
         return f"Erro ao acessar o painel do Cérebro: {str(e)}"
