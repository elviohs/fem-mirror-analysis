@echo off
chcp 65001 >nul
REM Analisis FEM de superficie de espejo (modo consola)
REM El script debe estar en la misma carpeta que este .bat
REM Requiere Python 3.9+ con numpy, scipy y matplotlib instalados.

REM ── PARAMETROS A EDITAR ─────────────────────────────────────────────

REM Fichero de datos FEM (nodo X Y Z dX dY dZ  o  X Y Z dX dY dZ)
set DATOS="ruta\a\tu\fichero.TXT"

REM Modos de solido rigido a eliminar: Tx Ty Tz Rx Ry Rz  (0=no, 1=si)
set RIGID=0 0 1 0 0 0

REM Apertura: circular (Zernike) o rectangular (Chebyshev)
REM (annular y hexagonal: pendientes de implementar)
set APERTURA=circular

REM Convencion de Zernike (solo apertura circular): fringe o noll
set CONVENCION=fringe

REM Numero de terminos a ajustar (los N primeros de la base; 0 = solo RMS)
set NTERMS=3

REM Normalizacion: pico o rms
set NORM=pico

REM Sistema de referencia: global (Z = eje optico) o bestfit
set FRAME=global

REM Si el fichero tiene varios casos de carga apilados, anade:  --case N

REM ────────────────────────────────────────────────────────────────────

python "%~dp0fem_mirror_analysis.py" %DATOS% ^
    --rigid %RIGID% ^
    --aperture %APERTURA% ^
    --convention %CONVENCION% ^
    --nterms %NTERMS% ^
    --norm %NORM% ^
    --frame %FRAME% ^
    --plot

pause
