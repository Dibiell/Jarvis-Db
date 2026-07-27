@echo off
echo ========================================================
echo CORRECAO DE CONFLITO DE PACOTES (Numpy / OpenCV)
echo ========================================================
echo.
call venv\Scripts\activate.bat
echo Ajustando biblioteca matematica Numpy para compatibilidade universal...
pip install "numpy>=1.22.5,<2.0.0"
echo.
echo Ajustando Camera (OpenCV) para suportar o Numpy seguro...
pip install opencv-python==4.10.0.84 opencv-contrib-python==4.10.0.84
echo.
echo ========================================================
echo CONFLITOS RESOLVIDOS!
echo Pode fechar esta tela e ligar o Jarvis!
echo ========================================================
pause
