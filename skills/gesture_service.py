import cv2
import mediapipe as mp
import socketio
import numpy as np
import time
from collections import deque
import math

# --- Configurações ---
sio = socketio.Client()
HISTORY_LENGTH = 16

class EliteGestureService:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.8,
            min_tracking_confidence=0.8
        )
        self.point_history = deque(maxlen=HISTORY_LENGTH)
        self.finger_gesture_history = deque(maxlen=HISTORY_LENGTH)
        self.cap = None
        self.running = False
        
        # Estados de Gesto
        self.is_grabbing = False
        self.last_pinch_dist = 0.0
        self.gesture_cooldown = 0.4
        self.last_emit_time = 0.0

    def pre_process_landmark(self, landmarks, width, height):
        """Padrão Kazuhito00: Coordenadas relativas ao pulso e normalizadas."""
        landmark_list = []
        for lm in landmarks.landmark:
            landmark_list.append([lm.x * width, lm.y * height])
            
        # Converter para relativo ao pulso (index 0)
        base_x, base_y = landmark_list[0][0], landmark_list[0][1]
        relative_list = []
        for x, y in landmark_list:
            relative_list.append([x - base_x, y - base_y])
            
        # Normalizar pela distância máxima (escala invariante)
        flat_list = [abs(val) for sublist in relative_list for val in sublist]
        max_val = max(flat_list) if flat_list and max(flat_list) > 0 else 1.0
        
        return [[p[0]/max_val, p[1]/max_val] for p in relative_list]

    def detect_dynamic_gesture(self):
        """Analisa o histórico de pontos para detectar Swipes (Deslizar)."""
        if len(self.point_history) < HISTORY_LENGTH:
            return "NONE"
            
        # Vetor do primeiro ao último ponto do histórico
        first = self.point_history[0]
        last = self.point_history[-1]
        
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        
        # Threshold de movimento
        if abs(dx) > 0.15: # Movimento horizontal significativo
            return "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
        
        return "NONE"

    def identify_static_sign(self, landmarks):
        """Identifica sinais estáticos baseados em distâncias normalizadas."""
        # 0: Wrist, 4: Thumb, 8: Index, 12: Middle, 16: Ring, 20: Pinky
        dist = lambda p1, p2: math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        
        d_thumb_index = dist(landmarks[4], landmarks[8])
        
        # Distâncias à palma (ponto 0)
        d_idx = dist(landmarks[8], landmarks[0])
        d_mid = dist(landmarks[12], landmarks[0])
        d_rng = dist(landmarks[16], landmarks[0])
        d_pnk = dist(landmarks[20], landmarks[0])
        
        avg_fingers = (d_idx + d_mid + d_rng + d_pnk) / 4

        # 1. PINCH (Pinça) -> Thumb e Index colados
        if d_thumb_index < 0.1:
            return "PINCH", d_thumb_index
            
        # 2. FIST (Punho) -> Todos os dedos perto do pulso
        if avg_fingers < 0.35:
            return "FIST", 0.0
            
        # 3. 3-FINGERS -> Index, Middle, Ring estendidos, Pinky dobrado
        if d_idx > 0.6 and d_mid > 0.6 and d_rng > 0.6 and d_pnk < 0.4:
            return "3-FINGERS", 0.0
            
        # 4. VICTORY (V) -> Index e Middle
        if d_idx > 0.6 and d_mid > 0.6 and d_rng < 0.4 and d_pnk < 0.4:
            return "VICTORY", 0.0
            
        # 5. PALM (Mão Aberta)
        if avg_fingers > 0.6:
            return "PALM", 0.0
            
        return "NONE", 0.0

    def start(self):
        self.cap = cv2.VideoCapture(0)
        self.running = True
        print("[ELITE GESTURES] Sistema Kazuhito-Pattern Ativo.")

        while self.running:
            if self.cap is None: break
            success, frame = self.cap.read()
            if not success: break
            
            frame = cv2.flip(frame, 1) # Espelhar para ficar natural
            h, w, _ = frame.shape
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(img_rgb)

            if results.multi_hand_landmarks:
                for hand_lms in results.multi_hand_landmarks:
                    # Pre-processamento Elite
                    norm_lms = self.pre_process_landmark(hand_lms, w, h)
                    
                    # 1. Identificar sinal estático (Fist, Pinch, etc)
                    sign, val = self.identify_static_sign(norm_lms)
                    
                    # Adiciona ao histórico do indicador (ponto 8) para gestos dinâmicos
                    self.point_history.append(norm_lms[8])
                    dynamic = self.detect_dynamic_gesture()
                    
                    # Lógica de Emissão
                    now = time.time()
                    if now - self.last_emit_time > self.gesture_cooldown:
                        emit_gesture = None
                        
                        if dynamic != "NONE":
                            emit_gesture = dynamic
                            self.point_history.clear() # Limpa após detectar swipe
                        elif sign != "NONE":
                            # Lógica especial de Drag & Drop
                            if sign == "FIST":
                                if not self.is_grabbing:
                                    self.is_grabbing = True
                                    sio.emit('gesture_event', {'gesture': 'GRAB_START', 'x': hand_lms.landmark[9].x, 'y': hand_lms.landmark[9].y})
                            elif sign == "PALM" and self.is_grabbing:
                                self.is_grabbing = False
                                sio.emit('gesture_event', {'gesture': 'GRAB_END'})
                            
                            # Lógica especial de Zoom dinâmico
                            if sign == "PINCH":
                                if self.last_pinch_dist > 0:
                                    diff = val - self.last_pinch_dist
                                    if abs(diff) > 0.01:
                                        sio.emit('gesture_event', {'gesture': 'ZOOM', 'delta': diff})
                                self.last_pinch_dist = val
                            else:
                                self.last_pinch_dist = 0.0
                                
                            emit_gesture = sign
                        
                        if emit_gesture:
                            print(f"[ELITE] Gesto: {emit_gesture}")
                            sio.emit('gesture_event', {'gesture': emit_gesture})
                            self.last_emit_time = now

            # cv2.imshow("Jarvis Gesture Vision", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            time.sleep(0.01)

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()

@sio.event
def connect(): print("[ELITE] Conectado ao Jarvis Engine.")

if __name__ == "__main__":
    service = EliteGestureService()
    try:
        sio.connect('http://localhost:5000')
        service.start()
    except Exception as e: print(f"[ERRO ELITE] {e}")
