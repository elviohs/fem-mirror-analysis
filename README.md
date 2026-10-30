# FEM Mirror Surface Analysis

Herramienta Python para el análisis de superficies de espejos a partir de resultados de simulaciones de elementos finitos (FEM). Permite calcular RMS, PV, ajuste de polinomios de Zernike y simulación de PSF, con una interfaz gráfica interactiva y vista 3D de la deformación.

## Características

- **Interfaz gráfica** (GUI tkinter) con paneles de configuración, log de resultados y figura embebida
- **Modo consola** para integración en flujos de trabajo automatizados
- Eliminación de modos de **sólido rígido** (Tx, Ty, Tz, Rx, Ry, Rz) configurables
- **Ajuste polinómico WLS ponderado por área** (como SurfCalc), normalización pico o RMS, con tabla de coeficientes e índice SurfCalc equivalente
- **Aperturas y bases**:
  - circular → Zernike, convención **Fringe** o **Noll**
  - rectangular → **Chebyshev 2D** Tᵢ(x)·Tⱼ(y), ordenación triangular
  - anular (Zernike de Mahajan) y hexagonal (polinomios de segmento) → pendientes
- Sistema de referencia **global** (Z = eje óptico) o **plano best-fit**
- Ficheros con **varios casos de carga** apilados (1ª columna = nº de caso)
- Cálculo de **RMS**, **RMS respecto a la media** y **PV** sobre la apertura
- Simulación de **PSF** (Point Spread Function) por transformada de Fourier
- **Vista 3D interactiva** de la superficie de deformación con escala Z configurable
- **Informe Word** (español o inglés) con los mapas de la superficie sin sólido rígido y del residuo, RMS, máximo, mínimo, PV, términos eliminados y observaciones automáticas
- Coordenadas + valor interpolado al pasar el ratón por encima de los gráficos

## Requisitos

- Python 3.9 o superior
- numpy
- scipy
- matplotlib
- python-docx (solo para los informes Word)

Instalación rápida de dependencias en Windows:

```
instalar_dependencias.bat
```

O directamente:

```bash
pip install numpy scipy matplotlib python-docx
```

## Uso

### Interfaz gráfica (recomendado)

```
ejecutar_gui_fem.bat
```

O directamente:

```bash
python gui_fem_mirror.py
```

La GUI permite cargar el fichero de datos FEM, configurar los parámetros y ejecutar el análisis con un clic. Tras el análisis, el botón 🎨 **Vista 3D** abre una ventana interactiva con la superficie de deformación, y el botón 📄 **Generar informe** crea un documento Word en el idioma y unidades seleccionados.

### Modo consola

Edita los parámetros en `ejecutar_fem_mirror.bat` y ejecútalo, o llama directamente:

```bash
python fem_mirror_analysis.py datos.TXT \
    --rigid 1 1 1 1 1 1 \
    --aperture circular --convention noll \
    --nterms 5 \
    --norm pico \
    --plot
```

`--nterms N` ajusta los N primeros términos de la base (igual que la GUI); `--terms` permite elegir índices concretos (Fringe y Chebyshev 0-based, Noll 1-based). `python fem_mirror_analysis.py --list-terms --convention noll` muestra la tabla de términos.

## Formato del fichero de datos

El fichero de entrada debe ser un fichero de texto con columnas separadas por espacios o tabuladores:

```
ID   X   Y   Z   dX   dY   dZ
```

donde `X`, `Y`, `Z` son las coordenadas del nodo y `dX`, `dY`, `dZ` los desplazamientos FEM. El análisis trabaja con el desplazamiento normal a la superficie (`dZ` por defecto).

## Estructura del repositorio

```
├── gui_fem_mirror.py          # Interfaz gráfica principal
├── fem_mirror_analysis.py     # Motor de análisis (también ejecutable en consola)
├── report_fem_mirror.py       # Generación de informes Word (ES/EN)
├── ejecutar_gui_fem.bat       # Acceso rápido a la GUI (Windows)
├── ejecutar_fem_mirror.bat    # Acceso rápido al modo consola (Windows)
└── instalar_dependencias.bat  # Instalador de dependencias (Windows)
```

## Origen

Desarrollado en el [Instituto de Astrofísica de Canarias (IAC)](https://www.iac.es) para el análisis de superficies de espejos en el contexto de proyectos de instrumentos astrofísicos.
