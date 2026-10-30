# FEM Mirror Surface Analysis

Herramienta Python para el análisis de superficies de espejos a partir de resultados de simulaciones de elementos finitos (FEM). Permite calcular RMS, PV, ajuste de polinomios de Zernike, Strehl y PSF, tolerancias de forma ISO 10110-5 y combinaciones de casos de carga, con una interfaz gráfica interactiva y vista 3D de la deformación.

## Características

- **Interfaz gráfica** (GUI tkinter) con paneles de configuración, log de resultados y figura embebida
- **Modo consola** para integración en flujos de trabajo automatizados
- Eliminación de modos de **sólido rígido** (Tx, Ty, Tz, Rx, Ry, Rz) configurables
- **Ajuste polinómico WLS ponderado por área** (como SurfCalc), normalización pico o RMS, con tabla de coeficientes e índice SurfCalc equivalente
- **Aperturas y bases**:
  - circular → Zernike, convención **Fringe** o **Noll**
  - anular → **Zernike anulares de Mahajan** (1981), con obscuración detectada de la malla
  - hexagonal → **ortonormales hexagonales de Mahajan–Dai** (2006), vértices en ±X o ±Y
  - rectangular (y cuadrada) → **ortonormales rectangulares de Mahajan–Dai** (2007)
- **Error de superficie**: cambio de sag Δz (recomendado en espejos curvos, incluye el movimiento en el plano) o desplazamiento normal u·n
- **Aporte RMS de cada término**, independiente del número de términos ajustados, y RMS/PV residual acumulado
- Sistema de referencia **global** (Z = eje óptico) o **plano best-fit**
- Áreas nodales sin triángulos falsos sobre huecos o entrantes del contorno
- Ficheros con **varios casos de carga** apilados (1ª columna = nº de caso)
- Cálculo de **RMS**, **RMS respecto a la media** y **PV** sobre la apertura
- **Calidad óptica**: error de frente de onda en reflexión (2·cosθ·superficie) con λ y ángulo de incidencia configurables, **Strehl** por Maréchal y numérico, y **PSF** por FFT en unidades de λ/D
- **ISO 10110-5:2015**: potencia (A), irregularidad (B), irregularidad rotacionalmente invariante (C), RMSt, RMSi, RMSa y PV robusto (PVr), notación `3/A(B/C) RMSx < D` y comprobación frente a una tolerancia
- **Combinación de casos de carga** calculados con la misma malla: gravedad a cualquier ángulo de elevación a partir de casos a ángulos distintos, u(θ) = cosθ·A + sinθ·B (+C), con comprobación de linealidad y barrido de RMS/PV; o combinación lineal Σ cₖ·uₖ
- **Vista 3D interactiva** de la superficie de deformación con escala Z configurable
- **Informe Word** (español o inglés) con los mapas de la superficie sin sólido rígido y del residuo, RMS, máximo, mínimo, PV, términos eliminados, calidad óptica, tabla ISO 10110-5 y observaciones automáticas
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

La GUI permite cargar el fichero de datos FEM, configurar los parámetros y ejecutar el análisis con un clic. En el bloque **Calidad óptica e ISO 10110-5** se indican las unidades del fichero, la longitud de onda, el ángulo de incidencia y, opcionalmente, una tolerancia ISO a comprobar. Tras el análisis, el botón 🎨 **Vista 3D** abre una ventana interactiva con la superficie de deformación, y el botón 📄 **Generar informe** crea un documento Word en el idioma seleccionado.

El botón **Combinar casos…** abre una ventana para combinar casos FEM con la misma malla (por ejemplo gravedad a 0° y 45°): genera el fichero del caso combinado a un ángulo dado (absoluto o respecto a un ángulo de referencia), lo analiza con los ajustes de la ventana principal y dibuja el barrido de RMS/PV frente al ángulo.

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

`--nterms N` ajusta los N primeros términos de la base (igual que la GUI); `--terms` permite elegir índices concretos (Fringe 0-based; Noll y bases anular, hexagonal y rectangular 1-based). `python fem_mirror_analysis.py --list-terms --convention noll` muestra la tabla de términos.

Calidad óptica e ISO 10110-5:

```bash
python fem_mirror_analysis.py datos.TXT --nterms 4 --units mm \
    --wavelength 632.8 --incidence 0 \
    --iso-spec "3/900 nm (250 nm/100 nm) RMSi < 30 nm"
```

Combinación de casos de gravedad (misma malla; `ruta::caso` para ficheros con varios casos):

```bash
python fem_mirror_analysis.py --gravity g0.TXT 0 --gravity g45.TXT 45 \
    --elevation 60 --ref-elevation 0 --sweep 0 90 15 --save-combined g60.TXT
```

Con tres o más casos, `--constant` añade un término constante (precargas, montaje) y el programa informa del desajuste de linealidad de cada caso. `--combine FICHERO COEF` (repetible) calcula una combinación lineal.

### Notas sobre ISO 10110-5

- Las magnitudes son de **superficie** en nm (1 fringe spacing = λ/2).
- Funciones de ISO 14999-4:2007: tilt = plano best-fit (incluye pistón); RMS = integral sobre la apertura (aquí ponderada por área nodal).
- La esfera best-fit se aproxima paraxialmente por el término ρ² (se avisa si la superficie es rápida), la parte rotacionalmente invariante (óptimo rms = media azimutal) por un ajuste de polinomios pares en ρ, y el PVr según Evans (Opt. Eng. 48(4), 2009) con los 37 términos Zernike Fringe que recomienda ISO 14999-4. ISO 10110-5:2015 limita el PVr a aperturas circulares; en las demás se calcula y se marca como fuera de norma.
- PV% (PV recortado) aún no implementado.
- La norma define la desviación de forma normal a la superficie; con «cambio de sag» los valores son desviación de sagita ΔZ. En espejos planos coinciden.
- No se evalúan las formas cilíndricas/tóricas (AX;AY, CX;CY), las pendientes ΔS con longitud de muestreo, los campos de prueba «(all …)» ni las tolerancias de coeficientes Z(n,m).

## Formato del fichero de datos

El fichero de entrada debe ser un fichero de texto con columnas separadas por espacios o tabuladores:

```
ID   X   Y   Z   dX   dY   dZ
```

donde `X`, `Y`, `Z` son las coordenadas del nodo y `dX`, `dY`, `dZ` los desplazamientos FEM. Si la primera columna se repite se interpreta como número de caso de carga. Las líneas que empiezan por `#` se ignoran.

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
