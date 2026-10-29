#!/usr/bin/env python3
"""
fem_mirror_analysis.py
======================
Análisis de desplazamientos de superficie de espejo a partir de resultados FEM.

Portado de las rutinas MATLAB: extract_rigid.m, zerfit.m, zernike.m,
zernikeISO2nm.m  (MatlabToolsJCL, IAC / JCL)


FORMATO DEL FICHERO DE ENTRADA TXT
===================================
El fichero de texto debe contener una línea por nodo FEM con los siguientes
campos separados por espacios o tabuladores:

    node_id   X   Y   Z   dX   dY   dZ

  - node_id : Entero. Identificador del nodo (no se usa en el análisis).
  - X, Y, Z : Coordenadas de posición del nodo en el sistema global (mm típicamente).
              El eje Z debe ser el eje óptico (normal al espejo en reposo).
  - dX, dY, dZ : Desplazamientos elásticos del nodo bajo la carga analizada (mismas
                 unidades que X Y Z).

Ejemplo de líneas válidas:
    1    0.000   0.000  1500.000   0.001  -0.002   0.015
    2   50.000  86.603  1499.987   0.000   0.001   0.018
    3  100.000   0.000  1499.950  -0.001   0.000   0.012
    ...

Restricciones y recomendaciones:
  - Las líneas que comiencen por '#' o estén vacías se ignoran.
  - No es necesario ordenar los nodos por ningún criterio.
  - El origen de coordenadas NO necesita estar centrado en el espejo;
    el programa calcula automáticamente el centroide de los nodos y
    centra ahí todas las funciones de apertura (circular, cuadrada,
    rectangular o hexagonal).
  - Se recomienda exportar el fichero en el sistema de referencia del
    elemento óptico (eje Z = eje óptico), no en el sistema global de
    la estructura, para que los desplazamientos dZ representen
    correctamente el error de figura.
  - Unidades: el programa es agnóstico a las unidades; los resultados
    (RMS, PV, coeficientes de Zernike) estarán en las mismas unidades
    que dX dY dZ (nanómetros si se exporta en nm, micras si en µm, etc.).


Flujo de trabajo
----------------
1. Leer fichero TXT con nube de puntos FEM
   Formato esperado: node_id  X  Y  Z  dX  dY  dZ
2. Triangulación de Delaunay → áreas nodales y normales de superficie
3. Eliminar modos de sólido rígido seleccionables (Tx Ty Tz Rx Ry Rz)
4. Calcular desplazamiento normal residual y su RMS ponderado por área
5. Descomponer en polinomios de Zernike (ISO) sobre la apertura seleccionada:
   circular | cuadrada | rectangular | hexagonal

Uso
---
python fem_mirror_analysis.py AARESULTADOS2.TXT [opciones]

Ejemplos
--------
# Sólo quitar Tz (defecto), apertura circular, ajustar Z0..Z9
python fem_mirror_analysis.py AARESULTADOS2.TXT --terms 0 1 2 3 4 5 6 7 8 9

# Quitar todos los modos de sólido rígido, espejo hexagonal radio 750 mm
python fem_mirror_analysis.py AARESULTADOS2.TXT \\
    --rigid 1 1 1 1 1 1 \\
    --aperture hexagonal --hexradius 750 \\
    --terms 0 1 2 3 4 5 6 7 8 9 10 --plot

# Listar nombres ISO de Zernike
python fem_mirror_analysis.py --list-terms

Dependencias
------------
numpy, scipy, matplotlib
  pip install numpy scipy matplotlib
"""

import argparse
import math
import sys

import numpy as np
from scipy.spatial import Delaunay


# ═══════════════════════════════════════════════════════════════════════════════
#  POLINOMIOS DE ZERNIKE
# ═══════════════════════════════════════════════════════════════════════════════

# Nombres descriptivos de los primeros términos ISO
ZERNIKE_NAMES = {
    0:  "Pistón (Z0)",
    1:  "Tip Y / Inclinación Y (Z1)",
    2:  "Tilt X / Inclinación X (Z2)",
    3:  "Desenfoque / Foco (Z3)",
    4:  "Astigmatismo oblicuo (Z4)",
    5:  "Astigmatismo (Z5)",
    6:  "Coma Y (Z6)",
    7:  "Coma X (Z7)",
    8:  "Trébol Y (Z8)",
    9:  "Trébol X (Z9)",
    10: "Aberración esférica primaria (Z10)",
    11: "Astigmatismo secundario oblicuo (Z11)",
    12: "Astigmatismo secundario (Z12)",
    13: "Coma secundaria Y (Z13)",
    14: "Coma secundaria X (Z14)",
    15: "Aberración esférica secundaria (Z15)",
}


def zernike_iso2nm(nterms):
    """
    Órdenes radial (n) y angular (m) para los primeros `nterms` polinomios
    de Zernike en ordenación ISO estándar.

    ISO Z_0 = pistón, Z_1 = tip (m=−1), Z_2 = tilt (m=+1), ...

    Parámetros
    ----------
    nterms : int
        Número de términos requeridos.

    Devuelve
    --------
    n_arr, m_arr : ndarray (nterms,), dtype int
    """
    n_arr = np.zeros(nterms, dtype=int)
    m_arr = np.zeros(nterms, dtype=int)
    idx = 0
    for shell in range(0, 2 * nterms + 2, 2):
        for inn in range(shell // 2, shell + 1):
            angular = shell - inn
            n_arr[idx] = inn
            m_arr[idx] = angular
            idx += 1
            if idx == nterms:
                return n_arr, m_arr
            if angular != 0:
                n_arr[idx] = inn
                m_arr[idx] = -angular
                idx += 1
                if idx == nterms:
                    return n_arr, m_arr
    return n_arr, m_arr


def zernike_radial_coeffs(n, m_abs, norm='pico'):
    """
    Coeficientes del polinomio radial de Zernike R_n^|m|(r), en orden
    descendente de potencias (compatible con numpy.polyval).

    Fórmula:
        R_n^m(r) = Σ_{s=0}^{(n-m)/2}  (-1)^s (n-s)! / [s! ((n+m)/2-s)! ((n-m)/2-s)!]  r^{n-2s}

    Parámetros
    ----------
    n     : int   Orden radial
    m_abs : int   |m|, orden angular (≥ 0)
    norm  : str   'pico' → máximo = 1 ;  'rms' → RMS sobre disco unidad = 1

    Devuelve
    --------
    coeffs : ndarray (n+1,)   Coeficientes en orden DESCENDENTE de potencias.
    """
    if (n + m_abs) % 2 != 0:
        raise ValueError(f"n={n}, |m|={m_abs}: n+|m| debe ser par")
    if m_abs > n:
        raise ValueError(f"n={n}, |m|={m_abs}: |m| debe ser ≤ n")

    # Posición 2*s en el array de longitud n+1 recibe el coeficiente de r^(n-2s)
    coeffs = np.zeros(n + 1)
    for s in range((n - m_abs) // 2 + 1):
        num = math.factorial(n - s)
        den = (math.factorial(s)
               * math.factorial((n + m_abs) // 2 - s)
               * math.factorial((n - m_abs) // 2 - s))
        coeffs[2 * s] = ((-1) ** s) * num / den

    if norm == 'rms':
        factor = math.sqrt(n + 1) if m_abs == 0 else math.sqrt(2 * (n + 1))
        coeffs *= factor

    return coeffs


def eval_zernike_term(n, m, r, theta, norm='pico'):
    """
    Evalúa el polinomio de Zernike Z_n^m en los puntos (r, theta).

    Convención:
        m ≥ 0 → Z = R_n^m(r) cos(m θ)
        m < 0 → Z = R_n^m(r) sin(|m| θ)

    Parámetros
    ----------
    n, m   : int        Órdenes radial y angular
    r      : ndarray    Coordenada radial normalizada [0, 1]
    theta  : ndarray    Ángulo azimutal [rad]
    norm   : str        'pico' o 'rms'

    Devuelve
    --------
    Z : ndarray con los valores del polinomio en cada punto.
    """
    coeffs = zernike_radial_coeffs(n, abs(m), norm)
    R = np.polyval(coeffs, r)
    if m >= 0:
        return R * np.cos(m * theta)
    else:
        return R * np.sin(-m * theta)


def build_zernike_matrix(terms, r, theta, norm='pico'):
    """
    Construye la matriz de diseño para el ajuste de Zernike.

    Parámetros
    ----------
    terms  : list[int]  Índices ISO de los términos a incluir
    r      : ndarray    Coordenada radial normalizada [0, 1]
    theta  : ndarray    Ángulo azimutal [rad]
    norm   : str        'pico' o 'rms'

    Devuelve
    --------
    A : ndarray (N_puntos, N_terms)
    """
    max_term = max(terms) + 1
    n_arr, m_arr = zernike_iso2nm(max_term)
    A = np.zeros((len(r), len(terms)))
    for col, t in enumerate(terms):
        A[:, col] = eval_zernike_term(n_arr[t], m_arr[t], r, theta, norm)
    return A


# ═══════════════════════════════════════════════════════════════════════════════
#  GEOMETRÍA DE SUPERFICIE: ÁREAS NODALES Y NORMALES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_nodal_areas_and_normals(coor, area_threshold=0.0):
    """
    Triangulación de Delaunay en XY de la nube de puntos 3D.
    Calcula áreas nodales (ponderación por área del triángulo / 3) y
    vectores normales unitarios en cada nodo.

    Equivale a la triangulación de extract_rigid.m / lee.m.

    Parámetros
    ----------
    coor           : ndarray (N, 3)   Coordenadas X, Y, Z de los nodos
    area_threshold : float            Área mínima en XY para aceptar un triángulo
                                      (filtra triángulos degenerados; MATLAB usa 1)

    Devuelve
    --------
    simplices  : ndarray (M, 3)   Índices de los triángulos válidos
    an         : ndarray (N,)     Áreas nodales normalizadas (suma = 1)
    normals    : ndarray (N, 3)   Vectores normales unitarios en cada nodo
    """
    npts = len(coor)

    # Triangulación 2D en XY
    tri = Delaunay(coor[:, :2])
    simplices = tri.simplices  # (M, 3)

    # Vectores de arista en XY para calcular el área proyectada
    p0 = coor[simplices[:, 0], :2]
    p1 = coor[simplices[:, 1], :2]
    p2 = coor[simplices[:, 2], :2]
    v12 = p1 - p0
    v13 = p2 - p0
    # Dos veces el área del triángulo proyectado en XY (= módulo del producto vectorial 2D)
    area2d = np.abs(v12[:, 0] * v13[:, 1] - v13[:, 0] * v12[:, 1])

    # Filtrar triángulos degenerados (igual que MATLAB: find(abs(area)>1))
    valid = area2d > area_threshold
    simplices = simplices[valid]
    area2d = area2d[valid]

    # ── Normales de triángulo en 3D ─────────────────────────────────────────
    p0 = coor[simplices[:, 0]]
    p1 = coor[simplices[:, 1]]
    p2 = coor[simplices[:, 2]]
    face_n = np.cross(p1 - p0, p2 - p0)              # (M, 3)
    # Orientar para que la componente Z sea positiva
    sign_z = np.sign(face_n[:, 2])
    sign_z[sign_z == 0] = 1.0
    face_n *= sign_z[:, np.newaxis]

    # ── Áreas nodales ────────────────────────────────────────────────────────
    an = np.zeros(npts)
    for j in range(3):
        np.add.at(an, simplices[:, j], area2d / 3.0)
    an /= an.sum()   # normalizar: suma = 1

    # ── Normales nodales (acumular y normalizar) ─────────────────────────────
    node_n = np.zeros((npts, 3))
    for j in range(3):
        np.add.at(node_n, simplices[:, j], face_n)
    mag = np.linalg.norm(node_n, axis=1, keepdims=True)
    mag[mag == 0] = 1.0
    node_n /= mag

    return simplices, an, node_n


# ═══════════════════════════════════════════════════════════════════════════════
#  EXTRACCIÓN DEL MOVIMIENTO DE SÓLIDO RÍGIDO
# ═══════════════════════════════════════════════════════════════════════════════

def extract_rigid(coor, disp, rigidmodes=(0, 0, 1, 0, 0, 0),
                  area_threshold=0.0):
    """
    Extrae el desplazamiento de sólido rígido de un campo de desplazamientos
    nodales y devuelve el desplazamiento normal residual.

    Traducción directa de extract_rigid.m (IAC).

    Modos de sólido rígido (traslaciones y rotaciones):
        rigidmodes = [Tx, Ty, Tz, Rx, Ry, Rz]   0 = conservar, 1 = eliminar

    La extracción se hace por mínimos cuadrados ponderados por la raíz
    cuadrada del área nodal.  Los modos activos se eliminan restando el
    campo de desplazamiento rígido más próximo (en sentido L²-área-ponderado).

    Parámetros
    ----------
    coor          : ndarray (N, 3)  Coordenadas de nodos
    disp          : ndarray (N, 3)  Desplazamientos nodales [dX, dY, dZ]
    rigidmodes    : secuencia de 6 ints  Flags de modos a eliminar
    area_threshold: float           Umbral de área para triángulos degenerados

    Devuelve
    --------
    un  : ndarray (N,)   Desplazamiento normal residual
    an  : ndarray (N,)   Áreas nodales normalizadas
    pos : ndarray (6,)   Coeficientes de sólido rígido [Tx, Ty, Tz, Rx, Ry, Rz]
    """
    _, an, node_norms = compute_nodal_areas_and_normals(coor, area_threshold)

    pos = np.zeros(6)
    disp_corr = disp.astype(float).copy()
    active = [i for i, f in enumerate(rigidmodes) if f != 0]

    if active:
        an_sqrt = np.sqrt(an)          # peso nodal = sqrt(área)
        npts = len(coor)

        # Matriz de modos de sólido rígido ponderada: (3*N, 6)
        # Orden de filas: [N filas dX | N filas dY | N filas dZ]
        # Columnas: Tx, Ty, Tz, Rx, Ry, Rz
        A = np.zeros((3 * npts, 6))
        # Traslaciones puras
        A[0       :npts,   0] = an_sqrt            # Tx → dX
        A[npts    :2*npts, 1] = an_sqrt            # Ty → dY
        A[2*npts  :3*npts, 2] = an_sqrt            # Tz → dZ
        # Rotación Rx (alrededor de X): dY = -Z*Rx, dZ = +Y*Rx
        A[npts    :2*npts, 3] = -coor[:, 2] * an_sqrt
        A[2*npts  :3*npts, 3] = +coor[:, 1] * an_sqrt
        # Rotación Ry (alrededor de Y): dX = +Z*Ry, dZ = -X*Ry
        A[0       :npts,   4] = +coor[:, 2] * an_sqrt
        A[2*npts  :3*npts, 4] = -coor[:, 0] * an_sqrt
        # Rotación Rz (alrededor de Z): dX = -Y*Rz, dY = +X*Rz
        A[0       :npts,   5] = -coor[:, 1] * an_sqrt
        A[npts    :2*npts, 5] = +coor[:, 0] * an_sqrt

        # Seleccionar sólo los modos activos
        A_act = A[:, active]

        # Vector de desplazamientos ponderados [dX*w | dY*w | dZ*w]
        b = (disp_corr * an_sqrt[:, np.newaxis]).ravel(order='F')
        # ravel 'F' → primero todas las filas de dX, luego dY, luego dZ

        # Mínimos cuadrados
        coef, *_ = np.linalg.lstsq(A_act, b, rcond=None)
        pos[active] = coef

        # Restar el campo de sólido rígido a los desplazamientos
        # A_act @ coef tiene las mismas unidades que an_sqrt * disp
        rigid_weighted = (A_act @ coef).reshape(npts, 3, order='F')
        # Evitar 0/0 en nodos aislados: para ellos an_sqrt=0 y
        # rigid_weighted=0 también, pero 0/0=NaN propagaría NaN al resultado.
        safe_w = np.where(an_sqrt > 0, an_sqrt, 1.0)
        disp_corr -= rigid_weighted / safe_w[:, np.newaxis]

    # Desplazamiento normal = proyección sobre la normal de superficie
    un = (disp_corr * node_norms).sum(axis=1)

    return un, an, pos


# ═══════════════════════════════════════════════════════════════════════════════
#  MÁSCARAS DE APERTURA Y NORMALIZACIÓN DE COORDENADAS
# ═══════════════════════════════════════════════════════════════════════════════

def aperture_circular(xy, radius=None):
    """
    Máscara circular.

    Las coordenadas se centran automáticamente en el centroide de los nodos,
    por lo que el origen del fichero FEM puede estar en cualquier posición.

    Parámetros
    ----------
    xy     : ndarray (N, 2)   Coordenadas X, Y de los nodos
    radius : float o None     Radio de la apertura; si None → máximo radial
                              medido desde el centroide

    Devuelve
    --------
    mask   : ndarray (N,) bool
    r_norm : ndarray (M,)     Radio normalizado al radio de la apertura [0, 1]
    theta  : ndarray (M,)     Ángulo azimutal [rad]
    """
    x, y = xy[:, 0], xy[:, 1]
    # Centrar en el centroide para que la apertura no dependa del origen FEM
    xc, yc = x - x.mean(), y - y.mean()
    r = np.hypot(xc, yc)
    if radius is None:
        radius = r.max()
    mask = r <= radius
    r_norm = r[mask] / radius
    theta  = np.arctan2(yc[mask], xc[mask])
    return mask, r_norm, theta


def aperture_square(xy, side=None):
    """
    Máscara cuadrada (|xc| ≤ L/2 y |yc| ≤ L/2).
    La normalización radial usa el radio de la circunferencia circunscrita (L/2·√2).

    Las coordenadas se centran automáticamente en el centroide de los nodos.

    Parámetros
    ----------
    xy   : ndarray (N, 2)
    side : float o None     Longitud del lado; si None → 2·max(|xc|, |yc|)
                            medido desde el centroide
    """
    x, y = xy[:, 0], xy[:, 1]
    # Centrar en el centroide
    xc, yc = x - x.mean(), y - y.mean()
    if side is None:
        side = 2.0 * max(np.abs(xc).max(), np.abs(yc).max())
    half = side / 2.0
    mask = (np.abs(xc) <= half) & (np.abs(yc) <= half)
    r_circ = half * math.sqrt(2)   # circunferencia circunscrita
    r_norm = np.hypot(xc[mask], yc[mask]) / r_circ
    theta  = np.arctan2(yc[mask], xc[mask])
    return mask, r_norm, theta


def aperture_rectangular(xy, width=None, height=None):
    """
    Máscara rectangular (|xc| ≤ W/2 y |yc| ≤ H/2).
    La normalización radial usa la diagonal del rectángulo / 2.

    Las coordenadas se centran automáticamente en el centroide de los nodos.

    Parámetros
    ----------
    xy     : ndarray (N, 2)
    width  : float o None   Anchura (X); si None → 2·max|xc| desde el centroide
    height : float o None   Altura  (Y); si None → 2·max|yc| desde el centroide
    """
    x, y = xy[:, 0], xy[:, 1]
    # Centrar en el centroide
    xc, yc = x - x.mean(), y - y.mean()
    if width  is None:
        width  = 2.0 * np.abs(xc).max()
    if height is None:
        height = 2.0 * np.abs(yc).max()
    hw, hh = width / 2.0, height / 2.0
    mask = (np.abs(xc) <= hw) & (np.abs(yc) <= hh)
    r_circ = math.hypot(hw, hh)   # semidiagonal del rectángulo
    r_norm = np.hypot(xc[mask], yc[mask]) / r_circ
    theta  = np.arctan2(yc[mask], xc[mask])
    return mask, r_norm, theta


def aperture_hexagonal(xy, circumradius=None):
    """
    Máscara hexagonal regular (orientación con vértice en el eje X positivo).
    Prueba: para cada uno de los 6 lados, la distancia al lado ≤ apotema.

    Las coordenadas se centran automáticamente en el centroide de los nodos,
    por lo que el origen del fichero FEM puede estar en cualquier posición.

    Parámetros
    ----------
    xy            : ndarray (N, 2)
    circumradius  : float o None   Circunradio (vértice a centro) en las mismas
                                   unidades que xy; si None → máximo radial
                                   medido desde el centroide
    """
    x, y = xy[:, 0], xy[:, 1]
    # Centrar en el centroide para que el hexágono quede correctamente posicionado
    xc, yc = x - x.mean(), y - y.mean()
    if circumradius is None:
        circumradius = np.hypot(xc, yc).max()
    apothem = circumradius * math.sqrt(3) / 2.0   # distancia centro–lado

    # Condiciones de inclusión para hexágono regular orientado vértice-derecha
    c1 = np.abs(yc) <= apothem
    c2 = np.abs(xc * (math.sqrt(3) / 2) + yc * 0.5) <= apothem
    c3 = np.abs(xc * (math.sqrt(3) / 2) - yc * 0.5) <= apothem
    mask = c1 & c2 & c3

    r_norm = np.hypot(xc[mask], yc[mask]) / circumradius
    theta  = np.arctan2(yc[mask], xc[mask])
    return mask, r_norm, theta


# Registro de funciones de apertura disponibles
APERTURE_FUNCTIONS = {
    'circular':    aperture_circular,
    'square':      aperture_square,
    'rectangular': aperture_rectangular,
    'hexagonal':   aperture_hexagonal,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  AJUSTE DE ZERNIKE SOBRE DATOS DISPERSOS
# ═══════════════════════════════════════════════════════════════════════════════

def zernike_fit_scatter(un, r_norm, theta, terms, norm='pico'):
    """
    Ajuste por mínimos cuadrados de polinomios de Zernike sobre datos dispersos.

    Parámetros
    ----------
    un     : ndarray (M,)     Desplazamiento normal en los puntos de la apertura
    r_norm : ndarray (M,)     Radio normalizado [0, 1]
    theta  : ndarray (M,)     Ángulo azimutal [rad]
    terms  : list[int]        Índices ISO de los términos a ajustar
    norm   : str              'pico' o 'rms'

    Devuelve
    --------
    coeffs   : ndarray (len(terms),)   Coeficientes de Zernike
    residual : ndarray (M,)            Residuo tras el ajuste
    A        : ndarray (M, len(terms)) Matriz de diseño (para diagnóstico)
    """
    A = build_zernike_matrix(terms, r_norm, theta, norm)
    coeffs, *_ = np.linalg.lstsq(A, un, rcond=None)
    residual = un - A @ coeffs
    return coeffs, residual, A


# ═══════════════════════════════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════════════════════

def rms_area_weighted(values, an):
    """
    RMS ponderado por área nodal.

    RMS = sqrt( Σ an_i · u_i² )    con  Σ an_i = 1
    """
    return math.sqrt(float(np.sum(an * values ** 2)))


def peak_to_valley(values):
    """Pico a valle."""
    return float(values.max() - values.min())


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRADA/SALIDA
# ═══════════════════════════════════════════════════════════════════════════════

def load_fem_data(fname):
    """
    Carga el fichero TXT de resultados FEM.

    Columnas esperadas: node_id  X  Y  Z  dX  dY  dZ
    Si hay más columnas, se ignoran las extras.

    Devuelve
    --------
    node : ndarray (N,)     Identificadores de nodo
    coor : ndarray (N, 3)   Coordenadas X, Y, Z
    disp : ndarray (N, 3)   Desplazamientos dX, dY, dZ
    """
    data = np.loadtxt(fname)
    if data.ndim == 1:
        data = data[np.newaxis, :]
    ncols = data.shape[1]
    if ncols >= 7:
        # Formato completo: node_id  X  Y  Z  dX  dY  dZ  [extras…]
        return data[:, 0], data[:, 1:4], data[:, 4:7]
    elif ncols == 6:
        # Sin node_id: X  Y  Z  dX  dY  dZ
        node = np.arange(len(data), dtype=float)
        return node, data[:, 0:3], data[:, 3:6]
    else:
        raise ValueError(
            f"El fichero debe tener 6 columnas (X Y Z dX dY dZ) o "
            f"7 columnas (node_id X Y Z dX dY dZ). Encontradas: {ncols}"
        )


def print_zernike_table():
    """Imprime la tabla de nombres ISO de Zernike."""
    print("\n  Índices ISO de Zernike (los más usados en óptica):")
    print(f"  {'Índice':>7}  {'n':>3}  {'m':>4}  Nombre")
    print(f"  {'-------':>7}  {'---':>3}  {'----':>4}  ------")
    max_t = max(ZERNIKE_NAMES.keys()) + 1
    n_arr, m_arr = zernike_iso2nm(max_t)
    for t, name in ZERNIKE_NAMES.items():
        print(f"  Z{t:>5d}   {n_arr[t]:>3d}  {m_arr[t]:>4d}  {name}")


def print_rigid_body_results(pos, rigidmodes):
    """Imprime los coeficientes de sólido rígido extraídos."""
    labels = ['Tx', 'Ty', 'Tz', 'Rx', 'Ry', 'Rz']
    activos = [(labels[i], pos[i]) for i in range(6) if rigidmodes[i]]
    if activos:
        print("\n  Coeficientes de sólido rígido eliminados:")
        for name, val in activos:
            print(f"    {name} = {val:+.6g}")


def print_zernike_results(terms, coeffs, n_arr, m_arr):
    """Imprime tabla de coeficientes de Zernike."""
    print(f"\n  {'Term':>6}  {'n':>3}  {'m':>4}  {'Coeficiente':>14}  Nombre")
    print(f"  {'------':>6}  {'---':>3}  {'----':>4}  {'-------------':>14}  -----")
    for i, t in enumerate(terms):
        name = ZERNIKE_NAMES.get(t, "")
        print(f"  Z{t:>5d}   {n_arr[t]:>3d}  {m_arr[t]:>4d}  "
              f"{coeffs[i]:>14.6g}  {name}")


# ═══════════════════════════════════════════════════════════════════════════════
#  VISUALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def plot_results(coor, un, mask, residual, aperture_name, output_file='fem_analysis.png'):
    """Genera figura con mapa de desplazamiento y residuo de Zernike."""
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    x, y = coor[:, 0], coor[:, 1]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel izquierdo: desplazamiento normal completo
    triang_full = mtri.Triangulation(x, y)
    cf1 = axes[0].tricontourf(triang_full, un, levels=64, cmap='RdBu_r')
    plt.colorbar(cf1, ax=axes[0], label='Desplazamiento normal')
    axes[0].set_title('Desplazamiento normal\n(tras quitar sólido rígido)')
    axes[0].set_aspect('equal')
    axes[0].set_xlabel('X')
    axes[0].set_ylabel('Y')

    # Panel derecho: residuo del ajuste de Zernike (sólo apertura)
    un_res_full = np.full(len(coor), np.nan)
    un_res_full[mask] = residual

    valid = ~np.isnan(un_res_full)
    if valid.sum() > 3:
        triang_ap = mtri.Triangulation(x[valid], y[valid])
        cf2 = axes[1].tricontourf(triang_ap, un_res_full[valid], levels=64, cmap='RdBu_r')
        plt.colorbar(cf2, ax=axes[1], label='Residuo Zernike')
    axes[1].set_title(f'Residuo tras ajuste Zernike\n(apertura {aperture_name})')
    axes[1].set_aspect('equal')
    axes[1].set_xlabel('X')
    axes[1].set_ylabel('Y')

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n  Gráfico guardado en: {output_file}")
    plt.show()


# ═══════════════════════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Análisis FEM de desplazamientos de superficie de espejo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Uso")[0].strip(),
    )

    parser.add_argument(
        "fname", nargs="?",
        help="Fichero TXT con resultados FEM (columnas: node X Y Z dX dY dZ)"
    )
    parser.add_argument(
        "--rigid", nargs=6, type=int, default=[0, 0, 1, 0, 0, 0],
        metavar=("Tx", "Ty", "Tz", "Rx", "Ry", "Rz"),
        help="Modos de sólido rígido a eliminar: 0=conservar, 1=eliminar. "
             "Orden: Tx Ty Tz Rx Ry Rz.  Default: 0 0 1 0 0 0 (sólo Tz)"
    )
    parser.add_argument(
        "--area-threshold", type=float, default=1.0,
        help="Umbral de área (unidades del modelo) para filtrar triángulos "
             "degenerados en la triangulación.  Default: 1.0"
    )
    parser.add_argument(
        "--aperture",
        choices=list(APERTURE_FUNCTIONS.keys()),
        default="circular",
        help="Forma de la apertura para el ajuste de Zernike.  Default: circular"
    )
    parser.add_argument(
        "--radius", type=float, default=None,
        help="Radio de la apertura circular (mismas unidades que las coordenadas). "
             "Default: radio máximo de los datos"
    )
    parser.add_argument(
        "--side", type=float, default=None,
        help="Lado de la apertura cuadrada.  Default: ajuste automático"
    )
    parser.add_argument(
        "--width", type=float, default=None,
        help="Anchura (X) de la apertura rectangular.  Default: ajuste automático"
    )
    parser.add_argument(
        "--height", type=float, default=None,
        help="Altura (Y) de la apertura rectangular.  Default: ajuste automático"
    )
    parser.add_argument(
        "--hexradius", type=float, default=None,
        help="Circunradio de la apertura hexagonal.  Default: radio máximo de los datos"
    )
    parser.add_argument(
        "--terms", nargs="+", type=int, default=[0, 1, 2, 3],
        help="Índices ISO de los términos de Zernike a ajustar. "
             "Default: 0 1 2 3  (pistón, tip, tilt, foco). "
             "Usar --list-terms para ver la tabla completa"
    )
    parser.add_argument(
        "--norm", choices=["pico", "rms"], default="pico",
        help="Normalización de los polinomios de Zernike.  Default: pico"
    )
    parser.add_argument(
        "--no-zernike", action="store_true",
        help="Omitir la descomposición en Zernike (sólo RMS de sólido rígido)"
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Generar y guardar figura de resultados"
    )
    parser.add_argument(
        "--plot-file", default="fem_analysis.png",
        help="Nombre del fichero de imagen.  Default: fem_analysis.png"
    )
    parser.add_argument(
        "--list-terms", action="store_true",
        help="Mostrar tabla de nombres ISO de Zernike y salir"
    )

    args = parser.parse_args()

    # ── Modo consulta de tabla ────────────────────────────────────────────────
    if args.list_terms:
        print_zernike_table()
        sys.exit(0)

    if args.fname is None:
        parser.error("Se requiere el nombre del fichero de datos FEM.")

    # ── Carga de datos ────────────────────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  fem_mirror_analysis.py")
    print(f"{'═'*60}")
    print(f"\n  Leyendo: {args.fname}")
    node, coor, disp = load_fem_data(args.fname)
    print(f"  Nodos leídos: {len(node)}")
    print(f"  X ∈ [{coor[:,0].min():.4g}, {coor[:,0].max():.4g}]")
    print(f"  Y ∈ [{coor[:,1].min():.4g}, {coor[:,1].max():.4g}]")
    print(f"  Z ∈ [{coor[:,2].min():.4g}, {coor[:,2].max():.4g}]")

    # ── Extracción del sólido rígido ──────────────────────────────────────────
    rigid_flags = tuple(args.rigid)
    active_names = [n for n, f in zip(['Tx','Ty','Tz','Rx','Ry','Rz'], rigid_flags) if f]
    print(f"\n  Eliminando sólido rígido: {active_names if active_names else 'ninguno'}")

    un, an, pos = extract_rigid(coor, disp, rigid_flags, args.area_threshold)

    print_rigid_body_results(pos, rigid_flags)

    rms_total = rms_area_weighted(un, an)
    pv_total  = peak_to_valley(un)
    print(f"\n  ── Desplazamiento normal (apertura completa) ──")
    print(f"  RMS (pond. por área): {rms_total:.6g}")
    print(f"  Pico a valle (P-V):   {pv_total:.6g}")

    # ── Descomposición en Zernike ─────────────────────────────────────────────
    if not args.no_zernike:
        print(f"\n  ── Descomposición en Zernike ──────────────────────────")
        print(f"  Apertura: {args.aperture}")

        # Construir máscara de apertura
        xy = coor[:, :2]
        ap_fn = APERTURE_FUNCTIONS[args.aperture]
        ap_kwargs = {}
        if args.aperture == 'circular' and args.radius is not None:
            ap_kwargs['radius'] = args.radius
        elif args.aperture == 'square' and args.side is not None:
            ap_kwargs['side'] = args.side
        elif args.aperture == 'rectangular':
            if args.width  is not None:
                ap_kwargs['width']  = args.width
            if args.height is not None:
                ap_kwargs['height'] = args.height
        elif args.aperture == 'hexagonal' and args.hexradius is not None:
            ap_kwargs['circumradius'] = args.hexradius

        mask, r_norm, theta = ap_fn(xy, **ap_kwargs)
        print(f"  Nodos en apertura: {mask.sum()} / {len(mask)}")

        if mask.sum() < len(args.terms):
            print("  ⚠  Advertencia: menos puntos que términos de Zernike. "
                  "El ajuste puede ser inestable.")

        un_ap = un[mask]
        an_ap = an[mask] / an[mask].sum()   # renormalizar dentro de la apertura

        # Ajuste
        terms = sorted(set(args.terms))
        coeffs, residual, _ = zernike_fit_scatter(un_ap, r_norm, theta, terms, args.norm)

        max_t = max(terms) + 1
        n_arr, m_arr = zernike_iso2nm(max_t)
        print_zernike_results(terms, coeffs, n_arr, m_arr)

        rms_ap_before = rms_area_weighted(un_ap, an_ap)
        rms_ap_after  = rms_area_weighted(residual, an_ap)
        pv_ap_before  = peak_to_valley(un_ap)
        pv_ap_after   = peak_to_valley(residual)

        print(f"\n  Dentro de la apertura — ANTES del ajuste:")
        print(f"    RMS = {rms_ap_before:.6g}")
        print(f"    P-V = {pv_ap_before:.6g}")
        print(f"\n  Dentro de la apertura — TRAS el ajuste de Zernike:")
        print(f"    RMS = {rms_ap_after:.6g}")
        print(f"    P-V = {pv_ap_after:.6g}")
        reduccion = (1.0 - rms_ap_after / rms_ap_before) * 100.0 if rms_ap_before > 0 else 0.0
        print(f"    Reducción de RMS: {reduccion:.1f}%")
    else:
        mask = np.zeros(len(coor), dtype=bool)
        residual = np.array([])

    print(f"\n{'═'*60}\n")

    # ── Gráficos ──────────────────────────────────────────────────────────────
    if args.plot:
        if not args.no_zernike and mask.any():
            plot_results(coor, un, mask, residual, args.aperture, args.plot_file)
        else:
            # Sólo mapa de desplazamiento
            import matplotlib.pyplot as plt
            import matplotlib.tri as mtri
            fig, ax = plt.subplots(figsize=(8, 7))
            triang = mtri.Triangulation(coor[:, 0], coor[:, 1])
            cf = ax.tricontourf(triang, un, levels=64, cmap='RdBu_r')
            plt.colorbar(cf, ax=ax, label='Desplazamiento normal')
            ax.set_title('Desplazamiento normal (tras quitar sólido rígido)')
            ax.set_aspect('equal')
            ax.set_xlabel('X'); ax.set_ylabel('Y')
            plt.tight_layout()
            plt.savefig(args.plot_file, dpi=150, bbox_inches='tight')
            print(f"\n  Gráfico guardado en: {args.plot_file}")
            plt.show()


if __name__ == '__main__':
    main()
