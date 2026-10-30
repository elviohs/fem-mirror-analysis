@echo off
chcp 65001 >nul
REM Lanza la interfaz grafica de analisis FEM de espejo
REM El script debe estar en la misma carpeta que este .bat
REM Requiere Python 3.9+ con numpy, scipy, matplotlib y python-docx (informes).
REM Si no los tienes, ejecuta primero: instalar_dependencias.bat

python "%~dp0gui_fem_mirror.py"
pause
