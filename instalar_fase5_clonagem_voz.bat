@echo off
echo ========================================================
echo INSTALADOR FASE 5 - CLONAGEM DE VOZ (XTTS-v2) J.A.R.V.I.S
echo ========================================================
echo.
echo Iniciando ambiente virtual e baixando modulos de inteligencia...
echo Atencao: Este processo vai baixar cerca de 2GB a 3GB (PyTorch + Motor TTS).
echo Pode demorar alguns minutos dependendo da sua internet!
echo.
call venv\Scripts\activate.bat
echo [Passo 1/2] Instalando PyTorch CUDA...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
echo [Passo 2/2] Instalando Coqui TTS e dependencias de audio...
pip install TTS soundfile torchcodec
echo.
echo ========================================================
echo INSTALACAO CONCLUIDA! 
echo.
echo Feche o CMD, certifique-se de que o jarvis_referencia.wav 
echo esta na pasta e abra o Jarvis-Assistant normalmente!
echo ========================================================
pause
