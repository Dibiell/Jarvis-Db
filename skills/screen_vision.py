"""
JARVIS SKILL: Screen Vision (Fase 1)
Permite que o Jarvis "veja" e descreva a tela do usuário em tempo real
usando APIs de visão computacional (Groq Vision / OpenAI Vision).
"""

import base64
import os
import tempfile
import datetime

# ============================================================
# DEPENDÊNCIAS E CONFIGURAÇÃO
# ============================================================

from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()

# Token e Cliente HuggingFace (Módulo Hugin)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
hf_client = InferenceClient(token=HUGGINGFACE_TOKEN) if HUGGINGFACE_TOKEN else None

# Modelos Visuais de Elite (FDM-1 Vision Layer)
MODELO_VISAO_HF = "Salesforce/blip-image-captioning-large"

# ============================================================
# PIPELINE DE COGNIÇÃO DE MÍDIA (FDM-3)
# ============================================================
import threading
import time
from collections import deque
from PIL import Image

class VisionBuffer:
    """Mantém um histórico circular de frames para memória temporal."""
    def __init__(self, size=5):
        self.buffer = deque(maxlen=size)
        self.lock = threading.Lock()

    def add_frame(self, frame_path):
        with self.lock:
            self.buffer.append({
                "path": frame_path,
                "timestamp": datetime.datetime.now()
            })

    def get_latest(self):
        with self.lock:
            return self.buffer[-1] if self.buffer else None

    def get_all(self):
        with self.lock:
            return list(self.buffer)

class VisionPipeline:
    """Gerencia a captura contínua e o processamento de visão em tempo real."""
    def __init__(self):
        self.buffer = VisionBuffer()
        self.active = False
        self._thread = None
        self.fps = 2  # Frequência de captura para o stream HUD
    
    def start(self):
        if not self.active:
            self.active = True
            self._thread = threading.Thread(target=self._run_pipeline, daemon=True)
            self._thread.start()
            print("[Vision] Pipeline de Cognição Contínua Iniciada.")

    def stop(self):
        self.active = False
        print("[Vision] Pipeline de Cognição Encerrada.")

    def _run_pipeline(self):
        while self.active:
            try:
                # Captura frame rápido
                path = capturar_tela()
                if path:
                    self.buffer.add_frame(path)
                    # Opcional: Aqui poderíamos disparar uma análise leve (ex: Título da Janela)
                
                time.sleep(1 / self.fps)
            except Exception as e:
                print(f"[Vision] Erro na Pipeline: {e}")
                time.sleep(1)

# Instância Global da Pipeline
vision_pipeline = VisionPipeline()


# ============================================================
# CAPTURA DE TELA (MULTI-MONITOR)
# ============================================================

def capturar_tela(regiao=None, monitor_index=0):
    """
    Tira um screenshot da tela (ou de uma região) usando MSS (Multi-Monitor).
    
    Args:
        regiao: tupla (x, y, width, height) para capturar só uma parte. None = monitor todo.
        monitor_index: Índice do monitor (0 = todos, 1 = principal, 2... = secundários).
    
    Returns:
        str: Caminho do arquivo .png temporário, ou None em caso de erro.
    """
    try:
        from PIL import Image
        screenshot = None

        # TENTATIVA 1: MSS (Multi-monitor, mais rápido)
        try:
            import mss
            with mss.mss() as sct:
                if monitor_index < len(sct.monitors):
                    monitor = sct.monitors[monitor_index]
                else:
                    monitor = sct.monitors[0]

                if regiao:
                    monitor = {
                        "top": regiao[1],
                        "left": regiao[0],
                        "width": regiao[2],
                        "height": regiao[3],
                        "mon": monitor_index
                    }

                sct_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except (ImportError, Exception) as e:
            if "mss" not in str(e).lower():
                print(f"[Vision] Falha no MSS: {e}")

        # TENTATIVA 2: PyAutoGUI (Fallback universal)
        if screenshot is None:
            try:
                import pyautogui
                # PyAutoGUI tira screenshot do monitor principal
                if regiao:
                    screenshot = pyautogui.screenshot(region=regiao)
                else:
                    screenshot = pyautogui.screenshot()
                print("[Vision] Usando PyAutoGUI como fallback de captura.")
            except Exception as e:
                if "[WinError 740]" in str(e):
                    print("[ERRO CRÍTICO] Falha de Elevação (Admin necessário para capturar certas janelas).")
                print(f"[Vision] Falha total na captura: {e}")
                return None

        # Otimiza o tamanho: reduz para 1280px de largura max
        max_width = 1280
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            nova_altura = int(screenshot.height * ratio)
            screenshot = screenshot.resize((max_width, nova_altura), Image.LANCZOS)
        
        # Salva em arquivo temporário
        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"jarvis_screen_{datetime.datetime.now().strftime('%H%M%S')}.png"
        )
        screenshot.save(tmp_path, "PNG", optimize=True)
        return tmp_path
    
    except Exception as e:
        print(f"[Vision] Erro inesperado ao capturar tela: {e}")
        return None


def imagem_para_base64(image_path):
    """Converte um arquivo de imagem para string Base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        print(f"[Vision] Erro ao converter imagem para base64: {e}")
        return None


# ============================================================
# ANÁLISE DE TELA (VISÃO IA)
# ============================================================

def analisar_tela(pergunta="Descreva detalhadamente o que está na tela", regiao=None):
    """
    Captura a tela e envia para a arquitetura FDM-1 (HuggingFace Vision + DeepSeek Reasoning).
    
    Args:
        pergunta: O que o Jarvis deve observar/perguntar sobre a tela.
        regiao: Região da tela (None = full).
    
    Returns:
        str: Descrição/análise da tela interpretada pelo DeepSeek.
    """
    print("[FDM-1] Iniciando pipeline de visão avançada...")
    
    # 1. Captura a tela
    img_path = capturar_tela(regiao)
    if not img_path:
        return "Não consegui capturar a tela, senhor."
    
    try:
        # Bypassing HuggingFace and directly using the robust OpenRouter/Traditional Vision pipeline
        print("[FDM-1] Fase 1: Percepção Visual via LLMRouter...")
        
        # We explicitly call the traditional fallback because it has been upgraded to use OpenRouter
        # as its primary logic. This completely avoids the fragile HuggingFace Inference Client.
        resultado_visao = _analisar_tela_vision_tradicional(img_path, pergunta)
        
        # Se DeepSeek estiver configurado, passa a visão para ele (Fase 2 de Raciocínio)
        if not resultado_visao.startswith("Falha"):
            print("[FDM-1] Fase 2: Raciocínio Tático via LLMRouter...")
            prompt_fdm = (
                "Você é o núcleo de raciocínio FDM-1 do J.A.R.V.I.S.\n"
                "Aqui está a descrição visual inicial da tela:\n"
                f"--- DESCRIÇÃO TÉCNICA ---\n{resultado_visao}\n\n"
                f"--- ORDEM DO USUÁRIO ---\n{pergunta}\n\n"
                "Sua tarefa: Interprete a visão e responda ao usuário de forma inteligente. "
                "Se for um pedido de automação, detalhe os próximos passos. Responda em Português do Brasil de forma concisa."
            )
            from brain.llm.router import router as llm_router
            try:
                resposta = llm_router.chat(messages=[{"role": "user", "content": prompt_fdm}])
                if resposta.get("text"):
                    return resposta["text"].strip()
            except Exception as e:
                print(f"[FDM-1] Raciocínio Profundo Falhou. Usando resposta visual direta. ({e})")
        
        return resultado_visao

    finally:
        if img_path and os.path.exists(img_path):
            os.remove(img_path)

def analisar_tela_huggingface(img_path, prompt="Describe the image"):
    """Usa o HuggingFace Inference API para analisar a tela."""
    if not hf_client:
        return "Erro: Token HuggingFace não configurado."
    
    try:
        with open(img_path, "rb") as f:
            image_data = f.read()
        
        # Prompt técnico otimizado para FDM-1 (UI & Infographics)
        prompt_tecnico = (
            "Analyze this UI screen. List all interactive elements (buttons, inputs, icons) "
            "with their approximate coordinates [x, y], roles, and labels. "
            "Identify the active window and any visible text."
        )
        
        # Chama o modelo especializado
        print(f"[Hugin] Percebendo Hierarquia de UI via {MODELO_VISAO_HF}...")
        response = hf_client.image_to_text(image_data, model=MODELO_VISAO_HF)
        
        # Alguns modelos retornam uma string, outros uma lista/dict
        if isinstance(response, list) and len(response) > 0:
            return response[0].get('generated_text', str(response))
        return str(response)
        
    except Exception as e:
        print(f"[Hugin] Erro na API HuggingFace: {e}")
        return f"Erro na análise visual: {e}"

def _analisar_tela_vision_tradicional(img_path, pergunta):
    """Fallback: Método original de análise via LLMRouter."""
    # (Movemos a lógica original de analisar_tela para cá)
    try:
        img_b64 = imagem_para_base64(img_path)
        if not img_b64: return "Falha Base64"
        
        prompt_sistema = (
            "Você é o sistema de visão computacional do J.A.R.V.I.S. "
            "Analise a imagem da tela do usuário e responda de forma precisa e útil. "
            "Descreva aplicativos abertos, conteúdo visível, textos importantes, e qualquer coisa relevante. "
            "Seja direto e objetivo. Responda em português do Brasil."
        )
        mensagem_visao = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": pergunta
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_b64}"
                    }
                }
            ]
        }
        
        resultado = None
        
        from brain.llm.router import router as llm_router
        try:
            print("[Vision] Usando LLMRouter Vision...")
            resposta = llm_router.chat(messages=[
                {"role": "system", "content": prompt_sistema},
                mensagem_visao
            ])
            resultado = resposta.get("text", "")
            if resultado:
                print("[Vision] LLMRouter Vision respondeu com sucesso.")
            else:
                print("[Vision] LLMRouter retornou estrutura vazia.")
                resultado = None
        except Exception as e:
            print(f"[Vision] LLMRouter Vision falhou tragicamente: {e}")
            resultado = None
        
        # Fallback final: OCR com pytesseract
        if not resultado:
            resultado = _fallback_ocr(img_path)
        
        return resultado or "Não consegui analisar a tela no momento."
    
    finally:
        # Limpa o arquivo temporário
        try:
            if img_path and os.path.exists(img_path):
                os.remove(img_path)
        except:
            pass


def _fallback_ocr(img_path):
    """
    Fallback: extrai texto da tela usando pytesseract (OCR simples, sem IA).
    Retorna None se pytesseract não estiver instalado.
    """
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r'D:\\Program Files\\Tesseract-OCR\\tesseract.exe'
        from PIL import Image, ImageOps, ImageEnhance
        
        print("[Vision] Usando OCR (pytesseract) com otimização FDM-3...")
        img = Image.open(img_path).convert('L') # Escala de cinza
        
        # Aumentar contraste
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Binarização (Threshold)
        img = img.point(lambda x: 0 if x < 140 else 255, '1')
        
        # OCR com configuração otimizada para blocos de texto
        texto = pytesseract.image_to_string(img, lang="por+eng", config='--psm 3')

        
        if texto.strip():
            return f"[OCR — sem API Vision disponível]\nTexto detectado na tela:\n{texto.strip()}"
        else:
            return "OCR não detectou texto legível na tela."
    
    except ImportError:
        print("[Vision] pytesseract não encontrado. Nenhum fallback disponível.")
        return None
    except Exception as e:
        print(f"[Vision] Erro no OCR: {e}")
        return None


# ============================================================
# ENSINO VISUAL (Fase 4: Multimodal)
# ============================================================

class VisualTeacher:
    """
    Controla a captura periódica de telas para ensinar novas habilidades ao Jarvis/Fire.
    """
    def __init__(self):
        self.esta_observando: bool = False
        self.screenshots: list[str] = []
        self.diretorio_sessao: str = ""
        self.intervalo: float = 1.0 # 1 segundo por padrão
        self._thread = None

    def iniciar_sessao(self, intervalo=1.0):
        import time
        import threading
        self.esta_observando = True
        self.screenshots = []
        self.intervalo = intervalo
        
        # Cria um diretório temporário
        self.diretorio_sessao = os.path.join(tempfile.gettempdir(), f"jarvis_teaching_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.diretorio_sessao, exist_ok=True)
        
        print(f"[VisualTeacher] Streaming iniciado em: {self.diretorio_sessao}")
        
        # Inicia thread de background
        def background_stream():
            while self.esta_observando:
                self.capturar_passo()
                time.sleep(self.intervalo)
        
        self._thread = threading.Thread(target=background_stream, daemon=True)
        self._thread.start()
        
        return f"Protocolo FDM-1 de Streaming ativado. Observando sua tela a cada {self.intervalo}s."

    def capturar_passo(self):
        """Tira um screenshot e salva na lista da sessão."""
        if not self.esta_observando:
            return
        
        caminho = capturar_tela()
        if caminho:
            # Move do temp geral para o da sessão
            novo_nome = f"step_{len(self.screenshots):03d}.png"
            novo_caminho = os.path.join(self.diretorio_sessao, novo_nome)
            import shutil
            shutil.move(caminho, novo_caminho)
            self.screenshots.append(novo_caminho)
            print(f"[VisualTeacher] Passo {len(self.screenshots)} capturado.")

    def parar_sessao(self):
        self.esta_observando = False
        num_fotos = len(self.screenshots)
        return f"Sessão de ensino finalizada. Capturei {num_fotos} imagens da sua tela para análise."

    def analisar_aprendizado(self):
        """
        Envia a sequência de imagens para a IA para extrair a lógica e identificar anomalias.
        """
        if not self.screenshots:
            return "Não há imagens para analisar, senhor."

        # Para evitar estourar o contexto, pegamos no máximo 10 fotos (início, meio, fim)
        selecao = self.screenshots
        if len(selecao) > 10:
            indices = [int(i * (len(selecao)-1) / 9) for i in range(10)]
            selecao = [selecao[i] for i in indices]

        print(f"[VisualTeacher] Analisando sequência de {len(selecao)} imagens...")
        
        prompt_ensino = (
            "Você é o instrutor do J.A.R.V.I.S. e do FIRE (gerador de agentes).\n"
            "Analise esta sequência de capturas de tela que mostram o usuário realizando uma tarefa.\n"
            "IDENTIFIQUE CADA PASSO: (Ex: 'Abriu o navegador', 'Entrou no site X', 'Fez login').\n"
            "DETECÇÃO DE ANOMALIA: Identifique comportamentos inesperados, falhas, ou erros visíveis.\n"
            "Responda em português, de forma estruturada:\n"
            "1. RESUMO: Descrição da tarefa.\n"
            "2. PASSOS: Lista detalhada do que foi feito.\n"
            "3. ANOMALIAS: Relate qualquer problema detectado.\n"
            "4. LÓGICA TÉCNICA: Descrição para criação de automação."
        )

        # Monta a mensagem multimodal
        conteudo = [{"type": "text", "text": "Analise o processo nestas imagens."}]
        for path in selecao:
            b64 = imagem_para_base64(path)
            if b64:
                conteudo.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                })

        mensagem_visao = {"role": "user", "content": conteudo}
        
        resultado = None
        from brain.llm.router import router as llm_router
        try:
            print("[VisualTeacher] Usando Pipeline FDM-1 via LLMRouter...")
            estudo_caso = self.screenshots[-1] if self.screenshots else None
            if estudo_caso:
                descricao_visual = analisar_tela_huggingface(estudo_caso, "Describe the actions performed in this screen sequence.")
                prompt_aprendizado = (
                    "Você é o instrutor FDM-1.\n"
                    f"Descrição visual da tarefa: {descricao_visual}\n"
                    "Gere um relatório estruturado de aprendizado em Português."
                )
                resposta = llm_router.chat(messages=[{"role": "user", "content": prompt_aprendizado}])
                resultado = resposta.get("text", "")
        except Exception as e:
            print(f"[VisualTeacher] Erro no Pipeline FDM-1: {e}")
            resultado = None

        if not resultado:
            try:
                print("[VisualTeacher] Fallback para LLMRouter (uma imagem)...")
                resultado = ver_tela_jarvis("Descreva o que foi feito baseado nesta imagem final do processo.")
            except Exception as e:
                print(f"[VisualTeacher] Erro no fallback Groq: {e}")

        return resultado or "Houve um erro ao processar a sequência de imagens via IA, senhor."


# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# FUNÇÃO DE CONVENIÊNCIA (chamada pelo Jarvis)
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

def ver_tela_jarvis(pergunta=None):
    """
    Interface principal para o Jarvis chamar o sistema de visão (FDM-1).
    Extrai o contexto da pergunta e analisa a tela.
    """
    if not pergunta:
        pergunta = "Descreva tudo que está visível na tela: aplicativos abertos, conteúdo, textos, janelas ativas."
    
    return analisar_tela(
        pergunta=pergunta
    )
