import math
import time
import threading

class LipTracker:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LipTracker()
        return cls._instance
        
    def __init__(self):
        self.is_speaking = False
        self.is_running = False
        self.thread = None
        self._last_open_time = 0
        self.threshold = 0.05  # MAR (Mouth Aspect Ratio) threshold 
        
    def start(self):
        if self.is_running: return
        self.is_running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print("[LipTracker] Sistema Óptico de Lábios Iniciado...")
        
    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join()
            
    def _run(self):
        try:
            import mediapipe as mp
            from mediapipe.python.solutions import face_mesh as mp_face_mesh
            import cv2
        except ImportError:
            print("[LipTracker] MediaPipe ou OpenCV não encontrados. Instale-os se desejar usar leitura labial.")
            return
            
        cap = cv2.VideoCapture(0)
        
        # Verifica se câmera abriu
        if not cap.isOpened():
            print("[LipTracker] Erro ao abrir a Câmera 0.")
            return

        with mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5) as face_mesh:
            
            while self.is_running and cap.isOpened():
                success, image = cap.read()
                if not success:
                    time.sleep(0.1)
                    continue
                
                image.flags.writeable = False
                # Conversão para RGB é mais rápida que BGR para o MediaPipe processar
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(image)
                
                current_speaking = False
                if results.multi_face_landmarks:
                    for face_landmarks in results.multi_face_landmarks:
                        # Pontos chaves da boca (Inner Lips)
                        p13 = face_landmarks.landmark[13] # Topo interno
                        p14 = face_landmarks.landmark[14] # Baixo interno
                        p78 = face_landmarks.landmark[78] # Esquerdo
                        p308 = face_landmarks.landmark[308] # Direito
                        
                        vertical_dist = math.hypot(p13.x - p14.x, p13.y - p14.y)
                        horizontal_dist = math.hypot(p78.x - p308.x, p78.y - p308.y)
                        
                        if horizontal_dist > 0:
                            mar = vertical_dist / horizontal_dist
                            # Se a boca tiver MAR elevado, está aberta (falando)
                            if mar > self.threshold:
                                current_speaking = True
                
                if current_speaking:
                    self._last_open_time = time.time()
                    self.is_speaking = True
                else:
                    # Trava visual: só considera silêncio se a boca estiver fechada por 0.6s
                    # Evita falsos positivos como o usuário molhando os lábios rapidamente
                    if time.time() - self._last_open_time > 0.6:
                        self.is_speaking = False
                
                # Executa ~30FPS para economizar GPU/CPU
                time.sleep(0.03)
        
        cap.release()
