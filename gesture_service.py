import cv2
import mediapipe as mp
import numpy as np
import socketio
import time
import argparse
from collections import deque
import copy
import itertools

# ============================================================
# ELITE GESTURE SERVICE (FDM-1 V2.0)
# Baseado nos padrões de Kazuhito00 para Máxima Precisão
# ============================================================

class EliteGestureService:
    def __init__(self, server_url="http://localhost:5000"):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.sio = socketio.Client()
        self.server_url = server_url
        
        # Histórico de Pontos (Poder do Oponente - Kazuhito00)
        self.history_length = 16
        self.point_history = deque(maxlen=self.history_length)
        
        # Estado de Gestos
        self.last_gesture_time = 0
        self.cooldown = 1.0 # 1 segundo entre gestos de comando
        
        # Tracking do Grab/Drag
        self.is_grabbing = False
        
        # Tracking do Zoom
        self.last_pinch_dist = 0

    def connect(self):
        try:
            self.sio.connect(self.server_url)
            print(f"[Gestos] Conectado ao HUD em {self.server_url}")
        except Exception as e:
            print(f"[Gestos] Erro ao conectar: {e}")

    def pre_process_landmarks(self, landmark_list):
        temp_landmark_list = copy.deepcopy(landmark_list)
        # Converter para coordenadas relativas ao pulso
        base_x, base_y = 0, 0
        for index, landmark in enumerate(temp_landmark_list):
            if index == 0:
                base_x, base_y = landmark[0], landmark[1]
            temp_landmark_list[index][0] = temp_landmark_list[index][0] - base_x
            temp_landmark_list[index][1] = temp_landmark_list[index][1] - base_y
        # Normalização (Escala Invariante)
        max_value = max(list(map(lambda x: abs(max(x)), temp_landmark_list)))
        def normalize_(n): return n / max_value
        temp_landmark_list = list(map(lambda x: list(map(normalize_, x)), temp_landmark_list))
        return list(itertools.chain.from_iterable(temp_landmark_list))

    def get_finger_status(self, hand_landmarks):
        """Retorna quais dedos estão abertos (True/False)."""
        tips = [8, 12, 16, 20] # Indicador, Médio, Anelar, Mínimo
        status = []
        # Polegar (lógica de X para lateralidade)
        status.append(hand_landmarks[4].x < hand_landmarks[3].x)
        # Outros dedos (lógica de Y)
        for tip in tips:
            status.append(hand_landmarks[tip].y < hand_landmarks[tip - 2].y)
        return status

    def calc_distance(self, p1, p2):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

    def run(self, headless=True):
        cap = cv2.VideoCapture(0)
        print("[Gestos] Câmera Ativada (Background Mode).")
        
        while cap.isOpened():
            success, image = cap.read()
            if not success: continue

            image = cv2.flip(image, 1)
            debug_image = copy.deepcopy(image)
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.hands.process(image_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # 1. Pega status dos dedos
                    fingers = self.get_finger_status(hand_landmarks)
                    num_fingers = sum(fingers)
                    
                    # 2. Histórico do Ponto (Indicador)
                    index_tip = hand_landmarks[8]
                    self.point_history.append([index_tip.x, index_tip.y])
                    
                    # 3. Detectar Swipes (Movimento rápido lateral)
                    now = time.time()
                    if now - self.last_gesture_time > self.cooldown:
                        if len(self.point_history) == self.history_length:
                            dx = self.point_history[-1][0] - self.point_history[0][0]
                            # Swipe detectado se o movimento em X for grande e rápido
                            if abs(dx) > 0.3:
                                gesture = "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"
                                self.sio.emit('gesture_event', {'gesture': gesture})
                                self.last_gesture_time = now
                                print(f"[Gestos] {gesture} detectado!")

                    # 4. GESTOS ESTÁTICOS ELITE
                    # --- PINCH (Zoom) ---
                    dist = self.calc_distance(hand_landmarks[4], hand_landmarks[8])
                    if fingers[0] and fingers[1] and not any(fingers[2:]):
                        if dist < 0.05:
                            # Pinch Ativo
                            if self.last_pinch_dist > 0:
                                delta = dist - self.last_pinch_dist
                                self.sio.emit('gesture_event', {'gesture': 'ZOOM', 'delta': delta})
                            self.last_pinch_dist = dist
                        else:
                            self.last_pinch_dist = 0
                    
                    # --- 3-FINGERS (Minimizar) ---
                    if num_fingers == 3 and not fingers[4] and fingers[1] and fingers[2] and fingers[3]:
                        if now - self.last_gesture_time > self.cooldown:
                            self.sio.emit('gesture_event', {'gesture': '3-FINGERS'})
                            self.last_gesture_time = now
                    
                    # --- VICTORY (Visão) ---
                    if num_fingers == 2 and fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
                         if now - self.last_gesture_time > self.cooldown:
                            self.sio.emit('gesture_event', {'gesture': 'VICTORY'})
                            self.last_gesture_time = now

                    # --- GRAB (Fist) vs RELEASE (Palm) ---
                    if num_fingers == 0 and not self.is_grabbing:
                        self.is_grabbing = True
                        self.sio.emit('gesture_event', {'gesture': 'GRAB_START', 'x': index_tip.x, 'y': index_tip.y})
                    elif num_fingers >= 4 and self.is_grabbing:
                        self.is_grabbing = False
                        self.sio.emit('gesture_event', {'gesture': 'GRAB_END'})

                    # --- FIST / PALM Simple Notifs ---
                    if num_fingers == 0:
                        self.sio.emit('gesture_event', {'gesture': 'FIST'})
                    elif num_fingers == 5:
                        self.sio.emit('gesture_event', {'gesture': 'PALM'})

            if not headless:
                cv2.imshow('JARVIS Hand Tracking (DEBUG)', debug_image)
                if cv2.waitKey(5) & 0xFF == 27: break

        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true", help="Mostrar janela de debug da câmera")
    args = parser.parse_args()
    
    service = EliteGestureService()
    service.connect()
    service.run(headless=not args.gui)
