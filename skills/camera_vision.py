"""
JARVIS SKILL: Camera Vision
Permite que o Jarvis "veja" e descreva o ambiente físico através da webcam
usando OpenCV e APIs de visão computacional (Groq / OpenAI).
"""

import cv2
import os
import tempfile
import datetime
import base64

def capturar_camera(camera_index=0):
    """
    Captura um frame da webcam e retorna o path do arquivo temp.
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("[Camera] Erro: Não foi possível abrir a câmera.")
            return None
        
        # Tenta capturar alguns frames para ajustar o brilho (warm-up)
        for _ in range(5):
            cap.read()
            
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("[Camera] Erro ao ler frame da câmera.")
            return None
            
        # Salva em arquivo temporário
        tmp_path = os.path.join(
            tempfile.gettempdir(),
            f"jarvis_cam_{datetime.datetime.now().strftime('%H%M%S')}.jpg"
        )
        cv2.imwrite(tmp_path, frame)
        print(f"[Camera] Frame salvo em: {tmp_path}")
        return tmp_path
        
    except Exception as e:
        print(f"[Camera] Erro ao capturar câmera: {e}")
        return None

def imagem_para_base64(image_path):
    """Converte um arquivo de imagem para string Base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except Exception as e:
        print(f"[Camera] Erro ao converter imagem para base64: {e}")
        return None

def ver_camera_jarvis(pergunta="O que você está vendo?", camera_index=0):
    """
    Captura a câmera e envia para análise de visão.
    """
    img_path = capturar_camera(camera_index)
    if not img_path:
        return "Não consegui acessar sua câmera, senhor. Ela pode estar sendo usada por outro aplicativo."
        
    try:
        img_b64 = imagem_para_base64(img_path)
        if not img_b64:
            return "Falha ao processar a imagem da câmera."
            
        prompt_sistema = (
            "Você é o sistema de visão ocular do J.A.R.V.I.S. "
            "Você está vendo através da webcam do seu mestre. "
            "Descreva o ambiente, objetos, pessoas ou qualquer coisa relevante que o usuário perguntar. "
            "Seja preciso, sofisticado e útil. Responda em português do Brasil."
        )
        
        mensagem_visao = {
            "role": "user",
            "content": [
                {"type": "text", "text": pergunta},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }
        
        from brain.llm.router import router as llm_router
        try:
            print("[Camera] Enviando imagem para o LLMRouter...")
            messages = [{"role": "system", "content": prompt_sistema}, mensagem_visao]
            resposta = llm_router.chat(messages=messages)
            resultado = resposta.get("text", "")
            if resultado:
                print("[Camera] LLMRouter respondeu com sucesso.")
            else:
                print("[Camera] LLMRouter retornou vazio.")
                resultado = None
        except Exception as e:
            print(f"[Camera] LLMRouter falhou na visão: {e}")
            resultado = None
            
        return resultado or "Estou vendo a imagem da sua câmera, mas meus módulos de análise falharam, Senhor."
        
    finally:
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except:
                pass
