#!/usr/bin/env python3
"""
fem_mirror_analysis.py
======================
Análisis de desplazamientos de superficie de espejo a partir de resultados FEM.

Portado de las rutinas MATLAB: extract_rigid.m, zerfit.m, zernike.m,
zernikeISO2nm.m  (MatlabToolsJCL, IAC / JCL)


FORMATO DEL FICHERO DE ENTRADA TXT
===================================
Una línea por nodo FEM, campos separados por espacios o tabuladores:

    node_id   X   Y   Z   dX   dY   dZ        (7 columnas)
    X   Y   Z   dX   dY   dZ                  (6 columnas, sin node_id)

  - X, Y, Z    : coordenadas del nodo.
  - dX, dY, dZ : desplazamientos del nodo (mismas unidades que X Y Z).
  - Las líneas que empiezan por '#' o vacías se ignoran.
  - El orden de los nodos es indiferente.
  - Sólo deben exportarse los nodos de la SUPERFICIE ÓPTICA.
  - Si la primera columna tiene valores repetidos se interpreta como número
    de CASO DE CARGA (varios casos apilados, p. ej. AARESULTADOS2.TXT) y hay
    que elegir uno con --case.
  - El programa es agnóstico a unidades: RMS, PV y coeficientes salen en
    las unidades de dX dY dZ.


FLUJO DE TRABAJO
----------------
1. Leer la nube de puntos FEM.
2. Sistema de referencia (--frame):
     global  : Z del fichero = eje óptico (por defecto, como el MATLAB).
     bestfit : girar a la normal del plano best-fit (SVD), equivalente a
               SurfCalc "Best-fit Plane (Auto)".  Útil si el espejo plano
               está exportado inclinado.  NO usar en modelos parciales de
               espejos curvos ni en segmentos fuera de eje.
   Para un espejo plano exportado con Z = eje óptico ambos coinciden.
3. Triangulación de Delaunay → áreas nodales (proyectadas en la pupila) y
   normales nodales.
4. Eliminar los modos de sólido rígido seleccionados (Tx Ty Tz Rx Ry Rz),
   ajuste por mínimos cuadrados ponderado por área.
5. Desplazamiento normal residual  u_n = u · n̂.
6. Ajuste polinómico WLS (ponderado por área) sobre la apertura:
     circular     → Zernike circular, convención Fringe o Noll
     rectangular  → Chebyshev 2D  T_i(x)·T_j(y)
     anular       → (pendiente: Zernike anular de Mahajan)
     hexagonal    → (pendiente: polinomios de segmento hexagonal)


CONVENCIONES DE ZERNIKE (apertura circular)
-------------------------------------------
Fringe (--convention fringe, por defecto).  Índices del script 0-based,
históricos de zernikeISO2nm.m.  Script Zk ↔ Fringe Z(k+1):
  Z0 pistón · Z1 tilt X (cosθ) · Z2 tilt Y (sinθ) · Z3 desenfoque ·
  Z4 astig. 0°/90° (cos2θ) · Z5 astig. ±45° (sin2θ) · Z6/Z7 coma X/Y ·
  Z8 esférica primaria · Z9/Z10 trébol · ...

Noll (--convention noll).  Índices 1-based estándar (Noll 1976):
  Z1 pistón · Z2 tilt X · Z3 tilt Y · Z4 desenfoque · Z5 astig. ±45° ·
  Z6 astig. 0°/90° · Z7/Z8 coma · Z9/Z10 trébol · Z11 esférica · ...

¡Atención!  "Términos 1-5" NO son lo mismo en Fringe (incluye astig. 0°)
que en Noll (incluye astig. 45°).  SurfCalc usa Noll por defecto.

Normalización (--norm): 'pico' (valor máximo 1 en el borde) o 'rms'
(RMS unidad sobre el disco, normalización de Noll).  Sólo cambia el valor
de los coeficientes; el residuo, su RMS y su PV NO dependen de ella.


POLINOMIOS DE CHEBYSHEV (apertura rectangular)
----------------------------------------------
Producto tensorial de Chebyshev de primera especie T_i(x)·T_j(y), con x, y
normalizados a [-1, 1] mediante la semianchura y semialtura de la apertura.
Ordenación triangular por grado total k = i + j y, dentro de cada grado,
de mayor a menor potencia en x:
  C0 (0,0) pistón · C1 (1,0) tilt X · C2 (0,1) tilt Y ·
  C3 (2,0) curvatura X · C4 (1,1) torsión · C5 (0,2) curvatura Y · ...
Los lados del rectángulo deben ser paralelos a los ejes X e Y.


Uso
---
python fem_mirror_analysis.py RESULTADOS.TXT [opciones]

Ejemplos
--------
# Apertura circular, ajustar los 5 primeros Fringe (Z0..Z4)
python fem_mirror_analysis.py RESULTADOS.TXT --terms 0 1 2 3 4

# Igual que SurfCalc "Noll Zernike, terms 1-5"
python fem_mirror_analysis.py RESULTADOS.TXT --convention noll --terms 1 2 3 4 5

# Espejo rectangular 120 x 80, Chebyshev hasta grado 2
python fem_mirror_analysis.py RESULTADOS.TXT --aperture rectangular \\
    --width 120 --height 80 --terms 0 1 2 3 4 5 --plot

# Listar términos
python fem_mirror_analysis.py --list-terms --convention noll

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
#  APERTURAS Y BASES DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════

# Aperturas implementadas y la base polinómica que usa cada una
APERTURE_BASIS = {
    'circular':    'zernike',
    'rectangular': 'chebyshev',
}
# Aperturas previstas pero todavía no implementadas (no seleccionables)
APERTURES_PENDING = ('annular', 'hexagonal')

ZERNIKE_CONVENTIONS = ('fringe', 'noll')
FRINGE_MAX_TERMS = 37      # el conjunto Fringe estándar termina en Z37 = (12, 0)


# ═══════════════════════════════════════════════════════════════════════════════
#  POLINOMIOS DE ZERNIKE
# ═══════════════════════════════════════════════════════════════════════════════

# Nombres por (n, m).  m > 0 → cos(mθ) ; m < 0 → sin(|m|θ)
_ZERNIKE_NM_NAMES = {
    (0, 0):  "Pistón",
    (1, 1):  "Tilt X (cos θ)",
    (1, -1): "Tilt Y (sin θ)",
    (2, 0):  "Desenfoque",
    (2, 2):  "Astigmatismo 0°/90° (cos 2θ)",
    (2, -2): "Astigmatismo ±45° (sin 2θ)",
    (3, 1):  "Coma X",
    (3, -1): "Coma Y",
    (3, 3):  "Trébol X (cos 3θ)",
    (3, -3): "Trébol Y (sin 3θ)",
    (4, 0):  "Esférica primaria",
    (4, 2):  "Astigmatismo secundario 0°/90°",
    (4, -2): "Astigmatismo secundario ±45°",
    (4, 4):  "Tetrafoil (cos 4θ)",
    (4, -4): "Tetrafoil (sin 4θ)",
    (5, 1):  "Coma secundaria X",
    (5, -1): "Coma secundaria Y",
    (5, 3):  "Trébol secundario X",
    (5, -3): "Trébol secundario Y",
    (6, 0):  "Esférica secundaria",
    (8, 0):  "Esférica terciaria",
}


def zernike_name(n, m):
    """Nombre descriptivo del polinomio Z_n^m."""
    return _ZERNIKE_NM_NAMES.get((int(n), int(m)), f"Z(n={n}, m={m:+d})")


def zernike_iso2nm(nterms):
    """
    Órdenes (n, m) de los primeros `nterms` polinomios en la ordenación
    histórica de zernikeISO2nm.m.  Coincide con la ordenación FRINGE
    (0-based, script Zk ↔ Fringe Z(k+1)) para los 36 primeros términos;
    Fringe Z37 = (12, 0) es un caso especial tratado en zernike_index_to_nm.

        Z0 (0,0)  Z1 (1,+1)  Z2 (1,-1)  Z3 (2,0)  Z4 (2,+2)  Z5 (2,-2)
        Z6 (3,+1) Z7 (3,-1)  Z8 (4,0)   Z9 (3,+3) Z10 (3,-3) ...

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


def zernike_noll2nm(j):
    """
    Órdenes (n, m) del polinomio de Noll j (1-based, Noll 1976).

    j par → cos(|m|θ) (m > 0) ; j impar → sin(|m|θ) (m < 0).
        Z1 (0,0)  Z2 (1,+1)  Z3 (1,-1)  Z4 (2,0)  Z5 (2,-2)  Z6 (2,+2)
        Z7 (3,-1) Z8 (3,+1)  Z9 (3,-3)  Z10 (3,+3) Z11 (4,0) ...
    """
    if j < 1:
        raise ValueError(f"Índice de Noll inválido: {j} (debe ser ≥ 1)")
    n = 0
    while j > (n + 1) * (n + 2) // 2:
        n += 1
    k = j - n * (n + 1) // 2            # posición dentro de la fila, 1..n+1
    if n % 2 == 0:
        m_abs = 2 * (k // 2)
    else:
        m_abs = 2 * ((k - 1) // 2) + 1
    if m_abs == 0:
        return n, 0
    return n, (m_abs if j % 2 == 0 else -m_abs)


def zernike_index_to_nm(t, convention='fringe'):
    """
    (n, m) del término `t` en la convención indicada.
      fringe : t 0-based (índice histórico del script; Fringe 1-based = t+1)
      noll   : t 1-based (índice de Noll estándar)
    """
    if convention == 'fringe':
        if t < 0 or t >= FRINGE_MAX_TERMS:
            raise ValueError(
                f"Índice Fringe inválido: {t}.  El conjunto Fringe estándar "
                f"tiene {FRINGE_MAX_TERMS} términos (índices 0..{FRINGE_MAX_TERMS - 1}).")
        if t == 36:
            return 12, 0                 # Fringe Z37 = esférica de 6º orden
        n_arr, m_arr = zernike_iso2nm(t + 1)
        return int(n_arr[t]), int(m_arr[t])
    if convention == 'noll':
        return zernike_noll2nm(t)
    raise ValueError(f"Convención de Zernike desconocida: {convention}")


def zernike_radial_coeffs(n, m_abs, norm='pico'):
    """
    Coeficientes del polinomio radial R_n^|m|(r), en orden descendente de
    potencias (compatible con numpy.polyval).

        R_n^m(r) = Σ_{s=0}^{(n-m)/2} (-1)^s (n-s)! /
                   [s! ((n+m)/2-s)! ((n-m)/2-s)!]  r^{n-2s}

    norm : 'pico' → máximo = 1 ;  'rms' → RMS sobre el disco unidad = 1
    """
    if (n + m_abs) % 2 != 0:
        raise ValueError(f"n={n}, |m|={m_abs}: n+|m| debe ser par")
    if m_abs > n:
        raise ValueError(f"n={n}, |m|={m_abs}: |m| debe ser ≤ n")

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
    Z_n^m(r, θ):   m ≥ 0 → R_n^m(r) cos(mθ) ;  m < 0 → R_n^|m|(r) sin(|m|θ)
    """
    R = np.polyval(zernike_radial_coeffs(n, abs(m), norm), r)
    if m >= 0:
        return R * np.cos(m * theta)
    return R * np.sin(-m * theta)


def build_zernike_matrix(terms, r, theta, norm='pico', convention='fringe'):
    """Matriz de diseño (N_puntos × N_terms) de Zernike."""
    A = np.zeros((len(r), len(terms)))
    for col, t in enumerate(terms):
        n, m = zernike_index_to_nm(t, convention)
        A[:, col] = eval_zernike_term(n, m, r, theta, norm)
    return A


# ═══════════════════════════════════════════════════════════════════════════════
#  POLINOMIOS DE CHEBYSHEV 2D (APERTURA RECTANGULAR)
# ═══════════════════════════════════════════════════════════════════════════════

def chebyshev_index2ij(t):
    """
    Grados (i, j) del término t (0-based) en ordenación triangular estándar:
    grado total k = i + j creciente; dentro de cada k, i decreciente.

        C0 (0,0)  C1 (1,0)  C2 (0,1)  C3 (2,0)  C4 (1,1)  C5 (0,2)
        C6 (3,0)  C7 (2,1)  C8 (1,2)  C9 (0,3)  ...
    """
    if t < 0:
        raise ValueError(f"Índice de Chebyshev inválido: {t} (0-based, ≥ 0)")
    k = 0
    while t > (k + 1) * (k + 2) // 2 - 1:
        k += 1
    pos = t - k * (k + 1) // 2           # 0..k dentro del grado k
    i = k - pos
    return i, k - i


_CHEB_NAMES = {
    (0, 0): "Pistón",
    (1, 0): "Tilt X",
    (0, 1): "Tilt Y",
    (2, 0): "Curvatura X (cilindro)",
    (1, 1): "Torsión (twist)",
    (0, 2): "Curvatura Y (cilindro)",
    (3, 0): "Cúbico X",
    (0, 3): "Cúbico Y",
    (2, 1): "Coma-like Y (x²·y)",
    (1, 2): "Coma-like X (x·y²)",
    (4, 0): "Cuártico X",
    (0, 4): "Cuártico Y",
    (2, 2): "x²·y² (silla doble)",
}


def chebyshev_name(i, j):
    return _CHEB_NAMES.get((int(i), int(j)), f"T{i}(x)·T{j}(y)")


_CHEB_RMS_CACHE = {}


def _chebyshev_rms_1d(n):
    """RMS de T_n(x) sobre [-1, 1] con peso uniforme (cuadratura de Gauss)."""
    if n not in _CHEB_RMS_CACHE:
        xg, wg = np.polynomial.legendre.leggauss(max(32, n + 8))
        c = np.zeros(n + 1)
        c[n] = 1.0
        Tn = np.polynomial.chebyshev.chebval(xg, c)
        _CHEB_RMS_CACHE[n] = math.sqrt(float(np.sum(wg * Tn ** 2)) / 2.0)
    return _CHEB_RMS_CACHE[n]


def eval_chebyshev_term(i, j, x, y, norm='pico'):
    """
    T_i(x)·T_j(y) con x, y ∈ [-1, 1].
    norm : 'pico' → máximo 1 ;  'rms' → RMS unidad sobre el rectángulo.
    """
    ci = np.zeros(i + 1); ci[i] = 1.0
    cj = np.zeros(j + 1); cj[j] = 1.0
    val = (np.polynomial.chebyshev.chebval(x, ci)
           * np.polynomial.chebyshev.chebval(y, cj))
    if norm == 'rms':
        val = val / (_chebyshev_rms_1d(i) * _chebyshev_rms_1d(j))
    return val


def build_chebyshev_matrix(terms, x, y, norm='pico'):
    """Matriz de diseño (N_puntos × N_terms) de Chebyshev 2D."""
    A = np.zeros((len(x), len(terms)))
    for col, t in enumerate(terms):
        i, j = chebyshev_index2ij(t)
        A[:, col] = eval_chebyshev_term(i, j, x, y, norm)
    return A


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERFAZ COMÚN DE BASES
# ═══════════════════════════════════════════════════════════════════════════════

def basis_key(aperture, convention='fringe'):
    """Base a usar: 'fringe' | 'noll' | 'chebyshev'."""
    if aperture in APERTURES_PENDING:
        raise NotImplementedError(
            f"La apertura '{aperture}' todavía no está implementada.")
    fam = APERTURE_BASIS[aperture]
    if fam == 'chebyshev':
        return 'chebyshev'
    if convention not in ZERNIKE_CONVENTIONS:
        raise ValueError(f"Convención desconocida: {convention}")
    return convention


def default_terms(basis, nterms):
    """Los `nterms` primeros términos de la base, en sus índices nativos."""
    if basis == 'noll':
        return list(range(1, nterms + 1))
    return list(range(nterms))


def term_info(basis, t):
    """
    Información de un término para imprimir.

    Devuelve (etiqueta, índice SurfCalc 1-based, orden, nombre).
    """
    if basis == 'fringe':
        n, m = zernike_index_to_nm(t, 'fringe')
        return f"Z{t}", t + 1, f"n={n} m={m:+d}", zernike_name(n, m)
    if basis == 'noll':
        n, m = zernike_noll2nm(t)
        return f"Z{t}", t, f"n={n} m={m:+d}", zernike_name(n, m)
    if basis == 'chebyshev':
        i, j = chebyshev_index2ij(t)
        return f"C{t}", t + 1, f"i={i} j={j}", chebyshev_name(i, j)
    raise ValueError(f"Base desconocida: {basis}")


def build_design_matrix(basis, terms, coords, norm='pico'):
    """
    Matriz de diseño para cualquier base.
      coords : dict con 'r' y 'theta' (Zernike) o 'x' e 'y' (Chebyshev),
               todos normalizados a la apertura.
    """
    if basis in ZERNIKE_CONVENTIONS:
        return build_zernike_matrix(terms, coords['r'], coords['theta'],
                                    norm, convention=basis)
    if basis == 'chebyshev':
        return build_chebyshev_matrix(terms, coords['x'], coords['y'], norm)
    raise ValueError(f"Base desconocida: {basis}")


# ═══════════════════════════════════════════════════════════════════════════════
#  GEOMETRÍA DE SUPERFICIE: SISTEMA LOCAL, ÁREAS NODALES Y NORMALES
# ═══════════════════════════════════════════════════════════════════════════════

def compute_bestfit_normal(coor):
    """
    Normal del plano best-fit de la nube de puntos (SVD / PCA): dirección de
    mínima varianza.  Se orienta con componente Z ≥ 0 (mismo convenio que
    SurfCalc: "every Normal Type resolves to an axis with a non-negative Z").

    Devuelve un vector unitario (3,).
    """
    centered = coor - coor.mean(axis=0)
    _, _, Vt = np.linalg.svd(centered, full_matrices=False)
    normal = Vt[-1]
    if normal[2] < 0:
        normal = -normal
    return normal / np.linalg.norm(normal)


def rotation_to_z(normal):
    """
    Matriz de giro R (3×3) que lleva `normal` a +Z con la rotación mínima
    (fórmula de Rodrigues), conservando lo más posible la orientación de X, Y.
    """
    n = np.asarray(normal, dtype=float)
    n = n / np.linalg.norm(n)
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(n, z)
    s = np.linalg.norm(v)
    c = float(n @ z)
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    vx = np.array([[0, -v[2], v[1]],
                   [v[2], 0, -v[0]],
                   [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)


def to_local_frame(coor, disp):
    """
    Gira coordenadas y desplazamientos al sistema local de la superficie
    (normal best-fit → +Z).  Equivale a "Normal Type: Best-fit Plane (Auto)"
    de SurfCalc.  No traslada el origen, para que los giros de sólido rígido
    se sigan refiriendo al mismo punto que en el sistema global.

    Devuelve
    --------
    coor_l, disp_l : ndarray (N, 3)
    info           : dict con 'normal', 'R' y 'tilt_deg' (ángulo normal–Z)
    """
    normal = compute_bestfit_normal(coor)
    R = rotation_to_z(normal)
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, float(normal[2])))))
    return coor @ R.T, disp @ R.T, {'normal': normal, 'R': R, 'tilt_deg': tilt}


def compute_nodal_areas_and_normals(coor, area_threshold=0.0):
    """
    Triangulación de Delaunay en XY.  Áreas nodales (área proyectada del
    triángulo / 3) y normales unitarias en cada nodo.

    Equivale a la triangulación de extract_rigid.m / lee.m.

    area_threshold : área mínima (en XY, unidades del modelo²) para aceptar
        un triángulo.  ¡Ojo! es absoluta: MATLAB usaba 1 para un espejo de
        1,2 m en mm; en espejos pequeños un umbral de 1 descarta casi toda
        la malla.  Por defecto 0 (sólo se descartan triángulos de área nula).

    Devuelve
    --------
    simplices : ndarray (M, 3)   Triángulos válidos
    an        : ndarray (N,)     Áreas nodales normalizadas (suma = 1);
                                 0 en nodos que no pertenecen a ningún
                                 triángulo válido (p. ej. nodos duplicados)
    normals   : ndarray (N, 3)   Normales unitarias (0 en esos nodos)
    """
    npts = len(coor)
    tri = Delaunay(coor[:, :2])
    simplices = tri.simplices

    p0 = coor[simplices[:, 0], :2]
    p1 = coor[simplices[:, 1], :2]
    p2 = coor[simplices[:, 2], :2]
    v12 = p1 - p0
    v13 = p2 - p0
    # Doble del área proyectada en XY
    area2d = np.abs(v12[:, 0] * v13[:, 1] - v13[:, 0] * v12[:, 1])

    valid = area2d > max(area_threshold, 0.0)
    simplices = simplices[valid]
    area2d = area2d[valid]

    # Normales de triángulo en 3D, orientadas con la normal global
    p0 = coor[simplices[:, 0]]
    p1 = coor[simplices[:, 1]]
    p2 = coor[simplices[:, 2]]
    face_n = np.cross(p1 - p0, p2 - p0)
    global_normal = compute_bestfit_normal(coor)
    sign_n = np.sign(face_n @ global_normal)
    sign_n[sign_n == 0] = 1.0
    face_n *= sign_n[:, np.newaxis]

    an = np.zeros(npts)
    for j in range(3):
        np.add.at(an, simplices[:, j], area2d / 3.0)
    if an.sum() > 0:
        an /= an.sum()

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
    Elimina el movimiento de sólido rígido y devuelve el desplazamiento
    normal residual.  Traducción de extract_rigid.m (IAC).

        rigidmodes = [Tx, Ty, Tz, Rx, Ry, Rz]   0 = conservar, 1 = eliminar

    Ajuste por mínimos cuadrados del campo 3D (dX, dY, dZ) ponderado por
    √(área nodal).  Los giros se toman respecto al ORIGEN de coordenadas.

    Devuelve
    --------
    un  : ndarray (N,)   Desplazamiento normal residual (NaN en nodos sin
                         área, que no pertenecen a ningún triángulo)
    an  : ndarray (N,)   Áreas nodales normalizadas
    pos : ndarray (6,)   Coeficientes [Tx, Ty, Tz, Rx, Ry, Rz]
    """
    _, an, node_norms = compute_nodal_areas_and_normals(coor, area_threshold)

    pos = np.zeros(6)
    disp_corr = disp.astype(float).copy()
    active = [i for i, f in enumerate(rigidmodes) if f != 0]

    if active:
        an_sqrt = np.sqrt(an)
        npts = len(coor)
        A = np.zeros((3 * npts, 6))
        A[0:npts, 0] = an_sqrt                       # Tx → dX
        A[npts:2 * npts, 1] = an_sqrt                # Ty → dY
        A[2 * npts:3 * npts, 2] = an_sqrt            # Tz → dZ
        A[npts:2 * npts, 3] = -coor[:, 2] * an_sqrt  # Rx: dY = -Z·Rx
        A[2 * npts:3 * npts, 3] = coor[:, 1] * an_sqrt   # dZ = +Y·Rx
        A[0:npts, 4] = coor[:, 2] * an_sqrt          # Ry: dX = +Z·Ry
        A[2 * npts:3 * npts, 4] = -coor[:, 0] * an_sqrt  # dZ = -X·Ry
        A[0:npts, 5] = -coor[:, 1] * an_sqrt         # Rz: dX = -Y·Rz
        A[npts:2 * npts, 5] = coor[:, 0] * an_sqrt   # dY = +X·Rz

        A_act = A[:, active]
        b = (disp_corr * an_sqrt[:, np.newaxis]).ravel(order='F')
        coef, *_ = np.linalg.lstsq(A_act, b, rcond=None)
        pos[active] = coef

        # Campo rígido SIN ponderar (válido también en nodos de área nula)
        rigid = np.zeros_like(disp_corr)
        for k, idx in enumerate(active):
            c = coef[k]
            if idx == 0:
                rigid[:, 0] += c
            elif idx == 1:
                rigid[:, 1] += c
            elif idx == 2:
                rigid[:, 2] += c
            elif idx == 3:
                rigid[:, 1] += -coor[:, 2] * c
                rigid[:, 2] += coor[:, 1] * c
            elif idx == 4:
                rigid[:, 0] += coor[:, 2] * c
                rigid[:, 2] += -coor[:, 0] * c
            elif idx == 5:
                rigid[:, 0] += -coor[:, 1] * c
                rigid[:, 1] += coor[:, 0] * c
        disp_corr -= rigid

    un = (disp_corr * node_norms).sum(axis=1)
    un[an <= 0] = np.nan          # nodos fuera de la triangulación
    return un, an, pos


# ═══════════════════════════════════════════════════════════════════════════════
#  APERTURAS
# ═══════════════════════════════════════════════════════════════════════════════

def surface_centroid(xy, an=None):
    """
    Centro geométrico de la superficie mallada.  Con áreas nodales es el
    centroide ponderado por área (independiente de la densidad de malla);
    sin ellas, la media de los nodos.
    """
    if an is not None and np.sum(an) > 0:
        w = an / np.sum(an)
        return float(w @ xy[:, 0]), float(w @ xy[:, 1])
    return float(xy[:, 0].mean()), float(xy[:, 1].mean())


def _center(xy, center):
    if center is None:
        return float(xy[:, 0].mean()), float(xy[:, 1].mean())
    return float(center[0]), float(center[1])


def aperture_circular(xy, radius=None, center=None):
    """
    Máscara circular.

    center : (xc, yc) o None (media de los nodos)
    radius : radio de normalización; None → distancia máxima al centro

    Devuelve mask (N,), r_norm (M,), theta (M,)
    """
    cx, cy = _center(xy, center)
    xc, yc = xy[:, 0] - cx, xy[:, 1] - cy
    r = np.hypot(xc, yc)
    if radius is None:
        radius = r.max()
    mask = r <= radius * (1 + 1e-9)
    return mask, r[mask] / radius, np.arctan2(yc[mask], xc[mask])


def aperture_rectangular(xy, width=None, height=None, center=None):
    """
    Máscara rectangular (lados paralelos a X e Y) y coordenadas normalizadas
    a [-1, 1] para Chebyshev.

    Devuelve mask (N,), x_norm (M,), y_norm (M,)
    """
    cx, cy = _center(xy, center)
    xc, yc = xy[:, 0] - cx, xy[:, 1] - cy
    if width is None:
        width = 2.0 * np.abs(xc).max()
    if height is None:
        height = 2.0 * np.abs(yc).max()
    hw, hh = width / 2.0, height / 2.0
    tol = 1 + 1e-9
    mask = (np.abs(xc) <= hw * tol) & (np.abs(yc) <= hh * tol)
    return mask, np.clip(xc[mask] / hw, -1, 1), np.clip(yc[mask] / hh, -1, 1)


def aperture_hexagonal(xy, circumradius=None, center=None):
    """
    Máscara hexagonal regular (vértice en +X).  PENDIENTE: la base de
    polinomios de segmento hexagonal no está implementada, por lo que esta
    apertura no es seleccionable todavía.
    """
    cx, cy = _center(xy, center)
    xc, yc = xy[:, 0] - cx, xy[:, 1] - cy
    if circumradius is None:
        circumradius = np.hypot(xc, yc).max()
    apothem = circumradius * math.sqrt(3) / 2.0
    c1 = np.abs(yc) <= apothem
    c2 = np.abs(xc * (math.sqrt(3) / 2) + yc * 0.5) <= apothem
    c3 = np.abs(xc * (math.sqrt(3) / 2) - yc * 0.5) <= apothem
    mask = c1 & c2 & c3
    return (mask, np.hypot(xc[mask], yc[mask]) / circumradius,
            np.arctan2(yc[mask], xc[mask]))


def apply_aperture(xy, un, an, aperture, radius=None, width=None, height=None,
                   center=None):
    """
    Selecciona los nodos de la apertura y devuelve sus coordenadas
    normalizadas para la base correspondiente.

    Se excluyen los nodos con un NaN (sin área en la triangulación).
    El centro por defecto es el centroide ponderado por área.

    Devuelve
    --------
    mask   : ndarray (N,) bool
    coords : dict  ('r','theta') para Zernike o ('x','y') para Chebyshev
    geom   : dict  geometría de la apertura (para dibujar el contorno)
    """
    if aperture in APERTURES_PENDING:
        raise NotImplementedError(
            f"La apertura '{aperture}' todavía no está implementada.")
    valid = np.isfinite(un) & (an > 0)
    if center is None:
        center = surface_centroid(xy[valid], an[valid])
    cx, cy = center

    if aperture == 'circular':
        if radius is None:
            radius = float(np.hypot(xy[valid, 0] - cx, xy[valid, 1] - cy).max())
        mask, r, th = aperture_circular(xy, radius, center)
        keep = valid[mask]
        mask &= valid
        coords = {'r': r[keep], 'theta': th[keep]}
        geom = {'type': 'circular', 'center': center, 'radius': radius}
    elif aperture == 'rectangular':
        if width is None:
            width = 2.0 * float(np.abs(xy[valid, 0] - cx).max())
        if height is None:
            height = 2.0 * float(np.abs(xy[valid, 1] - cy).max())
        mask, xn, yn = aperture_rectangular(xy, width, height, center)
        keep = valid[mask]
        mask &= valid
        coords = {'x': xn[keep], 'y': yn[keep]}
        geom = {'type': 'rectangular', 'center': center,
                'width': width, 'height': height}
    else:
        raise ValueError(f"Apertura desconocida: {aperture}")
    return mask, coords, geom


def aperture_area(geom):
    """Área teórica de la apertura."""
    if geom['type'] == 'circular':
        return math.pi * geom['radius'] ** 2
    if geom['type'] == 'rectangular':
        return geom['width'] * geom['height']
    return None


def mesh_coverage(xy, an, geom):
    """
    Fracción del área teórica de la apertura cubierta por la malla
    (casco convexo de los nodos válidos).  < ~0.8 indica modelo parcial.
    """
    from scipy.spatial import ConvexHull
    pts = xy[an > 0]
    area_ap = aperture_area(geom)
    if len(pts) < 3 or not area_ap:
        return None
    try:
        return ConvexHull(pts).volume / area_ap      # en 2D .volume = área
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#  AJUSTE POLINÓMICO SOBRE DATOS DISPERSOS
# ═══════════════════════════════════════════════════════════════════════════════

def fit_weighted_ls(u, A, weights=None):
    """
    Mínimos cuadrados (ponderados si `weights` no es None):
        minimizar  Σ wᵢ (Aᵢ·c − uᵢ)²
    Devuelve coeffs, residual.
    """
    if weights is not None:
        w = np.sqrt(np.asarray(weights, dtype=float))
        coeffs, *_ = np.linalg.lstsq(A * w[:, np.newaxis], u * w, rcond=None)
    else:
        coeffs, *_ = np.linalg.lstsq(A, u, rcond=None)
    return coeffs, u - A @ coeffs


def fit_surface(u, coords, basis, terms, norm='pico', weights=None):
    """
    Ajuste de la base `basis` ('fringe' | 'noll' | 'chebyshev').
    Por defecto debe pasarse weights = áreas nodales (WLS, como SurfCalc).

    Devuelve coeffs, residual, A
    """
    A = build_design_matrix(basis, terms, coords, norm)
    coeffs, residual = fit_weighted_ls(u, A, weights)
    return coeffs, residual, A


def zernike_fit_scatter(un, r_norm, theta, terms, norm='pico', weights=None,
                        convention='fringe'):
    """
    Ajuste de Zernike (compatibilidad con versiones anteriores).
    weights = áreas nodales → WLS ;  None → LS ordinario.
    """
    return fit_surface(un, {'r': r_norm, 'theta': theta}, convention,
                       terms, norm, weights)


# ═══════════════════════════════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ═══════════════════════════════════════════════════════════════════════════════

def rms_area_weighted(values, an):
    """
    RMS ponderado por área:  sqrt( Σ aᵢ uᵢ² / Σ aᵢ ).  Ignora NaN.
    (No resta la media; ver std_area_weighted.)
    """
    v = np.asarray(values, dtype=float)
    a = np.asarray(an, dtype=float)
    ok = np.isfinite(v) & (a > 0)
    if not ok.any():
        return float('nan')
    return math.sqrt(float(np.sum(a[ok] * v[ok] ** 2) / np.sum(a[ok])))


def std_area_weighted(values, an):
    """RMS respecto a la media ponderada por área (desviación típica)."""
    v = np.asarray(values, dtype=float)
    a = np.asarray(an, dtype=float)
    ok = np.isfinite(v) & (a > 0)
    if not ok.any():
        return float('nan')
    mean = np.sum(a[ok] * v[ok]) / np.sum(a[ok])
    return math.sqrt(float(np.sum(a[ok] * (v[ok] - mean) ** 2) / np.sum(a[ok])))


def peak_to_valley(values):
    """Pico a valle (ignora NaN)."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    return float(v.max() - v.min()) if v.size else float('nan')


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRADA/SALIDA
# ═══════════════════════════════════════════════════════════════════════════════

def _read_table(fname):
    data = np.loadtxt(fname)
    if data.ndim == 1:
        data = data[np.newaxis, :]
    if data.shape[1] < 6:
        raise ValueError(
            f"El fichero debe tener 6 columnas (X Y Z dX dY dZ) o "
            f"7 columnas (id X Y Z dX dY dZ). Encontradas: {data.shape[1]}")
    return data


def _case_ids(data):
    """
    Si la primera columna tiene valores repetidos no puede ser un número de
    nodo: es un identificador de CASO DE CARGA (ficheros con varios casos
    apilados, como AARESULTADOS2.TXT, que proc.m separa en bloques).
    Devuelve la lista de casos, o None si el fichero tiene un único caso.
    """
    if data.shape[1] < 7:
        return None
    ids = data[:, 0]
    uniq = np.unique(ids)
    if len(uniq) == len(ids) or len(uniq) == 1:
        return None
    return [int(v) if float(v).is_integer() else float(v) for v in uniq]


def list_load_cases(fname):
    """Casos de carga presentes en el fichero (None si sólo hay uno)."""
    return _case_ids(_read_table(fname))


def load_fem_data(fname, case=None):
    """
    Carga el fichero TXT de resultados FEM.
      7+ columnas : id X Y Z dX dY dZ [extras ignoradas]
      6 columnas  : X Y Z dX dY dZ

    Si la primera columna contiene valores repetidos se interpreta como
    número de caso de carga y hay que indicar `case`; si no se indica se
    produce un error (mezclar casos daría resultados sin sentido).

    Devuelve node (N,), coor (N, 3), disp (N, 3)
    """
    data = _read_table(fname)
    cases = _case_ids(data)
    if cases is not None:
        if case is None:
            raise ValueError(
                f"El fichero contiene {len(cases)} casos de carga apilados "
                f"(primera columna = {cases}).  Indica cuál analizar "
                f"(--case en línea de comandos o 'Caso de carga' en la GUI).")
        sel = data[:, 0] == float(case)
        if not sel.any():
            raise ValueError(f"El caso {case} no existe en el fichero. Casos: {cases}")
        data = data[sel]
        return np.arange(len(data), dtype=float), data[:, 1:4], data[:, 4:7]
    if data.shape[1] >= 7:
        return data[:, 0], data[:, 1:4], data[:, 4:7]
    return np.arange(len(data), dtype=float), data[:, 0:3], data[:, 3:6]


def check_duplicates(coor, tol_rel=1e-9):
    """Número de nodos con coordenadas XY repetidas."""
    span = float(np.ptp(coor[:, :2], axis=0).max()) or 1.0
    q = np.round(coor[:, :2] / (span * tol_rel)).astype(np.int64)
    _, counts = np.unique(q, axis=0, return_counts=True)
    return int((counts - 1).clip(min=0).sum())


def print_term_table(basis, nterms=21):
    """Imprime la tabla de términos de la base."""
    titles = {'fringe': "Zernike Fringe (índices del script 0-based)",
              'noll': "Zernike Noll (índices 1-based)",
              'chebyshev': "Chebyshev 2D rectangular (índices 0-based)"}
    print(f"\n  {titles[basis]}")
    print(f"  {'Término':>8}  {'SurfCalc #':>10}  {'Orden':>12}  Nombre")
    print(f"  {'-'*8:>8}  {'-'*10:>10}  {'-'*12:>12}  ------")
    for t in default_terms(basis, nterms):
        lab, sc, order, name = term_info(basis, t)
        print(f"  {lab:>8}  {sc:>10d}  {order:>12}  {name}")


def print_rigid_body_results(pos, rigidmodes):
    """Imprime los coeficientes de sólido rígido extraídos."""
    labels = ['Tx', 'Ty', 'Tz', 'Rx', 'Ry', 'Rz']
    activos = [(labels[i], pos[i]) for i in range(6) if rigidmodes[i]]
    if activos:
        print("\n  Coeficientes de sólido rígido eliminados:")
        for name, val in activos:
            print(f"    {name} = {val:+.6g}")


def format_fit_table(basis, terms, coeffs):
    """Tabla de coeficientes como lista de líneas de texto."""
    lines = [f"  {'Término':>8}  {'SurfCalc #':>10}  {'Orden':>12}  "
             f"{'Coeficiente':>14}  Nombre",
             f"  {'-'*8:>8}  {'-'*10:>10}  {'-'*12:>12}  {'-'*14:>14}  ------"]
    for t, c in zip(terms, coeffs):
        lab, sc, order, name = term_info(basis, t)
        lines.append(f"  {lab:>8}  {sc:>10d}  {order:>12}  {c:>+14.6e}  {name}")
    return lines


# ═══════════════════════════════════════════════════════════════════════════════
#  VISUALIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def plot_results(coor, un, mask, residual, aperture_name, output_file='fem_analysis.png'):
    """Figura con el desplazamiento normal y el residuo del ajuste."""
    import matplotlib.pyplot as plt
    import matplotlib.tri as mtri

    x, y = coor[:, 0], coor[:, 1]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    ok = np.isfinite(un)
    triang_full = mtri.Triangulation(x[ok], y[ok])
    cf1 = axes[0].tricontourf(triang_full, un[ok], levels=64, cmap='RdBu_r')
    plt.colorbar(cf1, ax=axes[0], label='Desplazamiento normal')
    axes[0].set_title('Desplazamiento normal\n(tras quitar sólido rígido)')
    axes[0].set_aspect('equal')
    axes[0].set_xlabel('X')
    axes[0].set_ylabel('Y')

    un_res_full = np.full(len(coor), np.nan)
    un_res_full[mask] = residual
    valid = np.isfinite(un_res_full)
    if valid.sum() > 3:
        triang_ap = mtri.Triangulation(x[valid], y[valid])
        cf2 = axes[1].tricontourf(triang_ap, un_res_full[valid], levels=64, cmap='RdBu_r')
        plt.colorbar(cf2, ax=axes[1], label='Residuo')
    axes[1].set_title(f'Residuo tras el ajuste\n(apertura {aperture_name})')
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
        help="Fichero TXT con resultados FEM (node X Y Z dX dY dZ  ó  X Y Z dX dY dZ)")
    parser.add_argument(
        "--case", type=float, default=None,
        help="Caso de carga a analizar si el fichero contiene varios casos "
             "apilados (primera columna = nº de caso).")
    parser.add_argument(
        "--rigid", nargs=6, type=int, default=[0, 0, 1, 0, 0, 0],
        metavar=("Tx", "Ty", "Tz", "Rx", "Ry", "Rz"),
        help="Modos de sólido rígido a eliminar (0/1).  Default: 0 0 1 0 0 0")
    parser.add_argument(
        "--area-threshold", type=float, default=0.0,
        help="Área mínima ABSOLUTA (unidades²) de los triángulos de Delaunay. "
             "Default: 0 (sólo se descartan triángulos degenerados).")
    parser.add_argument(
        "--frame", choices=["global", "bestfit"], default="global",
        help="Sistema de referencia: 'global' (Z del fichero = eje óptico, como "
             "el MATLAB original) o 'bestfit' (girar a la normal del plano "
             "best-fit, como SurfCalc 'Best-fit Plane (Auto)').  No usar "
             "'bestfit' con modelos parciales de espejos curvos ni segmentos "
             "fuera de eje.  Default: global")
    parser.add_argument(
        "--center", nargs=2, type=float, default=None, metavar=("XC", "YC"),
        help="Centro de la apertura.  Default: centroide de área de la malla "
             "(para modelos parciales/simetría hay que darlo, p. ej. 0 0).")
    parser.add_argument(
        "--aperture", choices=list(APERTURE_BASIS) + list(APERTURES_PENDING),
        default="circular",
        help="Forma de la apertura: circular (Zernike) o rectangular (Chebyshev). "
             "'annular' y 'hexagonal' están pendientes de implementar.")
    parser.add_argument(
        "--convention", choices=ZERNIKE_CONVENTIONS, default="fringe",
        help="Convención de Zernike para la apertura circular.  Default: fringe")
    parser.add_argument("--radius", type=float, default=None,
                        help="Radio de normalización (circular).  Default: auto")
    parser.add_argument("--width", type=float, default=None,
                        help="Anchura X (rectangular).  Default: auto")
    parser.add_argument("--height", type=float, default=None,
                        help="Altura Y (rectangular).  Default: auto")
    parser.add_argument(
        "--terms", nargs="+", type=int, default=None,
        help="Índices de los términos a ajustar en la convención de la base "
             "(Fringe y Chebyshev 0-based, Noll 1-based).  Default: pistón, "
             "tilts y desenfoque/curvaturas.  Ver --list-terms")
    parser.add_argument(
        "--nterms", type=int, default=None,
        help="Ajustar los N primeros términos de la base (igual que la GUI). "
             "Alternativa a --terms.")
    parser.add_argument("--norm", choices=["pico", "rms"], default="pico",
                        help="Normalización de los polinomios.  Default: pico")
    parser.add_argument(
        "--no-wls", action="store_true",
        help="Ajuste por LS ordinario en vez de WLS ponderado por área "
             "(por defecto WLS, como SurfCalc).")
    parser.add_argument("--no-zernike", action="store_true",
                        help="Omitir el ajuste polinómico")
    parser.add_argument("--plot", action="store_true",
                        help="Generar y guardar figura de resultados")
    parser.add_argument("--plot-file", default="fem_analysis.png",
                        help="Fichero de imagen.  Default: fem_analysis.png")
    parser.add_argument("--list-terms", action="store_true",
                        help="Mostrar la tabla de términos de la base y salir")

    args = parser.parse_args()

    if args.aperture in APERTURES_PENDING:
        parser.error(f"La apertura '{args.aperture}' todavía no está implementada "
                     f"(disponibles: {', '.join(APERTURE_BASIS)}).")
    basis = basis_key(args.aperture, args.convention)

    if args.list_terms:
        print_term_table(basis)
        sys.exit(0)
    if args.fname is None:
        parser.error("Se requiere el nombre del fichero de datos FEM.")

    if args.nterms is not None and args.terms is not None:
        parser.error("Usa --terms o --nterms, no ambos.")
    if args.nterms is not None:
        if args.nterms <= 0:
            args.no_zernike = True
            args.terms = [0]
        else:
            args.terms = default_terms(basis, args.nterms)
    if args.terms is None:
        args.terms = default_terms(basis, 6 if basis == 'chebyshev' else 4)
    terms = sorted(set(args.terms))
    try:
        for t in terms:
            term_info(basis, t)
    except ValueError as e:
        parser.error(str(e))

    # ── Carga ────────────────────────────────────────────────────────────────
    print(f"\n{'═'*60}\n  fem_mirror_analysis.py\n{'═'*60}")
    print(f"\n  Leyendo: {args.fname}")
    try:
        _, coor, disp = load_fem_data(args.fname, args.case)
    except ValueError as e:
        parser.error(str(e))
    if args.case is not None:
        print(f"  Caso de carga: {args.case:g}")
    print(f"  Nodos leídos: {len(coor)}")
    for k, ax in enumerate("XYZ"):
        print(f"  {ax} ∈ [{coor[:, k].min():.4g}, {coor[:, k].max():.4g}]")
    ndup = check_duplicates(coor)
    if ndup:
        print(f"  ⚠  {ndup} nodos con XY repetidas: se excluyen del análisis "
              f"(quedan fuera de la triangulación).")

    # ── Sistema de referencia ────────────────────────────────────────────────
    nbf = compute_bestfit_normal(coor)
    tilt = math.degrees(math.acos(min(1.0, float(nbf[2]))))
    print(f"\n  Normal del plano best-fit: ({nbf[0]:+.5f}, {nbf[1]:+.5f}, "
          f"{nbf[2]:+.5f})  → {tilt:.4f}° respecto a Z")
    if args.frame == 'bestfit':
        coor, disp, _ = to_local_frame(coor, disp)
        print("  Sistema: plano best-fit (coordenadas y desplazamientos girados; "
              "Tx..Rz en ese sistema).")
    else:
        print("  Sistema: global (Z del fichero = eje óptico).")
        if tilt > 1.0:
            print("  ⚠  La superficie está inclinada respecto a Z.  Si es plana o "
                  "Z no es el eje óptico, usa --frame bestfit.")

    # ── Sólido rígido ────────────────────────────────────────────────────────
    rigid_flags = tuple(args.rigid)
    active_names = [n for n, f in zip(['Tx', 'Ty', 'Tz', 'Rx', 'Ry', 'Rz'], rigid_flags) if f]
    print(f"\n  Eliminando sólido rígido: {active_names if active_names else 'ninguno'}")
    un, an, pos = extract_rigid(coor, disp, rigid_flags, args.area_threshold)
    nbad = int(np.sum(~np.isfinite(un)))
    if nbad:
        print(f"  ⚠  {nbad} nodos sin área en la triangulación (excluidos).")
    print_rigid_body_results(pos, rigid_flags)

    print(f"\n  ── Desplazamiento normal (toda la superficie) ──")
    print(f"  RMS (pond. por área):        {rms_area_weighted(un, an):.6g}")
    print(f"  RMS resp. media (std):       {std_area_weighted(un, an):.6g}")
    print(f"  Pico a valle (P-V):          {peak_to_valley(un):.6g}")

    # ── Ajuste polinómico ────────────────────────────────────────────────────
    mask = np.zeros(len(coor), dtype=bool)
    residual = np.array([])
    if not args.no_zernike:
        fam = "Chebyshev 2D" if basis == 'chebyshev' else f"Zernike {basis.capitalize()}"
        print(f"\n  ── Ajuste {fam} — apertura {args.aperture} ──")
        mask, coords, geom = apply_aperture(
            coor[:, :2], un, an, args.aperture,
            radius=args.radius, width=args.width, height=args.height,
            center=tuple(args.center) if args.center else None)
        print(f"  Centro de la apertura ({'usuario' if args.center else 'centroide de área'}): "
              f"({geom['center'][0]:.4g}, {geom['center'][1]:.4g})")
        if geom['type'] == 'circular':
            print(f"  Radio de normalización: {geom['radius']:.6g}")
        else:
            print(f"  Anchura × altura: {geom['width']:.6g} × {geom['height']:.6g}")
        print(f"  Nodos en apertura: {mask.sum()} / {len(mask)}")
        cov = mesh_coverage(coor[:, :2], an, geom)
        if cov is not None and cov < 0.82:
            print(f"  ⚠  La malla cubre sólo ~{cov*100:.0f}% de la apertura: parece un "
                  f"modelo parcial (simetría).  Revisa el centro (--center) y el radio.")
        if mask.sum() < len(terms):
            print("  ⚠  Menos puntos que términos: ajuste inestable.")

        un_ap = un[mask]
        an_ap = an[mask] / an[mask].sum()
        coeffs, residual, _ = fit_surface(
            un_ap, coords, basis, terms, args.norm,
            weights=None if args.no_wls else an_ap)
        print(f"  Método: {'LS ordinario (--no-wls)' if args.no_wls else 'WLS ponderado por área'}"
              f" · normalización '{args.norm}'\n")
        print("\n".join(format_fit_table(basis, terms, coeffs)))

        rb, ra = rms_area_weighted(un_ap, an_ap), rms_area_weighted(residual, an_ap)
        print(f"\n  Dentro de la apertura — ANTES del ajuste:")
        print(f"    RMS = {rb:.6g}   (std = {std_area_weighted(un_ap, an_ap):.6g})")
        print(f"    P-V = {peak_to_valley(un_ap):.6g}")
        print(f"\n  Dentro de la apertura — RESIDUO tras el ajuste:")
        print(f"    RMS = {ra:.6g}   (std = {std_area_weighted(residual, an_ap):.6g})")
        print(f"    P-V = {peak_to_valley(residual):.6g}")
        if rb > 0:
            print(f"    Reducción de RMS: {(1.0 - ra / rb) * 100.0:.1f}%")

    print(f"\n{'═'*60}\n")

    if args.plot:
        if mask.any():
            plot_results(coor, un, mask, residual, args.aperture, args.plot_file)
        else:
            import matplotlib.pyplot as plt
            import matplotlib.tri as mtri
            ok = np.isfinite(un)
            fig, ax = plt.subplots(figsize=(8, 7))
            cf = ax.tricontourf(mtri.Triangulation(coor[ok, 0], coor[ok, 1]),
                                un[ok], levels=64, cmap='RdBu_r')
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
