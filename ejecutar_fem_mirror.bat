@echo off
chcp 65001 >nul
REM Analisis FEM de superficie de espejo (modo consola)
REM El script debe estar en la misma carpeta que este .bat
REM Requiere Python 3.9+ con numpy, scipy y matplotlib instalados.

REM ── PARAMETROS A EDITAR ─────────────────────────────────────────────

REM Fichero de datos FEM (nodo X Y Z dX dY dZ)
set DATOS="ruta\a\tu\fichero.TXT"

REM Modos de solido rigido a eliminar: Tx Ty Tz Rx Ry Rz  (0=no, 1=si)
set RIGID=0 0 1 0 0 0

REM Apertura: circular, square, rectangular, hexagonal
set APERTURA=hexagonal

REM Numero de terminos de Zernike (0 = solo RMS)
set TERMS=3

REM Normalizacion: pico o rms
set NORM=pico

REM ────────────────────────────────────────────────────────────────────

python "%~dp0fem_mirror_analysis.py" %DATOS% ^
    --rigid %RIGID% ^
    --aperture %APERTURA% ^
    --terms %TERMS% ^
    --norm %NORM% ^
    --plot

pause
