@echo off
echo ========================================================
echo INSTALADOR FASE 7 - J.A.R.V.I.S (LIP-READING E VISAO 3D)
echo ========================================================
echo.
echo Iniciando ambiente virtual e baixando modulos de inteligencia de video (OpenCV + MediaPipe)...
echo.
call venv\Scripts\activate.bat
pip install opencv-python mediapipe
echo.
echo ========================================================
echo INSTALACAO CONCLUIDA! VOCE PODE REINICIAR O JARVIS AGORA.
echo ========================================================
pause
