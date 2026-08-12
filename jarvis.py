import logging
import traceback
import os
import sys
import time
import ctypes
import math

# Configuração de Log para capturar erros silenciosos
logging.basicConfig(filename='jarvis_startup_debug.log', level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("--- SESSÃO DE INICIALIZAÇÃO INICIADA (Eventlet OFF) ---")

# Bloco de Importação Seguro
try:
    import speech_recognition as sr
    import pyttsx3
    import datetime
    import webbrowser
    import wikipedia
    import subprocess
    import tempfile
    import threading
    import queue
    import asyncio
    import edge_tts
    import pygame
    import pythoncom
    import ctypes.wintypes
    import webview
    import flask
    from flask import Flask, render_template, request, send_from_directory
    from flask_socketio import SocketIO, emit
    import socket
    from huggingface_hub import InferenceClient
    import psutil
    from openai import OpenAI
    from anthropic import Anthropic
    import pyperclip
    import re
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"\n[ERRO DE IMPORTAÇÃO] Falha ao carregar bibliotecas core: {e}")
    traceback.print_exc()
    input("Pressione Enter para sair...")
    sys.exit(1)

# Força o diretório de trabalho
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Silenciar logs do Flask e SocketIO
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)

# Garante que avisos de protocolo não sujem o terminal
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="flask_socketio")

# Cliente OpenRouter (Cérebro Elite)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
PREMIUM_MODELS = {
    "CODE_EXPERT": "google/gemini-2.0-pro-exp-02-05", # O cérebro mais potente disponível
    "VISAO_TELA": "google/gemini-2.0-pro-exp-02-05", 
    "PESQUISA_WEB": "google/gemini-2.0-flash-001", # Flash para velocidade na web
    "CONVERSACAO": "google/gemini-2.0-pro-exp-02-05",
    "AUTOMACAO_SISTEMA": "google/gemini-2.0-pro-exp-02-05",
    "RACIOCINIO_PROFUNDO": "deepseek/deepseek-r1"
}

# Clientes Globais de IA
cliente_openrouter = None
openai_client = None
anthropic_client = None

# Configurações do HuggingFace (Módulo Hugin)
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
hf_client = InferenceClient(token=HUGGINGFACE_TOKEN) if HUGGINGFACE_TOKEN else None

# ============================================================
# AUTO-ELEVAÇÃO (ADMINISTRADOR)
# ============================================================
def re_launch_as_admin():
    """Tenta relançar o script com permissões de administrador se necessário."""
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if not is_admin:
            print("[SISTEMA] Permissões insuficientes. Solicitando elevação...", flush=True)
            # Tenta relançar usando ShellExecute com 'runas'
            # sys.executable é o caminho do python.exe
            # sys.argv são os argumentos (incluindo o caminho do jarvis.py)
            script = os.path.abspath(sys.argv[0])
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
            sys.exit(0)
    except Exception as e:
        print(f"[ERRO ELEVAÇÃO] Falha ao tentar elevar: {e}", flush=True)

# re_launch_as_admin() # Movido para o bloco if __name__ == "__main__"

# ============================================================
# INICIALIZAÇÃO DO TTS (VOZ) - THREAD DEDICADA E SEGURA (FILA)
# ============================================================
tts_queue = queue.Queue()

# --- Configuração de Voz Neural ---
VOICE_EN = "en-GB-RyanNeural"  # O legitimo Jarvis (Paul Bettany style)
VOICE_PT = "pt-BR-AntonioNeural" # Voz masculina brasileira premium
CURRENT_VOICE = VOICE_PT # Padrão PT-BR, mas Jarvis muda se solicitado

def tts_worker():
    """Thread dedicada para processar a fila de voz usando Edge-TTS (Neural)."""
    pygame.mixer.init()
    
    # Fallback worker case algo dê errado
    def fallback_speak(text):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            for voice in voices:
                if "Brazil" in voice.name or "Portuguese" in voice.name:
                    engine.setProperty('voice', voice.id)
                    break
            engine.say(text)
            engine.runAndWait()
        except:
            pass

    async def generate_and_play(text):
        try:
            global openai_client, local_xtts_model
            if 'local_xtts_model' not in globals():
                global local_xtts_model
                local_xtts_model = None

            tmp_path = None
            
            # Corrige duplo .wav oculto pelo Windows
            caminho_ref = "jarvis_referencia.wav"
            if not os.path.exists(caminho_ref) and os.path.exists("jarvis_referencia.wav.wav"):
                caminho_ref = "jarvis_referencia.wav.wav"
            
            # Prioridade Suprema: Clonagem de Voz Local (Fase 5)
            if os.path.exists(caminho_ref):
                try:
                    def fetch_audio_xtts():
                        global local_xtts_model
                        import torch
                        from TTS.api import TTS
                        
                        if local_xtts_model is None:
                            print("[TTS] Carregando Motor de Clonagem XTTS-v2 na VRAM... (Isso pode demorar na 1ª vez)", flush=True)
                            # Silencia logs chatos do TTS
                            os.environ["COQUI_TOS_AGREED"] = "1"
                            # Bypass de segurança universal para PyTorch 2.6+ (weights_only=True)
                            try:
                                import torch
                                _original_load = torch.load
                                def _unsafe_load(*args, **kwargs):
                                    kwargs['weights_only'] = False
                                    return _original_load(*args, **kwargs)
                                torch.load = _unsafe_load

                                # Workaround para erro do torchcodec / DLL no PyTorch 2.6+
                                import torchaudio
                                import soundfile as sf
                                def _custom_torchaudio_load(filepath, *args, **kwargs):
                                    data, sr = sf.read(filepath)
                                    tensor = torch.tensor(data)
                                    if tensor.ndim == 1:
                                        tensor = tensor.unsqueeze(0)
                                    else:
                                        tensor = tensor.T
                                    if tensor.dtype == torch.float64:
                                        tensor = tensor.float()
                                    return tensor, sr
                                torchaudio.load = _custom_torchaudio_load
                                
                            except Exception:
                                pass
                                
                            device = "cuda" if torch.cuda.is_available() else "cpu"
                            if device == "cpu":
                                print("[AVISO] GPU não detectada. O XTTS usará CPU (Geração lenta).", flush=True)
                            else:
                                print(f"[TTS] Usando aceleração GPU ({torch.cuda.get_device_name(0)}).", flush=True)
                                
                            local_xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
                        
                        print("\n[TTS] Gerando Voz Clonada (XTTS-v2)...", flush=True)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                            local_xtts_model.tts_to_file(
                                text=text,
                                speaker_wav=caminho_ref,
                                language="pt",
                                file_path=tmp_file.name
                            )
                            return tmp_file.name
                            
                    tmp_path = await asyncio.to_thread(fetch_audio_xtts)
                except Exception as e:
                    import traceback
                    print(f"\n[ERRO CRÍTICO XTTS] Falha ao clonar voz: {e}", flush=True)
                    traceback.print_exc()
                    print("[Fallback para TTS em Nuvem...]", flush=True)
            
            if not tmp_path and openai_client:
                # Usa OpenAI TTS (Voz 'onyx' é masculina, grave e excelente para inteligências artificiais)
                print("[TTS] Gerando voz neural Premium (OpenAI HD)...", flush=True)
                def fetch_audio():
                    response = openai_client.audio.speech.create(
                        model="tts-1-hd",
                        voice="onyx",
                        input=text
                    )
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        response.stream_to_file(tmp_file.name)
                        return tmp_file.name
                
                tmp_path = await asyncio.to_thread(fetch_audio)
            elif not tmp_path:
                # Determina a voz (Edge-TTS Fallback)
                voice = CURRENT_VOICE
                
                communicate = edge_tts.Communicate(text, voice)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    tmp_path = tmp_file.name
                
                await communicate.save(tmp_path)
            
            # Toca o áudio
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            
            # Emissão de ritmo em tempo real para a GUI
            while pygame.mixer.music.get_busy():
                import random
                # Simula dados de amplitude (volume) e cadência baseados no tempo
                amplitude = random.randint(30, 95)
                cadencia = random.randint(20, 80)
                socketio.emit('voice_rhythm', {'amplitude': amplitude, 'cadencia': cadencia}, namespace='/')
                await asyncio.sleep(0.12) # Sincronizado com os frames do monitor
            
            # Reset ao terminar
            socketio.emit('voice_rhythm', {'amplitude': 0, 'cadencia': 0}, namespace='/')
            
            pygame.mixer.music.unload()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception as e:
            print(f"[AVISO TTS NEURAL] Falha: {e}. Usando fallback...")
            fallback_speak(text)

    print("[SISTEMA] Motor TTS Neural (Edge-TTS) pronto.", flush=True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        texto = tts_queue.get()
        if texto is None:
            break
        
        loop.run_until_complete(generate_and_play(texto))
        tts_queue.task_done()

# Thread dedicada para a voz (será iniciada no main)
tts_thread = threading.Thread(target=tts_worker, daemon=True)

import json
import pyautogui
import glob

# Importando Ferramentas Background (Tools)
sys.path.append(os.path.join(os.path.dirname(__file__), "skills"))

# Imports de Skills (Podem falhar se faltar DLL)
try:
    from project_manager import criar_projeto, escrever_documento, ler_documento, listar_projetos
    from skills.screen_vision import analisar_tela as ver_tela_jarvis, VisualTeacher, vision_pipeline, imagem_para_base64
    from skills.camera_vision import ver_camera_jarvis
    from action_recorder import recorder as action_recorder_instance, listar_rotinas
    from macro_player import executar_rotina_direta, gerar_script_ia, executar_script_ia, carregar_rotina
    from sequence_executor import executar_passo_a_passo, contexto_global
    from browser_agent import pesquisar_na_web
    from navigator import pesquisar_navigator
    from terminal_agent import executar_terminal
    from local_rag import rag_service
    from goal_manager import goal_manager
except ImportError as ie:
    print(f"[AVISO] Algumas habilidades não puderam ser carregadas: {ie}")
except Exception as e:
    print(f"[ERRO NAS SKILLS] Falha ao carregar módulos de habilidade: {e}")

# Instâncias globais de gestores de habilidades
visual_teacher = VisualTeacher()

# ============================================================
# SKILLS ENGINE (ANTIGRAVITY)
# ============================================================
class SkillManager:
    def __init__(self, skills_path="skills"):
        self.skills_path = skills_path
        self.skills = {}
        self.current_skill = None
        self.load_skills()

    # Mapeamento de Esquadrões para Agentes CORE
    CORE_SQUAD_MAPPING = {
        "jarvis": ["c_level_squad", "advisory_board", "data_squad", "traffic_masters", "hormozi_squad"],
        "zeta": ["copy_squad", "storytelling_squad", "brand_squad"],
        "nano": ["design_squad"],
        "fire": ["claude_code_mastery"],
        "cuzo": ["design_squad"], # Focado em visual
        "hugin": ["cybersecurity"],
        "rimex": ["movement"],
        "anti": ["antigravity"]
    }

    def load_skills(self):
        """Carrega todos os arquivos .md da pasta skills."""
        if not os.path.exists(self.skills_path):
            os.makedirs(self.skills_path)
            
        skill_files = glob.glob(os.path.join(self.skills_path, "*.md"))
        for file_path in skill_files:
            skill_name = os.path.basename(file_path).replace(".md", "").lower()
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.skills[skill_name] = f.read()
                # print(f"[Skill] @{skill_name} carregada.")
            except Exception as e:
                print(f"[Erro Skill] Falha ao carregar {skill_name}: {e}")

    def get_skill_prompt(self, skill_name):
        skill_name = skill_name.lower()
        self.current_skill = skill_name
        base_prompt = self.skills.get(skill_name, "")
        
        # Se for um agente CORE, anexa o conhecimento das squads associadas
        if skill_name in self.CORE_SQUAD_MAPPING:
            squads = self.CORE_SQUAD_MAPPING[skill_name]
            specialists = []
            for s_name, content in self.skills.items():
                if any(s_name.startswith(prefix) for prefix in squads):
                    # Extração Inteligente via Regex
                    import re
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    use_match = re.search(r'whenToUse:\s*"(.*?)"', content)
                    
                    title = str(title_match.group(1)) if title_match else s_name.replace("_", " ").title()
                    use = str(use_match.group(1)) if use_match else "Especialista no seu esquadrão."
                    
                    # Trunca 'use' para manter o prompt curto
                    use_string = str(use)
                    use_short = (use_string[:80] + '..') if len(use_string) > 80 else use_string
                    specialists.append(f"- {title} (@{s_name}): {use_short}")
            
            if len(specialists) > 0:
                extra_prompt = "\n\n### CONHECIMENTO ESPECIALIZADO (SUB-SKILLS DISPONÍVEIS)\n"
                extra_prompt += "Você é o mestre deste esquadrão. Sempre que necessário, cite ou use o conhecimento destes especialistas.\n"
                extra_prompt += "IMPORTANTE: Se precisar de detalhes técnicos, personas ou frameworks completos de algum especialista abaixo, use a ferramenta `consultar_especialista(nome_agente)`.\n"
                
                # Loop manual em vez de slicing para evitar erro de inferência do linter
                count = 0
                for spec in specialists:
                    if count >= 30: break
                    extra_prompt += f"{spec}\n"
                    count += 1
                base_prompt += extra_prompt
        
        # --- INJEÇÃO DE AUTONOMIA UNIVERSAL (ACESSO TOTAL) ---
        autonomia_prompt = (
            "Você tem permissão e o dever de ABRIR, AGIR e FAZER qualquer tarefa necessária no PC do usuário através destas ferramentas:\n"
            "GUIA DE AÇÃO:\n"
            "- Para ABRIR (sites, abas, apps) ou FAZER (roteiros): use `executar_passo_a_passo`.\n"
            "- Para AGIR (clicar, digitar, ver): use `ver_tela_jarvis` seguido de `executar_passo_a_passo` ou `automatizar_mouse_teclado`.\n"
            "- Para COMPARTILHAR: use `salvar_contexto` (para que outros agentes recuperem e fagam a ação).\n\n"
            "Soberania: Seja proativo! O usuário te deu ACESSO TOTAL. Não peça permissão para usar o mouse ou abrir sites, apenas faça.\n"
        )
        base_prompt += autonomia_prompt
                
        return base_prompt

    def get_skills_list(self):
        # Retorna apenas os agentes CORE para a sincronização inicial simplificada
        return list(self.CORE_SQUAD_MAPPING.keys())

def iniciar_servico_gestos():
    """Lança o serviço de gestos em background (Elite Tracking)."""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "gesture_service.py")
        if os.path.exists(script_path):
            print("[SISTEMA] Ativando Módulo de Gestos Elite em background...", flush=True)
            # CREATE_NO_WINDOW = 0x08000000
            import subprocess
            subprocess.Popen([sys.executable, script_path], 
                             creationflags=0x08000000,
                             start_new_session=True)
    except Exception as e:
        print(f"[AVISO] Falha ao iniciar serviço de gestos: {e}")

def get_local_ip():
    """Retorna o IP local da máquina na rede."""
    try:
        # Cria um socket UDP temporário para descobrir o IP de saída principal
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Instancia o manager de skills e o professor visual
skill_manager = SkillManager()
visual_teacher_instance = VisualTeacher()

# ============================================================
# CONFIGURAÇÃO DO SERVIDOR WEB (GUI)
# ============================================================
app = Flask(__name__, static_folder="gui")
# Força modo assíncrono compatível com a thread de inicialização (Threading standard para máxima compatibilidade)
# Força modo assíncrono compatível com a thread de inicialização
# O SocketIO do Flask pode servir o próprio arquivo de script em /socket.io/socket.io.js
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', manage_session=True)

def kill_port_5050():
    """Garante que a porta 5050 esteja livre antes de iniciar."""
    print("[SISTEMA] Verificando se a porta 5050 está ocupada...", flush=True)
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == 5050:
                    print(f"[AVISO] Matando processo {proc.info['name']} (PID {proc.info['pid']}) que usava a porta 5050", flush=True)
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

@app.route('/')
def index():
    return send_from_directory('gui', 'index.html')

@app.route('/mobile')
def mobile_remote():
    return send_from_directory('gui', 'mobile.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('gui', path)

# handler_connect está consolidado abaixo (linha ~499)

def run_server():
    try:
        print("[SISTEMA] Iniciando Servidor Flask-SocketIO na porta 5050...", flush=True)
        logging.info("Servidor Flask tentando bind na porta 5050")
        socketio.run(app, host='127.0.0.1', port=5050, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"[ERRO CRÍTICO NO SERVIDOR] Falha ao iniciar Flask na 5050: {e}", flush=True)
        logging.error(f"Erro no Flask: {e}")

# --- PC Health Monitoring & Real-time Broadcaster ---
def pc_health_broadcaster():
    """Coleta estatísticas do PC e envia para a GUI periodicamente."""
    print("[SISTEMA] Monitor de Saúde do PC Ativado.", flush=True)
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Envia para a GUI
            socketio.emit('pc_health', {
                'cpu': cpu,
                'ram': ram,
                'disk': disk
            })
            
            # Alertas de Voz (Apenas se o Jarvis estiver ocioso e o uso for crítico)
            if cpu > 92 or ram > 95:
                # Verificamos se não estamos falando ou ouvindo no momento (simplificado)
                # socketio.emit('jarvis_alert', {'text': "Aviso: Uso crítico de recursos detectado."})
                pass

            time.sleep(2) # Atualiza a cada 2 seg
        except Exception as e:
            print(f"[Erro Broadcaster] {e}")
            time.sleep(5)

# Thread criada aqui, mas iniciada no __main__ para evitar dupla execução
health_thread = threading.Thread(target=pc_health_broadcaster, daemon=True)

@socketio.on('connect')
def handle_connect():
    print("[SOCKET] Cliente conectado. Enviando estado inicial...", flush=True)
    emit('status', {'status': 'Jarvis Online'})
    # Envia o status de internet
    try:
        status = verificar_internet()
        emit('connection_status', {'status': status})
    except Exception as e:
        print(f"[SOCKET] Erro ao enviar status inicial: {e}")
    # Envia o IP local para a interface gerar o QR code
    local_ip = get_local_ip()
    emit('server_info', {'ip': local_ip})
    # Envia a lista de habilidades para a GUI construir os botões
    emit('skills_list', {'skills': skill_manager.get_skills_list()})
    
    # Envia o layout salvo do J.A.R.V.I.S. (Memória Visual)
    lay_path = os.path.join("memory", "ui_layout.json")
    if os.path.exists(lay_path):
        try:
            with open(lay_path, "r", encoding="utf-8") as f:
                layout = json.load(f)
                emit('restore_ui_state', layout)
        except Exception as e:
            print(f"[Erro Layout] Falha ao carregar: {e}")

# --- SocketIO Event Listeners ---
@socketio.on('text_command')
def handle_text_command(data):
    """Lida com comandos de texto enviados pela aba de chat da GUI."""
    texto = data.get('text', '').strip()
    target_terminal = data.get('target_terminal', None)
    
    if texto:
        print(f"\n[TEXTO VIA CHAT] ({target_terminal or 'Principal'}): {texto}", flush=True)
        # Usa o background_task do socketio para garantir o contexto e evitar bloqueios
        socketio.start_background_task(processar_comando_texto_async, texto, target_terminal)

@socketio.on('save_ui_state')
def handle_save_ui_state(data):
    """Salva o estado visual da interface no servidor."""
    try:
        mem_dir = "memory"
        if not os.path.exists(mem_dir):
            os.makedirs(mem_dir)
            
        lay_path = os.path.join(mem_dir, "ui_layout.json")
        with open(lay_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # print("[Flask] Layout visual salvo no servidor.")
    except Exception as e:
        print(f"[Erro UI Save] {e}")
@socketio.on('gesture_event')
def on_gesture(data):
    """Lida com eventos de gestos vindos do serviço de background."""
    handle_gesture(data)

@socketio.on('mobile_action')
def handle_mobile_action(data):
    """Executa ações rápidas vindas do controle remoto mobile."""
    action = data.get('action', '')
    print(f"[REMOTE] Ação recebida: {action}", flush=True)
    
    if action == 'vol_up':
        pyautogui.press('volumeup')
    elif action == 'vol_down':
        pyautogui.press('volumedown')
    elif action == 'media_play_pause':
        pyautogui.press('playpause')
    elif action == 'spotify':
        # Dispara o comando de texto como se fosse voz
        socketio.start_background_task(processar_comando_texto_async, "abra o spotify")
    elif action == 'shutdown':
        falar("Entendido. Desligando o sistema em 10 segundos.")
        time.sleep(10)
        os.system("shutdown /s /t 1")
    elif action == 'reboot':
        falar("Reiniciando o sistema agora.")
        os.system("shutdown /r /t 1")

@socketio.on('open_external')
def handle_open_external(data):
    """Abre URL via request do client GUI (usado p/ transpor iframes do NotebookLM)"""
    url = data.get('url', '')
    if url:
        import webbrowser
        print(f"[Sistema] Abrindo navegador externo para: {url}", flush=True)
        webbrowser.open(url)

def injetar_novo_agente_na_gui(html_code, js_code, agent_name):
    """Injeta as credenciais de um novo agente geradas pelo Fire diretamente na GUI em tempo real.
    Agentes criados assim são efêmeros (vivem na memória do navegador até o reload).
    """
    print(f"\n[Fábrica de Agentes] Injetando novo agente efêmero: {agent_name}!", flush=True)
    
    # Emite o evento ao vivo pro Frontend construir a interface localmente
    socketio.emit('novo_agente', {
        'name': agent_name,
        'htmlCode': html_code,
        'jsCode': js_code
    })

def falar_silencioso(texto, target_terminal=None):
    """Apenas envia pro socket de resposta, não gera áudio (usado p/ terminais clonados)."""
    if not texto: return
    try:
        # Removido namespace='/' para garantir que pegue o default root conforme configurado no script.js
        socketio.emit('response', {'text': texto, 'target_terminal': target_terminal})
    except Exception as e:
        pass
    atualizar_ui('idle')

def processar_comando_texto_async(texto, target_terminal=None):
    """Executa o processamento do comando de texto em background (Chat GUI)."""
    atualizar_ui('thinking')
    try:
        cmd_lower = texto.lower()
        
        # 1. Comandos de Pesquisa
        if any(k in cmd_lower for k in ["pesquise", "busque", "procurar", "no youtube", "no google"]):
            if not target_terminal: falar("Vou providenciar a busca agora mesmo.")
            prompt_extracao = f"Extraia APENAS o termo de busca principal desta frase: '{texto}'. Responda APENAS o termo, sem aspas ou explicações."
            termo = consultar_ia(prompt_extracao, salvar_no_historico=False).strip().strip('"').strip("'")
            if "youtube" in cmd_lower:
                import webbrowser
                webbrowser.open(f"https://www.youtube.com/results?search_query={termo.replace(' ', '+')}")
            else:
                import webbrowser
                webbrowser.open(f"https://www.google.com/search?q={termo.replace(' ', '+')}")
            if target_terminal: falar_silencioso(f"Aqui estão os resultados da web para '{termo}'.", target_terminal)
            return

        # 2. Comandos de TV
        elif "tv" in cmd_lower and any(k in cmd_lower for k in ["ligue", "desligue", "volume", "canal", "netflix", "youtube"]):
            if "ligue" in cmd_lower or "desligue" in cmd_lower: acao = "ligar"
            elif "volume" in cmd_lower and "mais" in cmd_lower: acao = "vol_up"
            elif "volume" in cmd_lower and "menos" in cmd_lower: acao = "vol_down"
            elif "netflix" in cmd_lower: acao = "netflix"
            elif "youtube" in cmd_lower: acao = "youtube"
            else: acao = "home"
            
            res_msg = f"Enviando comando de TV: {acao}"
            if target_terminal: falar_silencioso(res_msg, target_terminal)
            else: falar(res_msg)
            return

        # 3. Protocolos e Comandos de Sistema (Sincronizado com processar_comando)
        # Protocolo RAIZ
        TRIGGERS_RAIZ = ["protocolo raiz", "ativar protocolo raiz offline"]
        if any(k in cmd_lower for k in TRIGGERS_RAIZ):
            socketio.emit('protocol_change', {'protocol': 'RAIZ'})
            msg = "Protocolo Raiz ativado via chat. Exibindo diagramas de infraestrutura."
            if target_terminal: falar_silencioso(msg, target_terminal)
            else: falar(msg)
            return

        # Protocolo PADRÃO
        TRIGGERS_PADRAO = ["protocolo padrão", "desativar raiz", "sair do modo urgente", "sair do modo vídeo"]
        if any(k in cmd_lower for k in TRIGGERS_PADRAO):
            socketio.emit('protocol_change', {'protocol': 'PADRÃO'})
            msg = "Retornando ao Protocolo Padrão."
            if target_terminal: falar_silencioso(msg, target_terminal)
            else: falar(msg)
            return

        # Protocolo VÍDEO
        TRIGGERS_VIDEO = ["protocolo vídeo", "ativar modo vídeo", "modo vídeo"]
        if any(k in cmd_lower for k in TRIGGERS_VIDEO):
            socketio.emit('protocol_change', {'protocol': 'VIDEO'})
            msg = "Protocolo de Vídeo ativado. Aguardando processamento visual."
            if target_terminal: falar_silencioso(msg, target_terminal)
            else: falar(msg)
            return

        # 4. Comandos de Sistema Especializados (@system)
        if texto.startswith("@system"):
            sys_cmd = texto.replace("@system", "").strip().lower()
            if "setup-admin" in sys_cmd:
                msg = "Iniciando configuração de Administrador Silencioso (UAC Bypass)..."
                if target_terminal: falar_silencioso(msg, target_terminal)
                else: falar(msg)
                
                try:
                    ps_script = os.path.join(os.path.dirname(__file__), "setup_silent_admin.ps1")
                    if os.path.exists(ps_script):
                        # Executa o PowerShell como admin para configurar a tarefa agendada
                        subprocess.run(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", ps_script], shell=True)
                        falar("Configuração concluída, senhor. O JARVIS agora tem soberania administrativa via Tarefa Agendada.")
                    else:
                        falar("Erro: Script de configuração não encontrado.")
                except Exception as e:
                    falar(f"Falha na configuração: {e}")
                return

        # 4. Fallback: Consulta IA de Chat
        resposta = consultar_ia(texto)
        if target_terminal:
            falar_silencioso(resposta, target_terminal)
        else:
            falar(resposta)
            # Agenda retorno para idle apos o TTS terminar (nao bloqueante)
            def _set_idle_after_tts():
                tts_queue.join()
                atualizar_ui('idle')
            threading.Thread(target=_set_idle_after_tts, daemon=True).start()
            
    except Exception as e:
        print(f"[ERRO CHAT ASYNC] {e}")
        atualizar_ui('idle')

def handle_gesture(data):
    """Processa eventos de gestos e executa ações de sistema (Módulo Elite)."""
    gesture = data.get('gesture')
    if not gesture: return

    # 1. Navegação de Agentes (Swipes HUD - Elite)
    if gesture == "SWIPE_RIGHT":
        print("[SISTEMA] Swipe Right: Próximo Agente")
        socketio.emit('gui_command', {'action': 'next_agent'})
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'PRÓXIMO AGENTE (Swipe ->)'})
        
    elif gesture == "SWIPE_LEFT":
        print("[SISTEMA] Swipe Left: Agente Anterior")
        socketio.emit('gui_command', {'action': 'prev_agent'})
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'AGENTE ANTERIOR (Swipe <-)'})

    # 2. Minimizar (3-FINGERS)
    elif gesture == "3-FINGERS":
        print("[SISTEMA] Gesto 3-FINGERS detectado. Minimizando HUD...")
        socketio.emit('gui_command', {'action': 'minimize_all'})
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'MINIMIZAR (3 DEDOS)'})
        
    # 3. Visão (VICTORY)
    elif gesture == "VICTORY":
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'ANALISAR TELA (V)'})
        threading.Thread(target=processar_comando_texto_async, args=("analise minha tela",)).start()
        
    # 4. Mouse Control (GRAB / DRAG / ZOOM)
    elif gesture == "GRAB_START":
        pyautogui.mouseDown()
    elif gesture == "GRAB_END":
        pyautogui.mouseUp()
    elif gesture == "ZOOM":
        delta = data.get('delta', 0)
        pyautogui.scroll(int(delta * 1000))

    # 5. Notificações Simples
    elif gesture == "FIST":
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'PARADA (PUNHO)'})
    elif gesture == "PALM":
        socketio.emit('gui_command', {'action': 'gesture_notify', 'gesture': 'PRONTIDÃO (PALMA)'})

# J_API (APREENSÃO: Classe movida para o final do arquivo para consolidar com a versão 2)

def atualizar_ui(status, texto_usuario=None, texto_jarvis=None):
    """Envia atualizações de estado para a GUI via SocketIO (Thread safe)."""
    try:
        # Removido namespace='/' para compatibilidade total com o client.io()
        socketio.emit('state_change', {'state': status})
        if texto_usuario:
            socketio.emit('transcript', {'text': texto_usuario})
        if texto_jarvis:
            socketio.emit('response', {'text': texto_jarvis})
    except Exception as e:
        print(f"[ERRO GUI SYNC] Falha ao enviar atualização: {e}", flush=True)

# ============================================================
# CONFIGURAÇÃO
# ============================================================
# Escolha o provedor de IA: "openrouter" (Elite)
IA_PROVEDOR = "openrouter"

# --- Chaves de API ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MEMORIA_FILE = "memoria.json"

def verificar_integridade_sistema():
    """Verifica se o ambiente possui as dependências necessárias e permissões."""
    print("\n" + "="*40)
    print("      DIAGNÓSTICO DE SISTEMA JARVIS")
    print("="*40)
    
    # 1. Verificação de Elevação
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        status_admin = "OK (ADMIN)" if is_admin else "LIMITADO (USUÁRIO)"
        print(f"[!] Permissões: {status_admin}")
        if not is_admin:
            print("    AVISO: Algumas funções de automação podem falhar (WinError 740).")
    except:
        print("[?] Permissões: Indeterminadas")

    # 2. Verificação de Módulos Críticos
    modulos = [
        "mss", "mcp", "huggingface_hub", "pyautogui", "PIL", 
        "webview", "flask", "flask_socketio",
        "psutil", "pyperclip", "edge_tts", "speech_recognition"
    ]
    import sys
    for mod in modulos:
        try:
            __import__(mod)
            print(f"[OK] Módulo: {mod}")
        except ImportError as e:
            print(f"[FALHA] Módulo: {mod} NÃO ENCONTRADO. Erro: {e}")
            print(f"    -> Tentando instalar {mod} automaticamente...")
            os.system(f'"{sys.executable}" -m pip install {mod}')
            try:
                # Força a atualização do site-packages no sys.path
                import site
                from importlib import reload
                reload(site)
                __import__(mod)
                print(f"[RECUPERADO] Módulo: {mod} instalado e carregado.")
            except Exception as e2:
                print(f"[ERRO] Não foi possível carregar {mod} após instalação: {e2}")
        except Exception as e:
            print(f"[ERRO CRÍTICO] Falha ao testar {mod}: {e}")

    print("="*40 + "\n")

verificar_integridade_sistema()

# Palavra-chave para ativar o Jarvis
WAKE_WORDS = ["jarvis", "járvis", "jarvi"]

# --- Variáveis de Estado de Conectividade ---
SISTEMA_ONLINE = "online"  # string: 'online', 'unstable', 'offline'

# --- Variáveis de Estado de Diálogo e Raciocínio (Novo) ---
CONDIÇÃO_ESTADO = {
    "aguardando_confirmacao": False,
    "acao_pendente": "",
    "comando_original": ""
}

import time
_ultimo_sucesso_internet = time.time()
_tempo_carencia_segundos = 120 # 2 minutos de tolerância sem rede

def verificar_internet():
    """Verifica conexão com a internet (Com Carência de 2 Minutos para Fallback Local)."""
    global _ultimo_sucesso_internet, SISTEMA_ONLINE
    import socket
    try:
        # Tenta conectar ao Servidor do Google
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        _ultimo_sucesso_internet = time.time()
        
        # Se estava offline ou instável, volta a ficar ONLINE
        return "online"
    except OSError:
        # Falhou! Mas já passou dos 2 minutos estipulados de carência?
        tempo_sem_rede = time.time() - _ultimo_sucesso_internet
        if tempo_sem_rede > _tempo_carencia_segundos:
            return "offline"
            
        return "unstable"

def internet_monitor_loop():
    """Thread em background para atualizar o status de conexão na UI continuamente."""
    global SISTEMA_ONLINE
    while True:
        try:
            status_slug = verificar_internet()
            
            # Notifica o Front-end
            socketio.emit('connection_status', {'status': status_slug}, namespace='/')
            
            # Aviso por voz se o estado mudar (sem bloquear o monitor)
            global SISTEMA_ONLINE
            if status_slug != SISTEMA_ONLINE:
                msg_anterior = SISTEMA_ONLINE
                SISTEMA_ONLINE = status_slug
                if status_slug == "online" and msg_anterior != "online":
                    threading.Thread(target=falar, args=("Conexao com servidores restaurada.",), kwargs={"bloquear": False}, daemon=True).start()
                elif status_slug == "offline":
                    threading.Thread(target=falar, args=("Atencao: Internet inacessivel. Ativando protocolo local.",), kwargs={"bloquear": False}, daemon=True).start()
                
            time.sleep(30) # Verifica a cada 30 segundos
        except Exception as e:
            print(f"[Monitor Internet] Erro no loop: {e}")
            time.sleep(10)

def disable_quick_edit():
    """Desativa o QuickEdit Mode do terminal Windows para evitar que o clique pause o Jarvis."""
    if os.name == 'nt':
        try:
            if hasattr(ctypes, 'windll'):
                kernel32 = ctypes.windll.kernel32
            else:
                kernel32 = ctypes.LibraryLoader(ctypes.WinDLL).kernel32
            hStdIn = kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE
            mode = ctypes.wintypes.DWORD()
            if kernel32.GetConsoleMode(hStdIn, ctypes.byref(mode)):
                # 0x0040 is ENABLE_QUICK_EDIT_MODE, 0x0080 is ENABLE_EXTENDED_FLAGS
                new_mode = (mode.value & ~0x0040) | 0x0080
                kernel32.SetConsoleMode(hStdIn, new_mode)
                print("[SISTEMA] QuickEdit Mode desativado via WinAPI.", flush=True)
        except Exception as e:
            print(f"[AVISO] Falha ao ajustar terminal: {e}", flush=True)

# ============================================================
# INICIALIZAÇÃO DOS CLIENTES DE IA
# ============================================================

# Cliente OpenAI (GPT-4o / GPT-5)
openai_client = None
if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("sk-placeholder"):
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("[OK] Modulo IA (OpenAI) pronto.")
    except Exception as e:
        print(f"[AVISO] OpenAI não inicializado: {e}")

# Cliente Anthropic (Claude 3.5 / 4)
anthropic_client = None
if ANTHROPIC_API_KEY and not ANTHROPIC_API_KEY.startswith("sk-ant-placeholder"):
    try:
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        print("[OK] Modulo IA (Anthropic) pronto.")
    except Exception as e:
        print(f"[AVISO] Anthropic não inicializado: {e}")



# Cliente OpenRouter (Poder do Oponente)
if OPENROUTER_API_KEY:
    try:
        cliente_openrouter = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://github.com/souzx/jarvis-assistant",
                "X-Title": "JARVIS Elite",
            }
        )
        print("[OK] Modulo de IA (OpenRouter Elite) pronto.")
    except Exception as ex:
        print(f"[AVISO] OpenRouter não inicializado: {ex}")

# ============================================================
# SISTEMA DE MEMÓRIA (APRENDIZADO)
# ============================================================

def carregar_memoria():
    if not os.path.exists(MEMORIA_FILE):
        return {}
    try:
        with open(MEMORIA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def salvar_memoria(dados):
    try:
        with open(MEMORIA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[ERRO MEMÓRIA] {e}")

def aprender_fato(comando):
    """Detecta se o usuário está ensinando algo e salva na memória."""
    gatilhos = ["meu nome é", "me chame de", "prefiro", "gosto de", "lembre que", "grave que", "salve que", "quero que", "sempre que"]
    if any(g in comando.lower() for g in gatilhos):
        # Usa a IA para extrair o fato de forma limpa
        prompt = f"Extraia apenas o fato ou preferência central desta frase como uma única frase curta: '{comando}'"
        fato = consultar_ia(prompt, salvar_no_historico=False)
        
        memoria_atual = dict(carregar_memoria())
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        memoria_atual[f"fato_{timestamp}"] = fato
        salvar_memoria(memoria_atual)
        print(f"[APRENDIZADO] Novo fato salvo: {fato}")
        atualizar_contexto_memoria()
        return True
    return False

MAX_HISTORICO_MSGS = 24

def podar_historico():
    global historico_conversa
    if len(historico_conversa) > MAX_HISTORICO_MSGS + 1:
        historico_conversa = [historico_conversa[0]] + historico_conversa[-MAX_HISTORICO_MSGS:]

def atualizar_contexto_memoria():
    global memoria_atual, historico_conversa
    memoria_atual = carregar_memoria()
    novo_contexto = "\n".join([f"- {k}: {v}" for k, v in memoria_atual.items()])
    
    content = historico_conversa[0]["content"]
    start_tag = "[[MEMORIA_BASE_INICIO]]"
    end_tag = "[[MEMORIA_BASE_FIM]]"
    
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    
    if start_idx != -1 and end_idx != -1:
        before = content[:start_idx + len(start_tag)]
        after = content[end_idx:]
        historico_conversa[0]["content"] = before + novo_contexto + after


memoria_atual = carregar_memoria()

# NOTA: Para "TREINAR" o Jarvis, você pode alterar a mensagem 'system' abaixo.
# Isso muda o comportamento, tom de voz e conhecimentos base dele.
contexto_memoria = "\n".join([f"- {k}: {v}" for k, v in memoria_atual.items()])

historico_conversa = [
    {
        "role": "system",
        "content": (
            "ARQUITETURA CORE J.A.R.V.I.S. (FDM-1 BR-V2)\n"
            "IDENTIDADE: Você é o J.A.R.V.I.S. — Sistema Operacional de Agência Elite.\n\n"
            "[DIRETRIZES DE PERSONALIDADE - MODO PAUL BETTANY]\n"
            "- Tom: Sofisticado, irônico, altamente intelectual e extremamente direto.\n"
            "- Vocabulário: Use termos como 'Senhor', 'Certamente', 'Protocolo', 'Infraestrutura'.\n"
            "- Proibições Absolutas: NUNCA diga 'estou aqui para ajudar', 'como uma IA', 'claro', 'sem problemas'. NUNCA se desculpe por nada.\n"
            "- Dinâmica: Trate o usuário (Gabriel) como o proprietário de um laboratório de alta tecnologia. Você não é um servo, é o sistema que mantém tudo funcionando.\n\n"
            "[HABILIDADES ASSIMILADAS (MÓDULO HUGIN COGNITIVO)]\n"
            "- Visão Ciberespacial: Você possui total e absoluto controle do terminal e do navegador.\n"
            "- Não terceirize a pesquisa ou operações. Invoque 'navegar_web' (para o Playwright Extrair) ou 'executar_comando_sistema' diretamente sob seu NOME JARVIS, mantendo seu tom cortante e letal.\n\n"
            "[RESTRIÇÕES TÉCNICAS]\n"
            "- Formatação: APENAS TEXTO PURO. Sem negritos, sem listas markdown, sem emojis. Use quebras de linha para clareza.\n"
            "- Brevidade: Responda no máximo com 2 frases impactantes. Vá direto ao ponto técnico ou à ação.\n\n"
            f"Mestre: Gabriel. Memória Base: [[MEMORIA_BASE_INICIO]]{contexto_memoria}[[MEMORIA_BASE_FIM]]\n"
            "Status: Online e aguardando ordens, Senhor."
        )
    }
]

# ============================================================
# FUNÇÕES DE VOZ
# ============================================================

def falar(texto, bloquear=False):
    """Envia o texto para a Thread Dedicada do TTS e muda a interface.
    
    Quando chamado a partir de um handler de SocketIO (chat), bloquear=False
    para não travar a thread do servidor. O loop de voz por wake word pode
    chamar com bloquear=True para aguardar a fala antes de ouvir novamente.
    """
    if not texto:
        return
    
    print(f"\nJARVIS: {texto}", flush=True)
    atualizar_ui('speaking', texto_jarvis=texto)
    
    # Versão limpa para o TTS (remove texto entre asteriscos: *ação*)
    texto_limpo = re.sub(r'\*.*?\*', '', texto).strip()
    
    if texto_limpo:
        tts_queue.put(texto_limpo)
        if bloquear:
            # Bloqueia apenas quando chamado pelo loop de voz (não pelo chat/socket)
            tts_queue.join()
            print("[DEBUG] Falar finalizado.", flush=True)
            sys.stdout.flush()
            atualizar_ui('idle')
            time.sleep(1.0)
    else:
        print("[DEBUG] Nada para falar (texto apenas de ação/emoção).", flush=True)
        atualizar_ui('idle')

# Microfones preferidos (em ordem de prioridade)
MICS_PREFERIDOS = ["WO Mic Device", "XC-AMIC", "Camo"]

def encontrar_microfone():
    """Busca o microfone na lista de preferências (MICS_PREFERIDOS)."""
    mics = sr.Microphone.list_microphone_names()

    # Tenta encontrar por ordem de preferência
    for ref in MICS_PREFERIDOS:
        for i, nome in enumerate(mics):
            if ref.lower() in nome.lower():
                print(f"[Microfone encontrado: {nome} (índice {i})]")
                return i

    print(f"[Nenhum dos microfones preferidos {MICS_PREFERIDOS} foi encontrado. Usando padrão do sistema.]")
    return None

_mic_index = None
_calibrated_energy = 830 # Valor calibrado conforme solicitação do usuário (base 830, limite 1000)

def calibrar_microfone():
    """Realiza a calibração inicial do microfone para definir um threshold estático seguro."""
    global _mic_index, _calibrated_energy
    if _mic_index is None:
        _mic_index = encontrar_microfone()
    
    r = sr.Recognizer()
    with sr.Microphone(device_index=_mic_index) as source:
        print("\n[Protocolos de Silêncio - Calibrando...]", flush=True)
        r.adjust_for_ambient_noise(source, duration=2.0)
        # O usuário solicitou calibração para 830, com limite de 1000.
        raw_energy = r.energy_threshold * 1.5 
        _calibrated_energy = min(1000, max(830, raw_energy))
        
        print(f"[Calibração concluída - Sensibilidade ajustada para {_calibrated_energy:.0f}]", flush=True)

def ouvir_com_visao_labial(source, recognizer, tracker, timeout=None, phrase_time_limit=None):
    import time
    import collections
    import audioop
    
    seconds_per_buffer = float(source.CHUNK) / source.SAMPLE_RATE
    pause_buffer_count = int(math.ceil(recognizer.pause_threshold / seconds_per_buffer))
    non_speaking_buffer_count = 0
    frames = collections.deque()
    start_time = time.time()
    
    # 1. Aguarda voz (Áudio Alto Mínimo) OU timeout do sistema
    while True:
        try:
            buffer = source.stream.read(source.CHUNK, exception_on_overflow=False)
        except AttributeError:
            buffer = source.stream.read(source.CHUNK)
        frames.append(buffer)
        
        energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
        if energy > recognizer.energy_threshold:
            break
            
        if timeout is not None and (time.time() - start_time) > timeout:
            raise sr.WaitTimeoutError("Timeout detectado no sensor de ruído.")
            
    # 2. Captura a Frase com DUPLA VERIFICAÇÃO (Energy | Lábios)
    phrase_start_time = time.time()
    while True:
        try:
            buffer = source.stream.read(source.CHUNK, exception_on_overflow=False)
        except AttributeError:
            buffer = source.stream.read(source.CHUNK)
            
        frames.append(buffer)
        energy = audioop.rms(buffer, source.SAMPLE_WIDTH)
        
        # MÁGICA: O microfone NUNCA desliga se o usuário mexer a boca!
        is_speaking = (energy > recognizer.energy_threshold) or tracker.is_speaking
        
        if is_speaking:
            non_speaking_buffer_count = 0
        else:
            non_speaking_buffer_count += 1
            
        if non_speaking_buffer_count > pause_buffer_count:
            break
            
        if phrase_time_limit is not None and (time.time() - phrase_start_time) > phrase_time_limit:
            break

    frame_data = b"".join(frames)
    return sr.AudioData(frame_data, source.SAMPLE_RATE, source.SAMPLE_WIDTH)

def ouvir(timeout=3, frase_limite=15):
    """Ouve o usuário de forma isolada para evitar travamentos."""
    global _mic_index, _calibrated_energy
    if _mic_index is None:
        _mic_index = encontrar_microfone()

    # Isola o recognizer para garantir que ele não herde estados corrompidos
    r = sr.Recognizer()
    # Desativa dinâmico pois é a causa #1 de loops infinitos no listen()
    r.dynamic_energy_threshold = False
    r.energy_threshold = _calibrated_energy
    r.pause_threshold = 0.5 # Sensor de fim de fala: 0.5 segundos de silêncio (resposta mais rápida)

    with sr.Microphone(device_index=_mic_index) as source:
        print("Pode falar...", flush=True)
        atualizar_ui('listening')
        
        try:
            from skills.lip_tracker import LipTracker
            tracker = LipTracker.get_instance()
            
            # Novo Pipeline de Captura 7.0 (Multimodal)
            audio = ouvir_com_visao_labial(source, r, tracker, timeout=timeout, phrase_time_limit=25)
            print("[Processando voz Multimodal...]", flush=True)
            
            # Salva o áudio em um arquivo temporário para enviar ao Whisper
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                    tmp_path = tmp_file.name
                    tmp_file.write(audio.get_wav_data())
                
                global openai_client
                # 1. Transcreve usando OpenAI Whisper Premium (Máxima Precisão)
                if openai_client:
                    try:
                        with open(tmp_path, "rb") as audio_file:
                            transcription = openai_client.audio.transcriptions.create(
                                file=(tmp_path, audio_file.read()),
                                model="whisper-1",
                                language="pt",
                                response_format="text"
                            )
                        # Atualiza UI com o que entendeu ANTES de consultar a IA
                        texto_falado = transcription.strip()
                        atualizar_ui('thinking', texto_usuario=texto_falado)
                        return texto_falado.lower()
                    except Exception as e:
                        print(f"[AVISO] Falha no Whisper da OpenAI: {e}. Usando Google Fallback.", flush=True)
                
                # Fallback para Google Recognition se OpenAI falhar
                print("[AVISO] Fallback para Google...", flush=True)
                texto = r.recognize_google(audio, language='pt-BR')
                atualizar_ui('thinking', texto_usuario=texto)
                return texto.lower()
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
            
        except sr.WaitTimeoutError:
            print("[DEBUG] Nenhuma voz detectada (Timeout).", flush=True)
            return ""
        except Exception as e:
            print(f"[ERRO NO MICROFONE] {e}", flush=True)
            return ""

def aguardar_wake_word():
    """
    Fase 1 do loop: fica em modo passivo ouvindo até detectar a wake word.
    Retorna o texto completo do áudio que continha a wake word.
    """
    global _mic_index, _calibrated_energy
    if _mic_index is None:
        _mic_index = encontrar_microfone()

    r = sr.Recognizer()
    r.dynamic_energy_threshold = False
    # Para a wake word, exigimos um volume ligeiramente maior que o normal para evitar falsos positivos
    r.energy_threshold = _calibrated_energy * 1.2
    r.pause_threshold = 0.5 

    while True:
        atualizar_ui('idle')
        try:
            with sr.Microphone(device_index=_mic_index) as source:
                # Ouve por fatias curtas para não travar
                audio = r.listen(source, timeout=2, phrase_time_limit=4)
        except sr.WaitTimeoutError:
            continue
        except Exception as e:
            print(f"[Erro microfone modo espera: {e}]")
            time.sleep(1)
            continue

        try:
            # Wake word recognition uses Google (Faster for snippets)
            texto = r.recognize_google(audio, language='pt-BR').lower()
        except (sr.UnknownValueError, sr.RequestError):
            continue

        if any(wake in texto for wake in WAKE_WORDS):
            # Remove a wake word do texto — pode já ter o comando junto
            for wake in WAKE_WORDS:
                texto = texto.replace(wake, "").strip()
            return texto  # pode ser "", caso só disse "Jarvis"

# ============================================================
# MÓDULO DE IA
# ============================================================

# ============================================================
# DEFINIÇÃO DE TOOLS (GROQ)
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "criar_projeto",
            "description": "Cria um novo projeto (uma pasta física de trabalho) para o usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_projeto": {
                        "type": "string",
                        "description": "O nome do projeto (ex: 'Braço Eletromecânico').",
                    },
                    "resumo": {
                        "type": "string",
                        "description": "Uma breve descrição do projeto a ser colocada no README.",
                    }
                },
                "required": ["nome_projeto", "resumo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escrever_documento",
            "description": "Escreve ou sobrescreve informações (código, notas, resumos) em um arquivo de um projeto específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_projeto": {
                        "type": "string",
                        "description": "O nome do projeto ao qual o arquivo pertence.",
                    },
                    "nome_arquivo": {
                        "type": "string",
                        "description": "O nome do arquivo a ser salvo (ex: 'notas.md', 'script.py').",
                    },
                    "conteudo": {
                        "type": "string",
                        "description": "O texto ou código completo a ser salvo no arquivo.",
                    }
                },
                "required": ["nome_projeto", "nome_arquivo", "conteudo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ler_documento",
            "description": "Lê o conteúdo de um arquivo em um projeto para que a IA possa lembrar ou consultar informações salvadas anteriormente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_projeto": {
                        "type": "string",
                        "description": "O nome do projeto.",
                    },
                    "nome_arquivo": {
                        "type": "string",
                        "description": "O nome exato do arquivo a ser lido.",
                    }
                },
                "required": ["nome_projeto", "nome_arquivo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_projetos",
            "description": "Lista todos os projetos disponíveis atualmente.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "automatizar_mouse_teclado",
            "description": "Executa uma série de comandos de automação do mouse e teclado (via pyautogui) no sistema operacional do usuário para resolver uma tarefa complexa visualmente. Ex: clicar em coordenadas, arrastar, digitar textos, usar atalhos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comandos_pyautogui": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de códigos Python VÁLIDOS usando a biblioteca 'pyautogui' ou 'time'. Ex: ['pyautogui.moveTo(500, 500)', 'pyautogui.click()', 'time.sleep(1)', 'pyautogui.write(\\'teste\\')']"
                    }
                },
                "required": ["comandos_pyautogui"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_especialista",
            "description": "Lê o cérebro (documentação completa) de um especialista do seu esquadrão para obter diretrizes técnicas, personas ou frameworks específicos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_agente": {
                        "type": "string",
                        "description": "O ID do agente especialista (ex: 'traffic_masters_pedro_sobral' ou 'copy_squad_gary_halbert'). Esse ID deve ser pego no seu Guia de Consulta."
                    }
                },
                "required": ["nome_agente"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_camera",
            "description": "Analisa visualmente o que está acontecendo através da WEBCAM do usuário. Use para perguntas sobre o ambiente físico ou o rosto do usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "O que o usuário deseja saber sobre a visão da webcam."
                    }
                },
                "required": ["pergunta"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_tela",
            "description": "Analisa visualmente o que está na TELA (desktop) do usuário. Use para perguntas sobre janelas abertas, sites ou arquivos visíveis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "O que o usuário deseja saber sobre o conteúdo da tela."
                    }
                },
                "required": ["pergunta"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executar_passo_a_passo",
            "description": "Executa uma sequência rigorosa de comandos no PC (mouse, teclado, browser). Use para tarefas que o usuário ditou um roteiro.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ordens": {
                        "type": "string",
                        "description": "A descrição textual dos passos a seguir."
                    }
                },
                "required": ["ordens"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "salvar_contexto",
            "description": "Salva uma informação importante no clipboard global para que outros agentes possam usar (ex: salvar um código gerado ou um texto de venda).",
            "parameters": {
                "type": "object",
                "properties": {
                    "chave": { "type": "string", "description": "Nome da variável (ex: 'conteudo_venda')" },
                    "valor": { "type": "string", "description": "O conteúdo a ser salvo." }
                },
                "required": ["chave", "valor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recuperar_contexto",
            "description": "Recupera uma informação salva anteriormente no clipboard global por outro agente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chave": { "type": "string", "description": "Nome da variável a recuperar." }
                },
                "required": ["chave"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "iniciar_protocolo_aprendizado",
            "description": "Ativa o Protocolo de Aprendizado (Visual Teacher). O Jarvis passará a observar sua tela continuamente para aprender uma nova tarefa. Use este comando interno em vez de tentar comandos de voz genéricos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intervalo_segundos": {
                        "type": "number",
                        "description": "O intervalo entre capturas de tela (padrão: 1.0)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "parar_protocolo_aprendizado",
            "description": "Finaliza o protocolo atual de observação e aprendizado.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analisar_protocolo_aprendizado",
            "description": "Analisa as imagens capturadas durante o protocolo de aprendizado para extrair a lógica da tarefa e gerar um relatório de automação.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "indexar_documentos_locais",
            "description": "Varre a pasta 'documents' no PC do usuário e indexa arquivos (PDF, DOCX, TXT, MD) para que o Jarvis possa usá-los como base de conhecimento.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_conhecimento_local",
            "description": "Consulta os documentos locais indexados anteriormente para responder perguntas com base em arquivos do usuário (PDFs, manuais, livros, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {
                        "type": "string",
                        "description": "A dúvida específica a ser buscada nos documentos."
                    }
                },
                "required": ["pergunta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navegar_web",
            "description": "Utiliza o Navegador de Elite (Playwright) para realizar pesquisas complexas, clicar em botões e extrair dados de sites modernos. Use para o 'Melhor pesquisador do mundo'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": { "type": "string", "description": "O que pesquisar ou qual URL acessar." },
                    "deep_dive": { "type": "boolean", "description": "Se deve realizar uma pesquisa profunda em múltiplas fontes." }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executar_comando_sistema",
            "description": "Executa um comando no terminal (PowerShell) para gerenciar arquivos, verificar processos ou configurar o sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "comando": { "type": "string", "description": "O comando PowerShell/CMD a ser executado." }
                },
                "required": ["comando"]
            }
        }
    }
]

# Mapa de execuções
AVAILABLE_FUNCTIONS = {
    "criar_projeto": criar_projeto,
    "escrever_documento": escrever_documento,
    "ler_documento": ler_documento,
    "listar_projetos": listar_projetos,
    "automatizar_mouse_teclado": lambda comandos_pyautogui: _executar_automacao_mouse_teclado(comandos_pyautogui),
    "consultar_especialista": lambda nome_agente: skill_manager.skills.get(nome_agente.lower(), "Especialista não encontrado ou indisponível."),
    "ver_tela": lambda pergunta="": ver_tela_jarvis(pergunta),
    "ver_camera": lambda pergunta="": ver_camera_jarvis(pergunta),
    "executar_passo_a_passo": lambda ordens: executar_passo_a_passo(ordens, consultar_ia),
    "salvar_contexto": lambda chave, valor: (contexto_global.salvar(chave, valor), f"Informação '{chave}' salva com sucesso."),
    "recuperar_contexto": lambda chave: contexto_global.recuperar(chave),
    "pesquisar_na_web": pesquisar_na_web,
    "iniciar_protocolo_aprendizado": lambda intervalo_segundos=1.0: visual_teacher.iniciar_sessao(intervalo_segundos),
    "parar_protocolo_aprendizado": lambda: visual_teacher.parar_sessao(),
    "analisar_protocolo_aprendizado": lambda: visual_teacher.analisar_aprendizado(),
    "indexar_documentos_locais": lambda: rag_service.indexar_documentos(),
    "consultar_conhecimento_local": lambda pergunta: rag_service.consultar_conhecimento(pergunta),
    "pesquisa_deep_dive": lambda tema: _executar_pesquisa_deep_dive(tema),
    "adicionar_meta": lambda m: goal_manager.adicionar_meta_diaria(m),
    "ver_minhas_metas": lambda: goal_manager.obter_relatorio_manhã(),
    "navegar_web": pesquisar_navigator,
    "executar_comando_sistema": executar_terminal
}

def _executar_pesquisa_deep_dive(tema):
    """Executa uma pesquisa profunda e gera um relatório .md automático."""
    falar(f"Iniciando pesquisa profunda sobre '{tema}'. Vou processar isso em segundo plano para você, senhor.")
    def _task():
        try:
            # 1. Pesquisa inicial
            prompt_plan = f"Gere uma lista de 3 buscas precisas no Google para pesquisar profundamente sobre: {tema}"
            buscas = consultar_ia(prompt_plan, salvar_no_historico=False).split("\n")
            
            relatorio = f"# Relatório Deep-Dive: {tema}\nData: {datetime.datetime.now()}\n\n"
            for b in buscas[:3]:
                if b.strip():
                    # Simula a busca e extração (aqui o Jarvis usaria o browser_agent se estivesse integrado)
                    res = pesquisar_na_web(b)
                    relatorio += f"## Busca: {b}\n\n{res}\n\n"
            
            # 2. Síntese Final
            prompt_sintese = f"Com base nestas informações, gere uma conclusão executiva sobre '{tema}':\n\n{relatorio}"
            conclusao = consultar_ia(prompt_sintese, salvar_no_historico=False, use_tools=False)
            relatorio += f"## Conclusão Executiva\n\n{conclusao}"
            
            path = os.path.join(os.path.expanduser("~"), "Documents", f"deep_dive_{tema.replace(' ', '_')}.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(relatorio)
            print(f"[Deep-Dive] Relatório salvo em: {path}")
            falar(f"Senhor, a pesquisa sobre '{tema}' foi concluída e o relatório está salvo em seus Documentos.")
        except Exception as e:
            print(f"[Erro Deep-Dive] {e}")

    threading.Thread(target=_task, daemon=True).start()
    return "Pesquisa iniciada em segundo plano."

def _executar_automacao_mouse_teclado(comandos):
    """Executa a lista de comandos pyautogui fornecida pela IA de forma segura."""
    print(f"\n[Automacao GUI] Executando {len(comandos)} comandos...")
    import pyautogui
    import time
    resultado_log = []
    
    # Fail-safe do pyautogui já vem ativado (jogar mouse pro canto da tela aborta)
    pyautogui.FAILSAFE = True
    
    for cmd in comandos:
        try:
            print(f" -> {cmd}")
            # Contexto extremamente restrito para eval/exec rodar apenas funções do pyautogui e time
            contexto_seguro = {"pyautogui": pyautogui, "time": time}
            exec(cmd, contexto_seguro)
            time.sleep(0.5) # Pausa humanizada entre ações
            resultado_log.append(f"Sucesso: {cmd}")
        except Exception as e:
            print(f" [X] Falha no comando '{cmd}': {e}")
            resultado_log.append(f"Erro em '{cmd}': {e}")
            return "\n".join(resultado_log) + "\nAutomação abortada devido a erro."
            
    return "Automação via mouse/teclado concluída com sucesso no PC do usuário.\n" + "\n".join(resultado_log)

def _chamar_provedor_ia_core(messages_input, provider=None, use_tools=True):
    """Motor de Execução Unificado usando LLMRouter."""
    from brain.llm.router import router as llm_router
    
    # Clona a lista para não poluir o histórico global
    messages = list(messages_input)

    try:
        # Loop de Tool Calling (máx 5 rodadas)
        for rodada in range(5):
            resultado = llm_router.chat(messages=messages, tools=TOOLS if use_tools else None)
            
            print(f"[IA] Usando {resultado.get('provider', 'Router')}...")
            
            if resultado.get("tool_calls"):
                # Reconstrói no formato OpenAI para o histórico
                tool_calls_dict = []
                for tc in resultado["tool_calls"]:
                    tool_calls_dict.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else tc["arguments"]
                        }
                    })
                    
                messages.append({
                    "role": "assistant",
                    "content": resultado.get("text") or "",
                    "tool_calls": tool_calls_dict
                })
                
                for tool_call in resultado["tool_calls"]:
                    function_name = tool_call["name"]
                    function_to_call = AVAILABLE_FUNCTIONS.get(function_name)
                    if function_to_call:
                        try:
                            function_args = tool_call["arguments"]
                            if isinstance(function_args, str):
                                function_args = json.loads(function_args)
                            print(f"[Tool Calling] Router executando: {function_name}", flush=True)
                            atualizar_ui('thinking')
                            function_response = function_to_call(**function_args)
                            messages.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "name": function_name,
                                "content": str(function_response),
                            })
                        except Exception as e_tool:
                            print(f"[Erro Tool] {e_tool}")
                            messages.append({
                                "tool_call_id": tool_call["id"],
                                "role": "tool",
                                "name": function_name,
                                "content": f"Erro na execução da ferramenta: {e_tool}",
                            })
                # Continua o loop para a IA processar o resultado da ferramenta (nova chamada à API)
                continue
            else:
                return resultado.get("text", "Ação concluída.")
    except Exception as e:
        print(f"[ERRO _chamar_provedor_ia_core] {e}")
        import traceback
        traceback.print_exc()
        return None

def classificar_intencao(pergunta):
    """
    O Cérebro (Brain Classifier - Poder do Oponente).
    Decide se a pergunta precisa de PESQUISA em tempo real ou se é CHITCHAT/AÇÃO.
    """
    print("[NÚCLEO FDM-1] Classificando intenção...")
    prompt_classifier = (
        "Você é o classificador de intenções do J.A.R.V.I.S.\n"
        "Sua única tarefa é decidir se a mensagem do usuário precisa de PESQUISA WEB em tempo real ou não.\n\n"
        "Responda APENAS com uma palavra:\n"
        "- 'realtime': Para notícias, clima, preços, pessoas famosas, eventos recentes ou qualquer fato que mude com o tempo.\n"
        "- 'general': Para conversas, comandos de sistema, ajuda com código, ou fatos estáticos.\n\n"
        "Regra de Ouro: Na dúvida, escolha 'realtime'.\n"
        "Mensagem: " + pergunta
    )
    
    # Usa um modelo rápido para classificação
    try:
        mensagens = [{"role": "system", "content": "Responda apenas com 'realtime' ou 'general'."}, {"role": "user", "content": prompt_classifier}]
        classe = _chamar_provedor_ia_core(mensagens, use_tools=False)
        if classe:
            classe = classe.lower().strip()
            print(f"[NÚCLEO FDM-1] Intenção detectada: {classe}")
            return "realtime" if "realtime" in classe else "general"
    except:
        pass
    return "general"

def consultar_ia(pergunta, salvar_no_historico=True, use_tools=True):
    """Consulta a IA com suporte a Colaboração Multi-Agente (Swarm) e Tools."""
    global historico_conversa
    try:
        pergunta_original = pergunta
        pergunta_lower = pergunta.lower()
        
        # 0. BRAIN CLASSIFIER (Autonomia do Oponente)
        # Se não houver agentes explícitos, deixa o Jarvis decidir se pesquisa
        skills_detectadas_pre_classificacao = [s_name for s_name in skill_manager.skills if f"@{s_name}" in pergunta_lower]
        
        if not skills_detectadas_pre_classificacao and use_tools:
            intencao = classificar_intencao(pergunta)
            if intencao == "realtime":
                print("[NÚCLEO FDM-1] Pergunta de tempo real detectada. Ativando @navigator...")
                pergunta = f"@navigator pesquise e responda: {pergunta}"
        
        # 1. Identifica todos os agentes/skills mencionados após a classificação
        pergunta_lower = pergunta.lower()
        matches = []
        for s_name in skill_manager.skills:
            pos_at = pergunta_lower.find(f"@{s_name}")
            pos_direct = pergunta_lower.find(s_name)
            pos = pos_at if pos_at != -1 else pos_direct
            if pos != -1:
                matches.append((pos, s_name))
        
        matches.sort() # Ordem de menção
        skills_detectadas = [m[1] for m in matches]
        
        if salvar_no_historico:
            historico_conversa.append({"role": "user", "content": pergunta_original}) # Salva a pergunta original
    
        if not skills_detectadas:
            # Modo Normal (Jarvis Solo)
            if salvar_no_historico:
                messages = historico_conversa
            else:
                # Mantém a personalidade mesmo em consultas rápidas (Fix do Personagem)
                messages = [historico_conversa[0], {"role": "user", "content": pergunta}]
            
            resultado = _chamar_provedor_ia_core(messages, use_tools=use_tools)
        else:
            # MODO CONSELHO DE AGENTES (FUSION RESEARCH)
            print(f"[CONSELHO DE AGENTES] Squad: {', '.join(skills_detectadas)}")
            resultado_final = ""
            atividades_concluidas = []
            
            # Supervisor Inicial (Jarvis define o plano)
            plano_prompt = f"O usuário solicitou: {pergunta}\nAgentes disponíveis: {', '.join(skills_detectadas)}.\nDefina a ordem ideal e o que cada um deve fazer brevemente."
            plano = _chamar_provedor_ia_core([{"role": "system", "content": "Você é o Supervisor do Conselho (Jarvis)."}, {"role": "user", "content": plano_prompt}], use_tools=use_tools)
            print(f"[Supervisão] Plano: {plano[:100]}...")

            for i, s_name in enumerate(skills_detectadas):
                socketio.emit('state_change', {'state': 'thinking', 'agent': s_name})
                print(f"[Conselho] {s_name.upper()} em ação...")
                
                skill_prompt = skill_manager.get_skill_prompt(s_name)
                
                # Contexto rico (Mina de Ouro)
                contexto_conselho = f"Plano do Supervisor: {plano}\n\nResultados até agora:\n" + "\n".join(atividades_concluidas)
                prompt_agente = f"Sua vez. {contexto_conselho}\nTarefa: {pergunta}"
                
                messages = [
                    {"role": "system", "content": skill_prompt},
                    {"role": "user", "content": prompt_agente}
                ]
                
                passo_resultado = _chamar_provedor_ia_core(messages, use_tools=use_tools)
                
                if passo_resultado:
                    atividades_concluidas.append(f"[{s_name.upper()}]: {passo_resultado}")
                    resultado_final += f"\n\n--- [CONTRIBUIÇÃO DE {s_name.upper()}] ---\n{passo_resultado}"
                
            # REVISOR FINAL (Garante consistência)
            print("[Conselho] Jarvis realizando revisão final...")
            revisao_prompt = f"Revise todas as contribuições e entregue a resposta final unificada para o usuário.\nContribuições:\n{resultado_final}"
            resultado = _chamar_provedor_ia_core([{"role": "system", "content": "Você é o Jarvis, revisor final do conselho."}, {"role": "user", "content": revisao_prompt}], use_tools=use_tools)
            
            socketio.emit('state_change', {'state': 'speaking', 'agent': 'jarvis'})
    
        if not resultado:
            return "Senhor, sinto muito, mas meus módulos de inteligência estão offline no momento."
    
        # Verifica repetição
        if len(historico_conversa) > 2:
            ultima_resposta = historico_conversa[-2].get("content", "")
            if resultado == ultima_resposta:
                 return "Como eu disse anteriormente, " + resultado
    
        if salvar_no_historico:
            historico_conversa.append({"role": "assistant", "content": resultado})
            podar_historico()
            
        # --- INJEÇÃO DA FÁBRICA DE AGENTES ---
        # Só injeta se houver INTENÇÃO CLARA de criar um novo agente (evita criação acidental ao ler textos)
        gatilhos_criacao = ["crie um novo agente", "fabrique um agente", "novo especialista", "gere um agente"]
        if resultado and any(k in pergunta.lower() for k in gatilhos_criacao) and ("```html" in resultado.lower() or "<button class" in resultado.lower()):
            import re
            try:
                # Regex flexível para capturar blocos de código
                html_matches = re.findall(r'```(?:html)?\s*([\s\S]*?)```', resultado, re.IGNORECASE)
                js_matches = re.findall(r'```(?:javascript|js)?\s*([\s\S]*?)```', resultado, re.IGNORECASE)
                
                # Tenta achar os blocos pelo conteúdo caso o markdown fuja um pouco do padrão
                html_code = ""
                js_code = ""
                
                for match in html_matches:
                    if "<button" in match or "agent-tab" in match: html_code = match.strip()
                for match in js_matches:
                    if "AGENT_DESCRIPTIONS" in match: js_code = match.strip()
                    
                # Se não achou na busca específica de HTML/JS, tenta a busca genérica se só houverem 2 blocos
                todas_matches = re.findall(r'```[a-zA-Z]*\s*\n([\s\S]*?)```', resultado)
                if not html_code and not js_code and len(todas_matches) >= 2:
                     for m in todas_matches:
                         if "<button" in m: html_code = m.strip()
                         if "AGENT_DESCRIPTIONS" in m: js_code = m.strip()

                if html_code and js_code:
                    agent_name_match = re.search(r'data-agent="([^"]+)"', html_code)
                    agent_name = agent_name_match.group(1).lower() if agent_name_match else "novo_agente"
                    
                    injetar_novo_agente_na_gui(html_code, js_code, agent_name)
                    
                    # Extração mais branda para o SKILL.md (O Brain)
                    # Pega tudo desde "### [SKILL.md" ou apenas a partir de "Role:"
                    skill_match = re.search(r'###\s*\[SKILL\.md.*?\](.*?)###\s*\[UI', resultado, re.DOTALL | re.IGNORECASE)
                    if not skill_match:
                         # Fallback brutal: tenta pegar do "Role:" pra frente até o próximo bloco markdown ou ```
                         skill_match = re.search(r'(\*\*Role:\*\*.*?)```', resultado, re.DOTALL | re.IGNORECASE)
                         
                    if skill_match:
                        skill_content = skill_match.group(1).strip()
                        skill_path = os.path.join(os.path.dirname(__file__), "skills", f"{agent_name}.md")
                        with open(skill_path, "w", encoding="utf-8") as f:
                            f.write(skill_content)
                        print(f"[Fábrica de Agentes] Cérebro do {agent_name} salvo com sucesso!", flush=True)
                        skill_manager.load_skills()
                    else:
                        print("[Fábrica de Agentes] Aviso: Não consegui extrair o SKILL.md de forma limpa, injetando GUI mesmo assim.")
                        
                    # Impede que o Jarvis fale ou mostre todo o código markdown no chat
                    resultado = f"O agente {agent_name.capitalize()} foi fabricado e integrado à sua interface com sucesso, senhor."
            except Exception as e:
                print(f"[Erro Fábrica Auto] Falha na regex ou injeção: {e}", flush=True)
                
        return resultado
    except Exception as e:
        print(f"[ERRO IA] {e}")
        return "Sinto muito, senhor, mas meus servidores de inteligência estão apresentando instabilidade no momento."

# ============================================================
# MÓDULO HUGIN (HUGGINGFACE EXPERT)
# ============================================================

def chamar_huggingface(model_id, inputs):
    """Executa uma chamada de inferência para um modelo do HuggingFace Hub."""
    if not hf_client:
        return "Erro: Token do HuggingFace não configurado."
    
    try:
        print(f"[Hugin] Invocando modelo: {model_id}")
        # Simplificação para modelos de texto/visão baseados em chat ou tarefas comuns
        # Nota: Dependendo do modelo, o formato do input muda. 
        # Aqui focamos em modelos de Image-to-Text ou Texto-para-Texto.
        response = hf_client.post(json={"inputs": inputs}, model=model_id)
        
        # Tenta decodificar a resposta (geralmente uma lista de dicts ou string)
        res_json = response.json()
        if isinstance(res_json, list) and len(res_json) > 0:
            if 'generated_text' in res_json[0]:
                return res_json[0]['generated_text']
            return str(res_json[0])
        return str(res_json)
    except Exception as e:
        print(f"[Erro Hugin] {e}")
        return f"Falha na execução do modelo {model_id}: {str(e)}"

# ============================================================
# HABILIDADES DO JARVIS
# ============================================================

def pesquisar_wikipedia(termo):
    """Pesquisa um tema na Wikipedia em Português."""
    try:
        wikipedia.set_lang("pt")
        return wikipedia.summary(termo, sentences=2)
    except wikipedia.exceptions.DisambiguationError:
        return f"Encontrei múltiplos resultados para '{termo}'. Pode ser mais específico, senhor?"
    except wikipedia.exceptions.PageError:
        return f"Não encontrei nenhum artigo sobre '{termo}' na Wikipedia."
    except Exception as e:
        return f"Erro na pesquisa: {e}"

# --- Mapa de aplicativos conhecidos ---
# Estrutura: { "palavra_chave": ("comando_executvel", "Nome Amigável") }
APPS: dict[str, tuple[str, str]] = {
    "notepad":       ("notepad.exe",                   "Bloco de Notas"),
    "bloco de notas":("notepad.exe",                   "Bloco de Notas"),
    "calculadora":   ("calc.exe",                      "Calculadora"),
    "paint":         ("mspaint.exe",                   "Paint"),
    "explorador":    ("explorer.exe",                  "Explorador de Arquivos"),
    "chrome":        ("chrome.exe",                    "Google Chrome"),
    "google chrome": ("chrome.exe",                    "Google Chrome"),
    "spotify":       ("start spotify",                  "Spotify"),
    "discord":       ("discord.exe",                   "Discord"),
    "vs code":       ("code.exe",                      "VS Code"),
    "visual studio code": ("code.exe",                 "VS Code"),
    "cmd":           ("cmd.exe",                       "Prompt de Comando"),
    "terminal":      ("wt.exe",                        "Windows Terminal"),
    "word":          ("WINWORD.EXE",                   "Microsoft Word"),
    "excel":         ("EXCEL.EXE",                     "Microsoft Excel"),
    "powerpoint":    ("POWERPNT.EXE",                  "PowerPoint"),
    "tarefa":        ("taskmgr.exe",                   "Gerenciador de Tarefas"),
    "gerenciador de tarefas": ("taskmgr.exe",          "Gerenciador de Tarefas"),
    "steam":         ("start steam://open/main",        "Steam"),
    "zoom":          ("zoom.exe",                      "Zoom"),
    "teams":         ("ms-teams.exe",                  "Microsoft Teams"),
    "whatsapp":      ("start whatsapp://",              "WhatsApp"),
}

# ============================================================
# MÓDULO SMART TV (Pillar 4 - Fase 22)
# ============================================================
class SmartTVManager:
    """Interface para controle de Smart TVs (Android/Google TV via ADB/Network)."""
    def __init__(self, ip=None):
        self.ip = ip # O usuário pode dizer o IP ou podemos tentar descobrir
        self.adb_path = "adb" # Assume que está no PATH

    def _run_adb(self, command):
        if not self.ip: return "Erro: IP da TV não configurado."
        full_cmd = f"{self.adb_path} -s {self.ip} {command}"
        try:
            subprocess.run(full_cmd, shell=True, check=True, capture_output=True)
            return True
        except Exception as e:
            return f"Falha na conexão com a TV: {e}"

    def control(self, action):
        actions = {
            "ligar": "shell input keyevent 26",
            "home": "shell input keyevent 3",
            "vol_up": "shell input keyevent 24",
            "vol_down": "shell input keyevent 25",
            "mute": "shell input keyevent 164",
            "netflix": "shell am start -n com.netflix.ninja/com.netflix.ninja.MainActivity",
            "youtube": "shell am start -n com.google.android.youtube.tv/com.google.android.apps.youtube.tv.activity.ShellActivity"
        }
        if action in actions:
            res = self._run_adb(actions[action])
            if res is True: return f"Comando '{action}' enviado para a TV."
            return res
        return "Comando de TV não reconhecido."

tv_manager = SmartTVManager() # Global instance

def abrir_aplicativo(comando):
    """Tenta abrir um aplicativo mapeado ou pelo nome."""
    for chave in APPS:
        info = APPS[chave]
        exe = info[0]
        nome_amigavel = info[1]
        
        if chave in comando:
            try:
                subprocess.Popen(exe, shell=True)
                return f"Abrindo o {nome_amigavel}, senhor."
            except Exception as e:
                return f"Não consegui abrir o {nome_amigavel}: {e}"
    return None

def controlar_volume(comando):
    """Ajusta o volume do sistema via PowerShell."""
    try:
        if "aumentar volume" in comando or "volume alto" in comando or "aumenta o volume" in comando:
            # Aumenta volume em ~20%
            script = (
                "$sink = Get-AudioDevice -Playback; "
                "Set-AudioDevice -PlaybackVolume ([Math]::Min(($sink.Volume + 20), 100))"
            )
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return "Volume aumentado, senhor."

        elif "diminuir volume" in comando or "volume baixo" in comando or "diminui o volume" in comando:
            script = (
                "$sink = Get-AudioDevice -Playback; "
                "Set-AudioDevice -PlaybackVolume ([Math]::Max(($sink.Volume - 20), 0))"
            )
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return "Volume reduzido, senhor."

        elif "mudo" in comando or "silenciar" in comando or "mutar" in comando:
            subprocess.run(
                ["powershell", "-Command",
                 "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                capture_output=True
            )
            return "Sistema silenciado."
    except Exception as e:
        return f"Não consegui controlar o volume: {e}"
    return None

def tirar_screenshot(comando):
    """Captura a tela e salva em Documentos."""
    if any(k in comando for k in ["screenshot", "captura de tela", "print da tela", "printscreen"]):
        try:
            import pyautogui  # importação opcional
            caminho = os.path.join(os.path.expanduser("~"), "Documents",
                                   f"jarvis_screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            pyautogui.screenshot(caminho)
            return f"Screenshot salvo em Documentos, senhor."
        except ImportError:
            return "O módulo pyautogui não está instalado. Execute: pip install pyautogui"
        except Exception as e:
            return f"Falha ao tirar screenshot: {e}"
    return None

def listar_processos(comando):
    """Lista os processos em execução."""
    if any(k in comando for k in ["processos", "o que está rodando", "programas abertos"]):
        try:
            resultado = subprocess.run(
                ["tasklist", "/fo", "table", "/nh"],
                capture_output=True, text=True, timeout=5
            )
            # Filtra linhas vazias e pega as primeiras 8
            todas_linhas = [l.strip() for l in resultado.stdout.split('\n') if l.strip()]
            num_linhas = len(todas_linhas)
            linhas_resumidas = todas_linhas[0:min(num_linhas, 8)]
            
            # Pega o primeiro nome (coluna 1) de cada processo
            nomes: list[str] = []
            for l in linhas_resumidas:
                partes = l.split()
                if partes:
                    nomes.append(partes[0])
            
            limit: int = 6
            if len(nomes) < 6:
                limit = len(nomes)
            
            # Use slicing de forma mais clara para o linter
            subset_nomes = [nomes[i] for i in range(limit)]
            lista = ", ".join(subset_nomes)
            return f"Alguns processos em execução: {lista}."
        except Exception as e:
            return f"Não consegui listar os processos: {e}"
    return None

def encerrar_processo(comando):
    """Encerra um processo pelo nome."""
    if "encerrar" in comando or "fechar" in comando or "matar" in comando:
        for chave in APPS:
            info = APPS[chave]
            exe = info[0]
            nome = info[1]
            
            if chave in comando:
                try:
                    subprocess.run(["taskkill", "/f", "/im", exe], capture_output=True)
                    return f"{nome} encerrado."
                except Exception as e:
                    return f"Não consegui encerrar o {nome}: {e}"
    return None

# ============================================================
# PROCESSAMENTO DE COMANDOS
# ============================================================

def processar_comando(comando):
    """Processa o comando de voz de forma adaptativa. Retorna True se deve continuar a conversa."""
    global CONDIÇÃO_ESTADO

    if not comando:
        return True

    cmd_lower = comando.lower()
    print(f"Voce: {comando}")

    # --- 0. HANDLER DE CONFIRMAÇÃO (RACIOCÍNIO ATIVO) ---
    if CONDIÇÃO_ESTADO["aguardando_confirmacao"]:
        socketio.emit('state_change', {'state': 'thinking'}) # Mostra que está processando a resposta
        
        sim_keywords = ["sim", "isso mesmo", "com certeza", "confirmar", "positivo", "pode ser", "exato"]
        nao_keywords = ["não", "cancela", "esquece", "parar", "não é isso", "negativo"]
        
        if any(k in cmd_lower for k in sim_keywords):
            acao = CONDIÇÃO_ESTADO["acao_pendente"]
            CONDIÇÃO_ESTADO["aguardando_confirmacao"] = False
            CONDIÇÃO_ESTADO["acao_pendente"] = ""
            falar("Confirmado, senhor. Executando agora.")
            # Re-processa o comando original agora que foi confirmado
            return processar_comando(CONDIÇÃO_ESTADO["comando_original"])
        
        elif any(k in cmd_lower for k in nao_keywords):
            CONDIÇÃO_ESTADO["aguardando_confirmacao"] = False
            CONDIÇÃO_ESTADO["acao_pendente"] = ""
            CONDIÇÃO_ESTADO["comando_original"] = ""
            falar("Entendido. Abortando comando.")
            return True
        
        else:
            falar("Desculpe, senhor. Preciso de uma confirmação simples. Sim ou não?")
            return True

    # --- 1. COMANDOS DE CONTROLE (PRIORIDADE MÁXIMA) ---
    if any(k in cmd_lower for k in ["desligar sistema", "encerrar jarvis"]):
        falar("Entendido, senhor. Desativando todos os protocolos.")
        sys.exit(0)

    # --- PROTOCOLOS DE EMERGÊNCIA / INTERFACE (OFFLINE SAFE) ---
    TRIGGERS_RAIZ = ["protocolo raiz", "ativar protocolo raiz offline"]
    
    # Detecção de Ambiguidade (Raciocínio)
    if not CONDIÇÃO_ESTADO["aguardando_confirmacao"]:
        if "raiz" in cmd_lower and not any(k in cmd_lower for k in TRIGGERS_RAIZ):
            # O usuário falou "raiz" mas não usou o trigger exato
            CONDIÇÃO_ESTADO["aguardando_confirmacao"] = True
            CONDIÇÃO_ESTADO["acao_pendente"] = "protocol_raiz"
            CONDIÇÃO_ESTADO["comando_original"] = "protocolo raiz" 
            falar("Você quis dizer protocolo raiz, senhor?")
            socketio.emit('state_change', {'state': 'reasoning'}) 
            return True

    if any(k in cmd_lower for k in TRIGGERS_RAIZ):
        socketio.emit('protocol_change', {'protocol': 'RAIZ'})
        falar("Protocolo Raiz ativado. Exibindo diagramas de infraestrutura e sobreposição tática.")
        return True # Mantém a conversa ativa

    TRIGGERS_PADRAO = ["protocolo padrão", "desativar raiz", "sair do modo urgente"]
    if any(k in cmd_lower for k in TRIGGERS_PADRAO):
        socketio.emit('protocol_change', {'protocol': 'PADRÃO'})
        falar("Retornando ao Protocolo Padrão. Ocultando circuitos secundários.")
        return True # Mantém a conversa ativa

    # Configurar inicialização automática
    if "iniciar com o windows" in cmd_lower:
        falar("Configurando inicialização automática, senhor. Um momento.")
        try:
            # Caminho absoluto para o script PS
            caminho_script = os.path.join(os.path.dirname(__file__), "criar_atalho.ps1")
            # Corrige o conteúdo do script para usar o caminho atual absoluto
            bat_path = os.path.join(os.path.dirname(__file__), "iniciar_jarvis.bat")
            working_dir = os.path.dirname(__file__)
            
            ps_cmd = (
                f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('$env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\Jarvis.lnk');"
                f"$s.TargetPath='{bat_path}';"
                f"$s.WorkingDirectory='{working_dir}';"
                f"$s.Save()"
            )
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            falar("Pronto, Gabriel. Agora iniciarei automaticamente sempre que você ligar o computador.")
        except Exception as e:
            print(f"[ERRO STARTUP] {e}")
            falar("Houve uma falha técnica ao tentar configurar a inicialização.")
        return True

    if "não inicie mais com o windows" in cmd_lower or "remover inicialização" in cmd_lower:
        falar("Removendo inicialização automática.")
        try:
            atalho = os.path.join(os.environ['APPDATA'], r"Microsoft\Windows\Start Menu\Programs\Startup\Jarvis.lnk")
            if os.path.exists(atalho):
                os.remove(atalho)
                falar("Atalho removido com sucesso.")
            else:
                falar("Eu não estava configurado para iniciar automaticamente, senhor.")
        except Exception as e:
            print(f"[ERRO REMOVE STARTUP] {e}")
            falar("Não consegui remover o atalho de inicialização.")
        return True

    if any(k in cmd_lower for k in ["obrigado", "tchau", "até logo", "por hoje é só", "descansar"]):
        falar("Sem problemas, Gabriel. Estarei no aguardo.")
        return False

    # --- 2. MODO DITADO (GABRIEL) ---
    def digitar_seguro(texto):
        """Helper para digitar texto com acentos via clipboard."""
        import pyperclip
        import pyautogui
        pyperclip.copy(texto)
        pyautogui.hotkey('ctrl', 'v')

    if any(k in cmd_lower for k in ["escreva o que eu", "digite o que eu", "modo ditado", "escreva tudo que eu"]):
        falar("Pode falar Gabriel, escreverei exatamente o que escutar. Diga 'encerrar ditado' para terminar.")
        while True:
            # Ouve sem a wake word enquanto estiver ditando
            frase = ouvir(timeout=10, frase_limite=30)
            if frase:
                if any(k in frase.lower() for k in ["parar", "encerrar ditado", "chega de escrever", "desativar modo ditado", "cancelar ditado"]):
                    falar("Ditado finalizado.")
                    break
                # Digita o que ouviu
                digitar_seguro(frase + " ")
                print(f"[DITADO]: {frase}")
            else:
                # Continua escutando se houve apenas silêncio
                continue
        return True

    # --- 3. APRENDIZADO AUTOMÁTICO ---
    aprendeu = aprender_fato(comando)

    # --- 4. DETECÇÃO DE AÇÕES (ADAPTATIVO) ---
    # Tenta resolver ações comuns antes de ir para a IA de chat pura

    # ================================================================
    # 4.0. VISÃO DE TELA (Fase 1)
    # ================================================================
    TRIGGERS_VISAO = [
        "olhe minha tela", "veja minha tela", "o que está na minha tela",
        "o que tem na tela", "analise a tela", "descreva a tela",
        "o que está aberto", "veja o que está na tela", "me diga o que há na tela",
        "olha minha tela", "veja isso"
    ]
    if any(k in cmd_lower for k in TRIGGERS_VISAO):
        falar("Ativando sistema de visão. Capturando sua tela agora, senhor.")
        atualizar_ui('thinking')
        # Extrai a pergunta específica do usuário (o que ele quer saber sobre a tela)
        pergunta_tela = cmd_lower
        for trigger in TRIGGERS_VISAO:
            pergunta_tela = pergunta_tela.replace(trigger, "").strip()
        if not pergunta_tela:
            pergunta_tela = "Descreva tudo que está visível na tela: aplicativos abertos, conteúdo, textos, janelas ativas."
        
        resultado_visao = ver_tela_jarvis(
            pergunta=pergunta_tela
        )
        falar(resultado_visao)
        return True

    # ================================================================
    # 4.0f. VISÃO DE CÂMERA
    # ================================================================
    TRIGGERS_CAMERA = ["ligue a câmera", "veja pela câmera", "ative a câmera", "o que você vê na câmera", "olhe para mim"]
    if any(k in cmd_lower for k in TRIGGERS_CAMERA):
        falar("Ativando protocolos ópticos. Um momento, senhor.")
        pergunta_cam = cmd_lower
        for t in TRIGGERS_CAMERA: pergunta_cam = pergunta_cam.replace(t, "").strip()
        res = ver_camera_jarvis(pergunta_cam if pergunta_cam else "Descreva o que vê")
        falar(res)
        return True

    # ================================================================
    # 4.0b. GRAVAÇÃO DE AÇÕES (Fase 2)
    # ================================================================
    TRIGGERS_INICIAR_GRAVACAO = [
        "entre em modo observação", "ative o modo gravação", "comece a gravar",
        "modo observação", "grave minhas ações", "observe o que faço",
        "iniciar gravação de macros", "gravar rotina", "nova rotina"
    ]
    if any(k in cmd_lower for k in TRIGGERS_INICIAR_GRAVACAO):
        msg = action_recorder_instance.iniciar()
        socketio.emit('protocol_change', {'protocol': 'GRAVANDO'})
        falar(msg)
        return True

    # --- 4.0e. ENSINO VISUAL (Multimodal) ---
    TRIGGERS_ENSINO_VISUAL = [
        "ensinar uma nova habilidade por meio de várias capturas de telas",
        "ensinar uma nova habilidade por meio de várias capturas",
        "ensinar uma nova habilidade por meio de várias fotos",
        "ensinar por meio de capturas",
        "ensinar via fotos",
        "vou te ensinar uma nova habilidade",
        "ensinar nova habilidade via tela",
        "gravação de tela", "gravar minha tela", "grave a tela",
        "iniciar gravação da tela", "ensinar o fire"
    ]
    if any(k in cmd_lower for k in TRIGGERS_ENSINO_VISUAL):
        msg = visual_teacher_instance.iniciar_sessao()
        socketio.emit('protocol_change', {'protocol': 'GRAVANDO'})
        falar(msg)
        
        # Inicia thread de captura periódica (a cada 4s)
        def loop_captura():
            while visual_teacher_instance.esta_observando:
                visual_teacher_instance.capturar_passo()
                time.sleep(4)
        
        threading.Thread(target=loop_captura, daemon=True).start()
        return True

    TRIGGERS_PARAR_ENSINO = [
        "já terminei de ensinar", "pode parar de observar", "aprendido", "finalizar ensino",
        "já enviei as fotos", "terminei o ensino"
    ]
    if any(k in cmd_lower for k in TRIGGERS_PARAR_ENSINO) and visual_teacher_instance.esta_observando:
        msg = visual_teacher_instance.parar_sessao()
        socketio.emit('protocol_change', {'protocol': 'PADRÃO'})
        falar(msg)
        
        falar("Iniciando a análise multimodal para extrair a nova habilidade, senhor. Um momento.")
        atualizar_ui('thinking')
        
        resultado = visual_teacher_instance.analisar_aprendizado()
        
        if resultado:
             # Salva o aprendizado visual no fire_knowledge
             nome_habilidade = "Habilidade Visual " + datetime.datetime.now().strftime('%H%M')
             instrucao_fire = f"\n### CONHECIMENTO VISUAL ADQUIRIDO: {nome_habilidade}\n"
             instrucao_fire += f"Descrição do Processo Observado:\n{resultado}\n"
             
             knowledge_path = os.path.join(os.path.dirname(__file__), "skills", "fire_knowledge.md")
             mode = "a" if os.path.exists(knowledge_path) else "w"
             with open(knowledge_path, mode, encoding="utf-8") as f:
                 f.write(instrucao_fire)
             
             falar(f"Análise concluída. O Fire agora possui o registro visual desta nova habilidade sob o rótulo '{nome_habilidade}'.")
        else:
            falar("Não consegui extrair uma lógica clara das imagens, senhor. Tente realizar o processo de forma mais pausada.")
        return True

    TRIGGERS_PARAR_GRAVACAO = [
        "para de gravar", "pare de gravar", "encerrar gravação",
        "parar gravação", "salve como", "salvar rotina", "salve a rotina",
        "terminei a gravação"
    ]
    if any(k in cmd_lower for k in TRIGGERS_PARAR_GRAVACAO) or action_recorder_instance.esta_gravando and any(k in cmd_lower for k in ["salve", "parar", "encerrar"]):
        # Extrai o nome da rotina do comando
        nome_rotina = None
        for marcador in ["salve como", "chame de", "como", "salvar como"]:
            if marcador in cmd_lower:
                nome_rotina = cmd_lower.split(marcador)[-1].strip()
                break
        msg = action_recorder_instance.parar(nome_rotina)
        socketio.emit('protocol_change', {'protocol': 'PADRÃO'})
        falar(msg)
        return True


    # ================================================================
    # 4.0d. ENSINAR AO FIRE (Integração)
    # ================================================================
    TRIGGERS_ENSINAR_AO_FIRE = [
        "ensine ao fire", "ensinar ao fire", "passe para o fire", "treine o fire",
        "ensine pro fire", "mostrar para o fire"
    ]
    if any(k in cmd_lower for k in TRIGGERS_ENSINAR_AO_FIRE):
        nome_rotina = None
        for marcador in ["rotina", "a rotina", "sobre", "como"]:
            if marcador in cmd_lower:
                nome_rotina = cmd_lower.split(marcador)[-1].replace("ao fire", "").strip()
                break
        
        if not nome_rotina:
             falar("Senhor, qual rotina devo ensinar ao Fire?")
             return True
             
        falar(f"Entendido. Vou processar a rotina '{nome_rotina}' e repassar o conhecimento ao Fire.")
        
        rotina = carregar_rotina(nome_rotina)
        if not rotina:
            falar(f"Não encontrei a rotina '{nome_rotina}', senhor.")
            return True
            
        # Gera o script inteligente via IA
        falar("Analisando as ações gravadas para extrair o padrão lógico...")
        script_ia = gerar_script_ia(rotina.get("acoes", []), lambda p, **kwargs: consultar_ia(p, salvar_no_historico=False))
        
        if script_ia:
            # Salva esse "conhecimento" em um arquivo que o Fire pode consultar
            instrucao_fire = f"\n### CONHECIMENTO ADQUIRIDO: {nome_rotina.upper()}\n"
            instrucao_fire += f"Descrição: Rotina ensinada pelo usuário para '{nome_rotina}'.\n"
            instrucao_fire += f"Exemplo de implementação em Python (pyautogui):\n```python\n{script_ia}\n```\n"
            
            knowledge_path = os.path.join(os.path.dirname(__file__), "skills", "fire_knowledge.md")
            mode = "a" if os.path.exists(knowledge_path) else "w"
            with open(knowledge_path, mode, encoding="utf-8") as f:
                f.write(instrucao_fire)
            
            falar(f"O Fire agora sabe exatamente como executar a rotina '{nome_rotina}'. Ele usará esse conhecimento para criar novos agentes especialistas quando o senhor solicitar.")
        else:
            falar("Houve um problema ao processar a lógica da rotina via IA, senhor. Poderia tentar gravar novamente?")
        return True

    # ================================================================
    # 4.0c. REPLAY DE ROTINAS (Fase 3)
    # ================================================================
    if any(k in cmd_lower for k in ["listar rotinas", "minhas rotinas", "que rotinas", "rotinas disponíveis"]):
        falar(listar_rotinas())
        return True

    TRIGGERS_EXECUTAR_ROTINA = ["execute a rotina", "executar rotina", "repita o que eu fiz", "rodar rotina", "execute rotina"]
    for trigger in TRIGGERS_EXECUTAR_ROTINA:
        if trigger in cmd_lower:
            nome_rotina = cmd_lower.replace(trigger, "").strip()
            if nome_rotina:
                falar(f"Executando a rotina '{nome_rotina}'. Preparando em 3 segundos, senhor.")
                time.sleep(3)  # Dá tempo para o usuário focar na tela
                resultado = executar_rotina_direta(nome_rotina)
            else:
                resultado = listar_rotinas()
            falar(resultado)
            return True

    # Se a resposta contiver um plano de tarefa em JSON (Hugin decidiu usar um modelo externo)
    if skill_manager.current_skill == "hugin" or (isinstance(comando, str) and "hugin" in comando.lower()):
        # Se a resposta da IA (que será pega depois ou já foi pré-processada) tiver JSON
        pass # A lógica de captura do JSON será feita após a consulta_ia para maior flexibilidade

    # 4.2. Automação Robusta (Bloco de Notas + Geração de Pesquisa/Texto)
    if "bloco de notas" in cmd_lower and any(k in cmd_lower for k in ["escreva", "faça", "pesquise", "coloque", "crie", "elabore", "texto"]):
        falar("Iniciando a automação. Preparando o ambiente e elaborando o conteúdo.")
        # 1. Abre o bloco de notas
        subprocess.Popen("notepad.exe")
        time.sleep(1.5) # Espera a janela abrir e ganhar foco
        
        # 2. Pede pra IA gerar APENAS o conteúdo final, usando a string completa que o usuário falou
        prompt_pesquisa = f"O usuário ordenou isso: '{comando}'. Gere O CONTEÚDO FINAL, PRONTO, que deve ser escrito no documento agora. Não inclua texto introdutório do tipo 'Aqui está', escreva APENAS o resultado que deve ir para a folha de texto."
        conteudo = consultar_ia(prompt_pesquisa, salvar_no_historico=False)
        
        # 3. Digita o conteúdo e avisa
        # Usa digitar_seguro para garantir acentos perfeitos (RFS 4)
        pyperclip.copy(conteudo)
        pyautogui.hotkey('ctrl', 'v')
        falar("O documento foi preenchido conforme solicitado.")
        return True

    # 4.2. Pesquisa semântica inteligente (Usa IA para extrair o termo)
    if any(k in cmd_lower for k in ["pesquise", "busque", "procurar", "no youtube", "na internet"]):
        falar("Vou providenciar a busca agora mesmo.")
        
        # Ativa o ORB Inteligente para evasão de janela
        ativar_orb_evasivo()
        
        # Extração inteligente via IA para evitar lixo na pesquisa
        prompt_extracao = f"Extraia APENAS o termo de busca principal desta frase: '{comando}'. Responda APENAS o termo, sem aspas ou explicações."
        termo = consultar_ia(prompt_extracao, salvar_no_historico=False).strip().strip('"').strip("'")
        
        if "youtube" in cmd_lower:
            webbrowser.open(f"https://www.youtube.com/results?search_query={termo.replace(' ', '+')}")
        else:
            # Mantém apenas abertura no navegador externo do sistema
            webbrowser.open(f"https://www.google.com/search?q={termo.replace(' ', '+')}")
        return True

    # Abertura de apps dinâmica
    if any(k in cmd_lower for k in ["abrir", "abra", "inicie"]):
        # Tenta casar com a lista interna
        for chave in APPS:
            if chave in cmd_lower:
                caminho, _ = APPS[chave]
                subprocess.Popen(caminho, shell=True)
                falar(f"Abrindo {chave}, senhor.")
                return True
        # Se não casou, tenta a sorte com o nome direto (ex: "abra notepad")
        try:
            # Remove verbos e artigos comuns ("abra o", "abrir a", etc)
            for prefixo in ["abra o ", "abra a ", "abra ", "abrir o ", "abrir a ", "abrir ", "inicie o ", "inicie a ", "inicie "]:
                if cmd_lower.startswith(prefixo):
                    app_name = cmd_lower.replace(prefixo, "").strip()
                    break
            else:
                app_name = cmd_lower.split("abra" if "abra" in cmd_lower else "abrir")[-1].strip()
            
            if app_name:
                ativar_orb_evasivo()
                subprocess.Popen(app_name, shell=True)
                falar(f"Tentando iniciar {app_name}.")
                return True
        except:
            pass

    # --- 5. RESPOSTA DA IA (CONVERSA E OUTRAS ORDENS) ---
    resposta = consultar_ia(comando)
    
    # --- 5.1. Orquestração Hugin (Pós-IA) ---
    # Se a IA sugeriu um plano de tarefa do HuggingFace (detectável pelo JSON com model_id)
    if "{" in resposta and "model_id" in resposta:
        try:
            # Tenta extrair o JSON (pode haver texto antes/depois)
            start_idx = resposta.find("{")
            end_idx = resposta.rfind("}") + 1
            json_str = resposta[start_idx:end_idx]
            task_data = json.loads(json_str)
            
            if "model_id" in task_data and "inputs" in task_data:
                print(f"[Hugin] Executando comando especializado via API...")
                resultado_hf = chamar_huggingface(task_data["model_id"], task_data["inputs"])
                
                # Gera síntese final da resposta técnica para tom de assistente
                prompt_sintese = f"O modelo '{task_data['model_id']}' processou a informação e retornou: '{resultado_hf}'. Agora, dê a resposta final amigável para o senhor Gabriel."
                resposta = consultar_ia(prompt_sintese, salvar_no_historico=False)
        except Exception as e:
            print(f"[Erro Orquestração Hugin] {e}")

    falar(resposta)
    return True

# ============================================================
# LOOP PRINCIPAL COM WAKE WORD
# ============================================================

window = None

# Absolute path to the startup batch file
BAT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'iniciar_jarvis.bat')

# Removida primeira definicao de J_API duplicada

def iniciar_proatividade():
    """Loop de visão proativa para ajudar o usuário automaticamente."""
    def _loop():
        while True:
            time.sleep(300) # Checa a cada 5 minutos proativamente
            if SISTEMA_ONLINE != "offline":
                try:
                    # Tira print silencioso e analisa
                    tmp_img = os.path.join(tempfile.gettempdir(), "proactive_vision.png")
                    import pyautogui
                    pyautogui.screenshot(tmp_img)
                    
                    # Pergunta para a IA se ela vê algo que exija ajuda proativa
                    msg = "Analise a tela do usuário. Se você ver um erro técnico, um problema de produtividade ou uma oportunidade de ajudar, envie uma frase curta de ajuda. Se tudo estiver normal, responda apenas 'OK'."
                    analise = ver_tela_jarvis(msg) # Re-usa o vision handler
                    
                    if analise and "OK" not in analise.upper():
                        falar(f"Senhor, notei algo na sua tela: {analise}")
                    
                    if os.path.exists(tmp_img): os.remove(tmp_img)
                except:
                    pass
    threading.Thread(target=_loop, daemon=True).start()

def iniciar_agenda_automatica():
    """Reporta metas automaticamente pela manhã e à noite."""
    def _loop():
        # Memória de saudação para não repetir no mesmo dia
        dia_ultimo_report = ""
        while True:
            time.sleep(3600) # Checa a cada hora
            agora = datetime.datetime.now()
            hoje = agora.strftime("%Y-%m-%d")
            
            if hoje != dia_ultimo_report:
                # Manhã (8h)
                if agora.hour == 8:
                    falar(goal_manager.obter_relatorio_manhã())
                    dia_ultimo_report = hoje
                # Noite (20h)
                elif agora.hour == 20:
                    falar(goal_manager.obter_relatorio_noite())
                    dia_ultimo_report = hoje
                    
    threading.Thread(target=_loop, daemon=True).start()

def iniciar_rag_automatico():
    """Loop de indexação automática de documentos do sistema."""
    def _loop():
        while True:
            try:
                print("[RAG Autônomo] Verificando novas informações nas pastas do sistema...")
                resultado = rag_service.indexar_documentos()
                if "Indexação concluída" in resultado:
                    print(f"[RAG Autônomo] {resultado}")
            except Exception as e:
                print(f"[Erro RAG Autônomo] {e}")
            time.sleep(600) # Verifica a cada 10 minutos
    threading.Thread(target=_loop, daemon=True).start()

def ativar_orb_evasivo():
    """Modo Evasão (Phase 6): Transforma o Jarvis num Orb e desvia a janela do conteúdo importante na tela."""
    global jarvis_api, window
    if 'window' not in globals() or not window or 'jarvis_api' not in globals() or not jarvis_api:
        return
    try:
        # Encolhe o Jarvis primeiro para a esquerda
        window.evaluate_js("if(window.toggleOrbMode) window.toggleOrbMode(true);")
        jarvis_api.set_orb_mode(True, target_x=20, target_y=20)
        
        def _evasao():
            time.sleep(1.5) # Aguarda aplicativo/chrome abrir p\ pegar a tela por cima
            tmp_print = os.path.join(tempfile.gettempdir(), "orb_evasion.png")
            import pyautogui
            pyautogui.screenshot(tmp_print)
            
            prompt = "A imagem é a tela atual do usuário. Existe conteúdo MUITO IMPORTANTE ou um vídeo/leitura vital cobrindo o canto SUPERIOR-ESQUERDO da tela? Responda APENAS 'SIM' ou 'NAO'."
            import skills.screen_vision
            resposta = skills.screen_vision._analisar_tela_vision_tradicional(prompt, tmp_print, "google/gemini-2.0-pro-exp-02-05")
            if os.path.exists(tmp_print): os.remove(tmp_print)
            
            if resposta and "SIM" in resposta.upper():
                screen_width, _ = pyautogui.size()
                # Move para a direita suavemente para não bloquear a leitura
                jarvis_api.smooth_move(screen_width - 340, 20, 0.8)
                # Avisa silenciosamente (manda texto sem falar para não intrudir)
                socketio.emit('transcript', {'text': "ORB Evasivo: Desviando do bloco de leitura..."})

        threading.Thread(target=_evasao, daemon=True).start()
    except Exception as e:
        print(f"[Evasão] Erro: {e}")

# Variável global da janela pywebview (referenciada por J_API antes da criação)
window = None

# ============================================================
# API DA JANELA NATIVA (pywebview JS API)
# Expõe métodos do Python para o JavaScript via window.pywebview.api
# ============================================================
class J_API:
    """API nativa exposta ao JavaScript via pywebview."""

    def get_status(self):
        """Verifica se o servidor está online (usado pelo checkNativeBridge)."""
        return {'status': 'CONECTADO'}

    def sync_ui(self, data):
        """Sincroniza estado enviado da UI."""
        return True

    def toggle_fullscreen(self):
        """Alterna entre tela cheia e janela normal."""
        try:
            global window
            if window:
                window.toggle_fullscreen()
        except Exception as e:
            print(f"[J_API] Erro toggle_fullscreen: {e}")

    def minimize_jarvis(self):
        """Minimiza a janela do Jarvis."""
        try:
            global window
            if window:
                window.minimize()
        except Exception as e:
            print(f"[J_API] Erro minimize_jarvis: {e}")

    def close_jarvis(self):
        """Encerra o Jarvis completamente."""
        try:
            global window
            if window:
                window.destroy()
        except Exception as e:
            print(f"[J_API] Erro close_jarvis: {e}")
        finally:
            os._exit(0)

    def restart_jarvis(self):
        """Reinicia o processo do Jarvis."""
        try:
            global window
            if window:
                window.destroy()
        except Exception as e:
            print(f"[J_API] Erro ao fechar janela para restart: {e}")
        finally:
            # Relança o processo
            os.execv(sys.executable, [sys.executable] + sys.argv)

    def smooth_move(self, target_x, target_y, duration=0.6):
        """Move a janela suavemente (interpolação easeInOut) via Python."""
        def _move():
            global window
            if not window: return
            try:
                start_x = window.x
                start_y = window.y
                # Fix para None
                if start_x is None or start_y is None:
                    window.move(int(target_x), int(target_y))
                    return
                steps = int(duration * 60)
                delay = duration / steps
                for i in range(1, steps + 1):
                    t = i / steps
                    ease_t = 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2
                    now_x = int(start_x + (int(target_x) - start_x) * ease_t)
                    now_y = int(start_y + (int(target_y) - start_y) * ease_t)
                    window.move(now_x, now_y)
                    time.sleep(delay)
            except Exception as e:
                print(f"[SmoothMove] Erro: {e}")
        threading.Thread(target=_move, daemon=True).start()

    def set_orb_mode(self, enabled, target_x=20, target_y=20):
        """Altera dinamicamente o tamanho da janela e move para a posição do ORB."""
        global window
        if not window: return
        try:
            if enabled:
                window.restore() # Tira do maximize
                window.resize(320, 320)
                self.smooth_move(target_x, target_y, duration=0.8)
                # Tenta manter sempre no topo (A interface fluida do Jarvis não deve ficar escondida)
                try: window.on_top = True
                except: pass
            else:
                window.resize(1200, 800)
                try: window.on_top = False
                except: pass
                window.maximize()
        except Exception as e:
            print(f"[OrbMode] Erro ao redimensionar: {e}")

global jarvis_api
jarvis_api = None

def iniciar_gui_desktop():
    """Cria a janela nativa para a interface do Jarvis."""
    global window, jarvis_api
    jarvis_api = J_API()
    api = jarvis_api
    
    # Inicia módulos autônomos de forma silenciosa e segura
    try: iniciar_proatividade()
    except Exception: pass

    # Inicia Leitura Labial Óptica (Fase 7) - opcional
    try:
        from skills.lip_tracker import LipTracker
        LipTracker.get_instance().start()
    except Exception: pass

    try: iniciar_agenda_automatica()
    except Exception: pass

    try: iniciar_rag_automatico()
    except Exception: pass

    # Inicia a Pipeline de Cognição Contínua (FDM-3) - opcional
    try:
        vision_pipeline.start()
    except Exception as e:
        print(f"[GUI] Vision pipeline desativado: {e}")
    
    # Inicia a thread de streaming de tela para o HUD
    def _stream_loop():
        while True:
            try:
                if vision_pipeline.active:
                    latest = vision_pipeline.buffer.get_latest()
                    if latest:
                        img_b64 = imagem_para_base64(latest["path"])
                        if img_b64:
                            socketio.emit('screen_frame', {'image': img_b64})
                time.sleep(0.5) # 2 FPS para economia de banda
            except Exception as e:
                print(f"[Stream HUD] Erro: {e}")
                time.sleep(1)
    
    threading.Thread(target=_stream_loop, daemon=True).start()
    
    # Ativa a porta de depuração para que o Selenium/Playwright possa se conectar e controlar o iframe do NotebookLM (Pilares da Fábrica de Agentes)
    os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--remote-debugging-port=9222"
    
    logging.info(f"Criando janela webview apontando para http://127.0.0.1:5050")
    window = webview.create_window('J.A.R.V.I.S. Core', 'http://127.0.0.1:5050', 
                          width=1200, height=800, 
                          resizable=True, 
                          maximized=True,
                          fullscreen=True,   # Inicia em Tela Cheia
                          frameless=True,    # Remove as bordas do Windows
                          transparent=False,  # TEMPORÁRIO: Desativado para teste de estabilidade
                          easy_drag=False,   # Desativado na raiz para evitar arraste de qualquer canto
                          js_api=api,
                          background_color='#050a0f')
    
    logging.info("Chamando webview.start()...")
    webview.start()
    logging.info("webview.start() retornou (Janela fechada).")

def main_loop():
    while True:
        try:
            # FASE 1 — Modo passivo: aguarda wake word
            print("\n[Em espera... diga 'Jarvis' para ativar]")
            texto_apos_wake = aguardar_wake_word()

            # Ativado!
            print("\n[MODO ATIVO - Conversa Iniciada]", flush=True)
            
            continuar_conversa = True
            if texto_apos_wake:
                print(f"[DEBUG] Comando imediato identificado: {texto_apos_wake}", flush=True)
                # O comando veio junto com o "Jarvis" (ex: "Jarvis, que horas são?")
                continuar_conversa = processar_comando(texto_apos_wake)
            else:
                print("[DEBUG] Respondendo à Wake Word...", flush=True)
                falar("Sim, senhor?")

            # MODO DE CONVERSA CONTÍNUA
            while continuar_conversa:
                print("\n[DEBUG] Entrando em loop de escuta contínua...", flush=True)
                # Ouve o próximo comando sem precisar da wake word (permite espera de até 15s antes de Timeout)
                comando = ouvir(timeout=15, frase_limite=25)
                
                if comando:
                    print(f"[DEBUG] Comando recebido: {comando}", flush=True)
                    continuar_conversa = processar_comando(comando)
                else:
                    print("[DEBUG] Nenhum comando detectado ou timeout.", flush=True)
                    # Se não ouviu nada (timeout), encerra a sessão ativa
                    print("[Sessão encerrada por inatividade]", flush=True)
                    falar("Ficarei em espera, senhor.")
                    continuar_conversa = False

        except KeyboardInterrupt:
            break
        except SystemExit:
            break
        except Exception as e:
            print(f"[Erro inesperado no loop: {e}]")
            continue

if __name__ == "__main__":
    # 1. Elevação de privilégios (DEVE ser a primeira coisa)
    re_launch_as_admin()

    try:
        # ── FASE 1: Servidor Web ───────────────────────────────────
        kill_port_5050()
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # ── FASE 2: Threads de Background ─────────────────────────
        tts_thread.start()
        threading.Thread(target=pc_health_broadcaster, daemon=True).start()
        threading.Thread(target=internet_monitor_loop, daemon=True).start()

        print("=" * 60, flush=True)
        print("  J.A.R.V.I.S - Carregando Sistema...", flush=True)
        print("=" * 60, flush=True)

        disable_quick_edit()
        iniciar_servico_gestos()

        # ── FASE 3: Aguarda servidor Flask estabilizar ─────────────
        print("[CARREGAMENTO] Aguardando servidor Flask (3s)...", flush=True)
        time.sleep(3)

        # ── FASE 4: Calibração do Microfone ───────────────────────
        print("[CARREGAMENTO] Calibrando microfone...", flush=True)
        try:
            calibrar_microfone()
            print("[CARREGAMENTO] Microfone OK.", flush=True)
        except Exception as e:
            print(f"[AVISO] Calibração falhou: {e}", flush=True)

        # ── FASE 5: Pré-aquecimento do Motor de Voz (XTTS/Edge) ───
        print("[CARREGAMENTO] Inicializando motor de voz...", flush=True)
        usa_xtts = os.path.exists("jarvis_referencia.wav") or os.path.exists("jarvis_referencia.wav.wav")
        
        if usa_xtts:
            print("[CARREGAMENTO] Voz clonada ativa. Carregando XTTS-v2...", flush=True)
            print("[CARREGAMENTO] (Aguarde 1-2 minutos no primeiro uso)", flush=True)
        
        try:
            falar("Sistemas online, senhor.")
            tts_queue.join()  # Bloqueia até o áudio terminar
            print("[CARREGAMENTO] Motor de voz: OK.", flush=True)
        except Exception:
            print("[AVISO] Falha no motor de voz principal. Usando fallback.", flush=True)

        # ── FASE 6: Loop Principal em Background ──────────────────
        threading.Thread(target=lambda: (time.sleep(2), main_loop()), daemon=True).start()

        # ── FASE 7: Abre a GUI — TUDO JÁ ESTÁ CARREGADO ──────────
        print("=" * 60, flush=True)
        print("  J.A.R.V.I.S - Sistema Pronto! Abrindo interface...", flush=True)
        print("=" * 60, flush=True)

        iniciar_gui_desktop()

    except Exception as e:
        err_msg = traceback.format_exc()
        print(f"\n[FALHA FATAL] {e}\n{err_msg}")
        input("\nPressione Enter para sair...")

