#!/usr/bin/env python3
"""
Interfaz gráfica para fem_mirror_analysis.py
Requiere: tkinter (incluido en Python estándar), numpy, scipy, matplotlib
"""
import sys
import os
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

# ── Añadir el directorio del script al path para importar fem_mirror_analysis ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Logo del departamento (PNG 104×60, embebido como base64) ──────────
_LOGO_B64 = (
    "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"
)


# ═══════════════════════════════════════════════════════════════════
#  UTILIDADES DE VISUALIZACIÓN
# ═══════════════════════════════════════════════════════════════════

def _draw_aperture_boundary(ax, aperture, cx, cy, xc_all, yc_all, params):
    """
    Dibuja el contorno de la apertura (línea amarilla discontinua) sobre 'ax'.

    cx, cy       : centroide de los nodos en coordenadas originales
    xc_all, yc_all : coordenadas centradas de TODOS los nodos (para auto-radio)
    """
    import numpy as np
    import matplotlib.patches as mpatches

    kw_line   = dict(color='gold', lw=1.5, ls='--', zorder=5)
    kw_patch  = dict(edgecolor='gold', facecolor='none', lw=1.5, ls='--', zorder=5)

    if aperture == 'Circular':
        r = float(params['radius']) if params.get('radius') else np.hypot(xc_all, yc_all).max()
        ax.add_patch(mpatches.Circle((cx, cy), r, **kw_patch))

    elif aperture == 'Hexagonal':
        R = float(params['hexradius']) if params.get('hexradius') else np.hypot(xc_all, yc_all).max()
        # Hexágono regular con vértice apuntando a la derecha (ángulo 0)
        angles = [k * (2 * 3.14159265 / 6) for k in range(7)]
        hx = [cx + R * __import__('math').cos(a) for a in angles]
        hy = [cy + R * __import__('math').sin(a) for a in angles]
        ax.plot(hx, hy, **kw_line)

    elif aperture == 'Cuadrada':
        side = float(params['side']) if params.get('side') else 2.0 * max(float(np.abs(xc_all).max()), float(np.abs(yc_all).max()))
        half = side / 2.0
        ax.add_patch(mpatches.Rectangle((cx - half, cy - half), side, side, **kw_patch))

    elif aperture == 'Rectangular':
        w = float(params['width'])  if params.get('width')  else 2.0 * float(np.abs(xc_all).max())
        h = float(params['height']) if params.get('height') else 2.0 * float(np.abs(yc_all).max())
        ax.add_patch(mpatches.Rectangle((cx - w / 2, cy - h / 2), w, h, **kw_patch))


# ═══════════════════════════════════════════════════════════════════
#  LÓGICA DE ANÁLISIS  (se ejecuta en hilo secundario)
# ═══════════════════════════════════════════════════════════════════

def run_analysis(params, log, schedule, embed_fig=None, result_store=None):
    """
    Ejecuta el análisis FEM completo.

    params       : dict con todos los parámetros de la GUI
    log          : función log(texto) para escribir en el widget de resultados
    schedule     : función schedule(ms, fn) para ejecutar fn en el hilo principal
    embed_fig    : función embed_fig(fig) para mostrar la figura en la GUI
                   (si es None se usa plt.show() en ventana externa)
    result_store : lista de un elemento [None] donde se guardan los datos
                   del análisis para la vista 3D posterior
    """
    try:
        import numpy as np
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        import importlib

        # ── Importar el módulo de análisis ──────────────────────────────
        m = importlib.import_module('fem_mirror_analysis')

        # ── 1. Cargar datos ─────────────────────────────────────────────
        log("Cargando datos FEM…\n")
        _, coor, disp = m.load_fem_data(params['fname'])
        log(f"  {len(coor):,} nodos leídos.\n\n")

        # ── 2. Extraer sólido rígido ─────────────────────────────────────
        rigid = params['rigid']
        active = [('Tx','Ty','Tz','Rx','Ry','Rz')[i] for i, v in enumerate(rigid) if v]
        if active:
            log(f"Eliminando modos de sólido rígido: {', '.join(active)}\n")
        else:
            log("No se eliminan modos de sólido rígido.\n")

        un, an, pos = m.extract_rigid(coor, disp, rigid)

        labels = ['Tx', 'Ty', 'Tz', 'Rx', 'Ry', 'Rz']
        for i, lbl in enumerate(labels):
            if rigid[i]:
                log(f"  {lbl} = {pos[i]:+.6e}\n")

        rms_total = m.rms_area_weighted(un, an)
        pv_total  = m.peak_to_valley(un)
        log(f"\nRMS desplazamiento normal : {rms_total:.6e}\n")
        log(f"Peak-to-valley            : {pv_total:.6e}\n")

        # ── 3. Máscara de apertura ───────────────────────────────────────
        aperture = params['aperture']
        xy = coor[:, :2]

        log(f"\nCalculando apertura '{aperture}'…\n")
        if aperture == 'Circular':
            kw = {}
            if params.get('radius'): kw['radius'] = float(params['radius'])
            mask, r_norm, theta = m.aperture_circular(xy, **kw)
        elif aperture == 'Hexagonal':
            kw = {}
            if params.get('hexradius'): kw['circumradius'] = float(params['hexradius'])
            mask, r_norm, theta = m.aperture_hexagonal(xy, **kw)
        elif aperture == 'Cuadrada':
            kw = {}
            if params.get('side'): kw['side'] = float(params['side'])
            mask, r_norm, theta = m.aperture_square(xy, **kw)
        elif aperture == 'Rectangular':
            kw = {}
            if params.get('width'):  kw['width']  = float(params['width'])
            if params.get('height'): kw['height'] = float(params['height'])
            mask, r_norm, theta = m.aperture_rectangular(xy, **kw)

        log(f"  {mask.sum():,} nodos dentro de la apertura.\n")

        # ── 4. Ajuste de Zernike ─────────────────────────────────────────
        nterms   = params['nterms']
        norm     = params['norm']
        un_ap    = un[mask]
        an_ap    = an[mask]
        an_ap    = an_ap / an_ap.sum()
        residual = un_ap.copy()   # si no hay ajuste, residuo = señal

        if nterms > 0:
            log(f"\nAjustando {nterms} polinomios de Zernike (norma '{norm}')…\n")
            term_indices = list(range(nterms))
            coeffs, residual, _ = m.zernike_fit_scatter(
                un_ap, r_norm, theta, terms=term_indices, norm=norm
            )
            rms_res = m.rms_area_weighted(residual, an_ap)
            pv_res  = m.peak_to_valley(residual)
            log(f"  RMS residuo : {rms_res:.6e}\n")
            log(f"  PV  residuo : {pv_res:.6e}\n")

            n_arr, m_arr = m.zernike_iso2nm(nterms)
            log(f"\n{'─'*44}\n")
            log(f"  {'Z':>3}  {'n':>3}  {'m':>4}   Coeficiente\n")
            log(f"{'─'*44}\n")
            for i, c in enumerate(coeffs):
                log(f"  Z{i:<3d}  {n_arr[i]:>3}  {m_arr[i]:>+4}   {c:+.6e}\n")
            log(f"{'─'*44}\n")
        else:
            rms_res = m.rms_area_weighted(residual, an_ap)
            pv_res  = m.peak_to_valley(residual)

        # ── 5. Figura ────────────────────────────────────────────────────
        log("\nGenerando figura…\n")

        def show_fig():
            try:
                x, y = coor[:, 0], coor[:, 1]
                import matplotlib.tri as mtri
                import numpy as np_local

                fig, axes = plt.subplots(1, 3, figsize=(17, 5))
                fig.suptitle('Análisis FEM – Superficie de espejo', fontsize=12)

                # Coordenadas centradas (para contorno de apertura)
                cx, cy       = float(x.mean()), float(y.mean())
                xc_all       = x - cx
                yc_all       = y - cy

                # Panel izquierdo: desplazamiento normal (todos los nodos válidos)
                valid_full = np_local.isfinite(un)
                if valid_full.sum() > 3:
                    tri_full = mtri.Triangulation(x[valid_full], y[valid_full])
                    cf1 = axes[0].tricontourf(tri_full, un[valid_full], levels=64, cmap='gist_rainbow')
                    plt.colorbar(cf1, ax=axes[0], label='Despl. normal')
                else:
                    axes[0].text(0.5, 0.5, 'Sin datos válidos', ha='center', va='center',
                                 transform=axes[0].transAxes)
                axes[0].set_title(
                    f'Desplazamiento normal\n(tras extracción sólido rígido)\n'
                    f'RMS = {rms_total:.3e}   PV = {pv_total:.3e}',
                    fontsize=9)
                axes[0].set_aspect('equal')
                axes[0].set_xlabel('X')
                axes[0].set_ylabel('Y')

                # Interpolador para mostrar valor z al pasar el ratón (panel 0)
                if valid_full.sum() > 3:
                    _interp0 = mtri.LinearTriInterpolator(tri_full, un[valid_full])
                    def _fmt0(xm, ym, _i=_interp0):
                        zv = float(_i(xm, ym))
                        zs = f'{zv:.4e}' if np_local.isfinite(zv) else '—'
                        return f'X={xm:.4f}  Y={ym:.4f}  Despl. normal={zs}'
                    axes[0].format_coord = _fmt0

                # Panel derecho: residuo de Zernike solo en la apertura
                un_res_full = np_local.full(len(coor), np_local.nan)
                un_res_full[mask] = residual
                valid = ~np_local.isnan(un_res_full)
                if valid.sum() > 3:
                    tri_ap = mtri.Triangulation(x[valid], y[valid])
                    cf2 = axes[1].tricontourf(tri_ap, un_res_full[valid], levels=64, cmap='gist_rainbow')
                    plt.colorbar(cf2, ax=axes[1], label='Residuo Zernike')

                    # Interpolador para mostrar valor z al pasar el ratón (panel 1)
                    _label1 = 'Residuo Zernike' if nterms > 0 else 'Despl. normal (apertura)'
                    _interp1 = mtri.LinearTriInterpolator(tri_ap, un_res_full[valid])
                    def _fmt1(xm, ym, _i=_interp1, _l=_label1):
                        zv = float(_i(xm, ym))
                        zs = f'{zv:.4e}' if np_local.isfinite(zv) else '—'
                        return f'X={xm:.4f}  Y={ym:.4f}  {_l}={zs}'
                    axes[1].format_coord = _fmt1

                title2 = (f'Residuo Zernike ({nterms} términos)\napertura {aperture}'
                          if nterms > 0 else f'Apertura {aperture}')
                axes[1].set_title(
                    f'{title2}\nRMS = {rms_res:.3e}   PV = {pv_res:.3e}',
                    fontsize=9)
                axes[1].set_aspect('equal')
                axes[1].set_xlabel('X')
                axes[1].set_ylabel('Y')

                # ── Panel derecho: PSF ───────────────────────────────────────
                # Interpolamos el residuo (o la señal si no hay ajuste Zernike)
                # a una malla cuadrada regular y calculamos la PSF via FFT2.
                N_psf = 256
                from scipy.interpolate import griddata as _griddata
                # Rango de la apertura centrada
                xc_ap = x[valid] - cx
                yc_ap = y[valid] - cy
                ap_range = max(np_local.abs(xc_ap).max(), np_local.abs(yc_ap).max()) * 1.05
                xi = np_local.linspace(-ap_range, ap_range, N_psf)
                yi = np_local.linspace(-ap_range, ap_range, N_psf)
                XI, YI = np_local.meshgrid(xi, yi)
                # Interpolar residuo en la malla
                W_grid = _griddata(
                    np_local.column_stack([xc_ap, yc_ap]),
                    un_res_full[valid],
                    (XI, YI), method='linear'
                )
                # Máscara de apertura en la malla (NaN fuera)
                A_grid = np_local.where(np_local.isfinite(W_grid), 1.0, 0.0)
                W_grid = np_local.nan_to_num(W_grid, nan=0.0)
                # Fase en radianes: W en unidades de longitud → normalizar a fracción de λ
                # Como no tenemos λ, mostramos la PSF en unidades arbitrarias
                # (la forma espacial es lo que importa, no la escala absoluta)
                pupil = A_grid * np_local.exp(1j * 2 * np_local.pi * W_grid
                                              / (W_grid[A_grid > 0].max() - W_grid[A_grid > 0].min() + 1e-30))
                psf_raw = np_local.abs(np_local.fft.fftshift(
                                       np_local.fft.fft2(pupil))) ** 2
                # Recortar al 20% central para ver el pico de difracción
                c = N_psf // 2
                crop = max(N_psf // 10, 8)
                psf_crop = psf_raw[c - crop:c + crop, c - crop:c + crop]
                # Escala log para ver lóbulos secundarios
                psf_log = np_local.log10(psf_crop / psf_crop.max() + 1e-6)
                im_psf = axes[2].imshow(psf_log, origin='lower', cmap='inferno',
                                        extent=[-crop, crop, -crop, crop])
                plt.colorbar(im_psf, ax=axes[2], label='log₁₀(PSF norm.)')
                axes[2].set_title('PSF simulada\n(residuo Zernike → difracción)')
                axes[2].set_xlabel('píxeles FFT')
                axes[2].set_ylabel('píxeles FFT')

                # Valor PSF al pasar el ratón (panel 2)
                _psf_arr  = psf_log
                _psf_rows, _psf_cols = _psf_arr.shape
                _psf_ext  = [-crop, crop, -crop, crop]   # xmin, xmax, ymin, ymax
                def _fmt2(xm, ym,
                          _arr=_psf_arr, _r=_psf_rows, _c=_psf_cols,
                          _e=_psf_ext):
                    col = int((_c - 1) * (xm - _e[0]) / (_e[1] - _e[0]) + 0.5)
                    row = int((_r - 1) * (ym - _e[2]) / (_e[3] - _e[2]) + 0.5)
                    if 0 <= row < _r and 0 <= col < _c:
                        zs = f'{_arr[row, col]:.4f}'
                    else:
                        zs = '—'
                    return f'X={xm:.2f}  Y={ym:.2f}  log₁₀(PSF norm.)={zs}'
                axes[2].format_coord = _fmt2

                # ── Casco convexo de los datos FEM reales (línea blanca) ──────
                from scipy.spatial import ConvexHull
                import math as _math
                valid_pts = np_local.column_stack([x[valid_full], y[valid_full]])
                try:
                    hull = ConvexHull(valid_pts)
                    hv   = hull.vertices
                    hv   = np_local.append(hv, hv[0])          # cerrar el polígono
                    for ax in axes[:2]:
                        ax.plot(valid_pts[hv, 0], valid_pts[hv, 1],
                                'w-', lw=1.4, alpha=0.85, zorder=4,
                                label='Límite datos FEM')
                    # Fracción de la apertura teórica cubierta por los datos
                    area_data = hull.volume   # en 2D, .volume == área
                    if aperture == 'Circular':
                        R_ap = float(params['radius']) if params.get('radius') \
                               else np_local.hypot(xc_all, yc_all).max()
                        area_ap = _math.pi * R_ap ** 2
                    elif aperture == 'Hexagonal':
                        R_ap = float(params['hexradius']) if params.get('hexradius') \
                               else np_local.hypot(xc_all, yc_all).max()
                        area_ap = (3 * _math.sqrt(3) / 2) * R_ap ** 2
                    elif aperture == 'Cuadrada':
                        side = float(params['side']) if params.get('side') \
                               else 2.0 * max(float(np_local.abs(xc_all).max()),
                                              float(np_local.abs(yc_all).max()))
                        area_ap = side ** 2
                    elif aperture == 'Rectangular':
                        w = float(params['width'])  if params.get('width')  \
                            else 2.0 * float(np_local.abs(xc_all).max())
                        h = float(params['height']) if params.get('height') \
                            else 2.0 * float(np_local.abs(yc_all).max())
                        area_ap = w * h
                    else:
                        area_ap = None
                    if area_ap:
                        pct = 100.0 * area_data / area_ap
                        schedule(0, lambda p=pct: log(
                            f"\n  ℹ Los datos FEM cubren ~{p:.0f}% del área de la apertura.\n"
                            + ("    El modelo FEM parece ser un modelo parcial (simetría reducida).\n"
                               if p < 82 else "")))
                except Exception:
                    pass   # si hay < 3 puntos válidos, ConvexHull falla — ignorar

                # ── Contorno de apertura teórica (línea amarilla discontinua) ──
                _draw_aperture_boundary(axes[0], aperture, cx, cy, xc_all, yc_all, params)
                _draw_aperture_boundary(axes[1], aperture, cx, cy, xc_all, yc_all, params)

                # ── Leyenda (solo paneles de superficie) ─────────────────────
                import matplotlib.lines as mlines
                leg_data = mlines.Line2D([], [], color='white', lw=1.4, label='Límite datos FEM')
                leg_ap   = mlines.Line2D([], [], color='gold', lw=1.5, ls='--',
                                          label=f'Apertura {aperture}')
                for ax in axes[:2]:
                    ax.legend(handles=[leg_data, leg_ap], loc='lower right',
                              fontsize=7, framealpha=0.6)

                plt.tight_layout()

                # Guardar datos para la vista 3D posterior
                if result_store is not None:
                    result_store[0] = {
                        'x':        x,
                        'y':        y,
                        'z_res':    un_res_full,
                        'valid':    valid,
                        'rms_res':  rms_res,
                        'pv_res':   pv_res,
                        'nterms':   nterms,
                        'aperture': aperture,
                    }

                # Mostrar en la GUI (embebida) o en ventana externa
                # Para guardar la imagen usa el botón 💾 de la barra de navegación inferior.
                if embed_fig is not None:
                    embed_fig(fig)
                else:
                    plt.show()

            except Exception:
                log(f"\n✗ Error al generar figura:\n{traceback.format_exc()}\n")

        # Mostrar la figura en el hilo principal de Tk
        schedule(0, show_fig)
        log("\n✓ Análisis completado.\n")

    except FileNotFoundError as e:
        log(f"\n✗ Archivo no encontrado: {e}\n")
    except Exception:
        log(f"\n✗ Error durante el análisis:\n{traceback.format_exc()}\n")


# ═══════════════════════════════════════════════════════════════════
#  INTERFAZ GRÁFICA
# ═══════════════════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Análisis FEM – Superficie de espejo")
        self.resizable(True, True)
        self.minsize(700, 700)

        style = ttk.Style(self)
        style.theme_use('clam')

        self._result_store = [None]   # datos del último análisis para vista 3D

        self._build_ui()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)   # log se expande
        self.rowconfigure(6, weight=3)   # figura ocupa más espacio

    # ── Construcción de widgets ─────────────────────────────────────

    def _build_ui(self):
        pad = dict(padx=10, pady=5)

        # ── Archivo de datos ─────────────────────────────────────────
        frm_file = ttk.LabelFrame(self, text="Archivo de datos FEM")
        frm_file.grid(row=0, column=0, sticky='ew', **pad)
        frm_file.columnconfigure(0, weight=1)

        self.fname_var = tk.StringVar()
        ttk.Entry(frm_file, textvariable=self.fname_var, width=60).grid(
            row=0, column=0, padx=(6, 4), pady=6, sticky='ew')
        ttk.Button(frm_file, text="Examinar…", command=self._browse).grid(
            row=0, column=1, padx=(0, 6), pady=6)

        # Logo del departamento (columna 2, rowspan=2)
        try:
            _logo_img = tk.PhotoImage(data=_LOGO_B64)
            _logo_lbl = ttk.Label(frm_file, image=_logo_img)
            _logo_lbl.image = _logo_img        # evitar que el GC destruya la imagen
            _logo_lbl.grid(row=0, column=2, rowspan=2, padx=(6, 10), pady=4, sticky='e')
        except Exception:
            pass   # si el entorno no soporta PhotoImage con data=, continúa sin logo

        # Nota de formato del fichero TXT
        _fmt_text = (
            "Formato TXT: una línea por nodo  →  node_id   X   Y   Z   dX   dY   dZ\n"
            "Las columnas deben estar separadas por espacios o tabuladores. "
            "Se ignoran las líneas que empiecen por '#'.\n"
            "El eje Z debe ser el eje óptico (normal al espejo). "
            "El origen de coordenadas puede estar en cualquier punto; "
            "el programa centra automáticamente la apertura en el centroide de los nodos."
        )
        ttk.Label(frm_file, text=_fmt_text, foreground='#555555',
                  wraplength=680, justify='left').grid(
            row=1, column=0, columnspan=2, padx=6, pady=(0, 6), sticky='w')

        # ── Sólido rígido ─────────────────────────────────────────────
        frm_rigid = ttk.LabelFrame(self, text="Modos de sólido rígido a eliminar")
        frm_rigid.grid(row=1, column=0, sticky='ew', **pad)

        self.rigid_vars = []
        defaults = [True, True, True, True, True, True]
        for i, lbl in enumerate(['Tx', 'Ty', 'Tz', 'Rx', 'Ry', 'Rz']):
            v = tk.BooleanVar(value=defaults[i])
            self.rigid_vars.append(v)
            ttk.Checkbutton(frm_rigid, text=lbl, variable=v).grid(
                row=0, column=i, padx=8, pady=6)

        # ── Apertura ─────────────────────────────────────────────────
        frm_ap = ttk.LabelFrame(self, text="Apertura del espejo")
        frm_ap.grid(row=2, column=0, sticky='ew', **pad)
        frm_ap.columnconfigure(4, weight=1)

        self.ap_var = tk.StringVar(value='Circular')
        apertures = ['Circular', 'Hexagonal', 'Cuadrada', 'Rectangular']
        for i, name in enumerate(apertures):
            ttk.Radiobutton(frm_ap, text=name, variable=self.ap_var,
                            value=name, command=self._update_ap_fields).grid(
                row=0, column=i, padx=10, pady=6)

        # Sub-frame para parámetros opcionales de apertura
        self.frm_ap_extra = ttk.Frame(frm_ap)
        self.frm_ap_extra.grid(row=1, column=0, columnspan=5, sticky='ew', padx=6, pady=(0, 6))
        self._ap_extra_widgets = {}
        self._build_ap_extras()
        self._update_ap_fields()

        # ── Zernike ───────────────────────────────────────────────────
        frm_zern = ttk.LabelFrame(self, text="Polinomios de Zernike")
        frm_zern.grid(row=3, column=0, sticky='ew', **pad)

        ttk.Label(frm_zern, text="Número de términos:").grid(row=0, column=0, padx=8, pady=6)
        self.nterms_var = tk.IntVar(value=3)
        sp = ttk.Spinbox(frm_zern, from_=0, to=200, textvariable=self.nterms_var, width=6)
        sp.grid(row=0, column=1, padx=4, pady=6)
        ttk.Label(frm_zern, text="  (0 = solo RMS, sin ajuste Zernike)").grid(
            row=0, column=2, padx=0, pady=6, sticky='w')

        ttk.Label(frm_zern, text="Normalización:").grid(row=0, column=3, padx=(20, 4), pady=6)
        self.norm_var = tk.StringVar(value='pico')
        ttk.Radiobutton(frm_zern, text='Pico', variable=self.norm_var, value='pico').grid(
            row=0, column=4, pady=6)
        ttk.Radiobutton(frm_zern, text='RMS', variable=self.norm_var, value='rms').grid(
            row=0, column=5, padx=4, pady=6)

        # ── Botón ejecutar ─────────────────────────────────────────────
        frm_btns = ttk.Frame(self)
        frm_btns.grid(row=4, column=0, pady=10)

        self.btn_run = ttk.Button(frm_btns, text="▶  Ejecutar análisis",
                                  command=self._run, style='Accent.TButton')
        self.btn_run.grid(row=0, column=0)

        # ── Log de resultados ─────────────────────────────────────────
        frm_log = ttk.LabelFrame(self, text="Resultados")
        frm_log.grid(row=5, column=0, sticky='nsew', **pad)
        frm_log.columnconfigure(0, weight=1)
        frm_log.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            frm_log, wrap=tk.WORD, font=('Consolas', 9),
            state='disabled', height=12, background='#1e1e1e', foreground='#d4d4d4')
        self.log_text.grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        btn_clear = ttk.Button(frm_log, text="Limpiar", command=self._clear_log, width=8)
        btn_clear.grid(row=1, column=0, sticky='e', padx=4, pady=(0, 4))

        # ── Panel de figura embebida ──────────────────────────────────
        self.frm_fig = ttk.LabelFrame(self, text="Figura")
        self.frm_fig.grid(row=6, column=0, sticky='nsew', **pad)

        # ── Controles Vista 3D (debajo de la figura) ───────────────────
        frm_3d = ttk.Frame(self)
        frm_3d.grid(row=7, column=0, pady=(4, 6))

        ttk.Label(frm_3d, text="Escala Z:").grid(row=0, column=0, padx=(0, 4))
        self.scale3d_var = tk.StringVar(value='10E6')
        ttk.Entry(frm_3d, textvariable=self.scale3d_var, width=8).grid(
            row=0, column=1, padx=(0, 8))

        self.btn_3d = ttk.Button(frm_3d, text="🎨  Vista 3D",
                                 command=self._show_3d, state='disabled')
        self.btn_3d.grid(row=0, column=2)
        self.frm_fig.columnconfigure(0, weight=1)
        self.frm_fig.rowconfigure(0, weight=1)

        # Placeholder mientras no hay figura
        self._fig_placeholder = ttk.Label(
            self.frm_fig,
            text="La figura aparecerá aquí al completar el análisis.",
            foreground='gray')
        self._fig_placeholder.grid(row=0, column=0, padx=10, pady=40)

        self._canvas = None   # FigureCanvasTkAgg actual

    def _build_ap_extras(self):
        """Crea todos los sub-widgets de parámetros de apertura (ocultos por defecto)."""
        f = self.frm_ap_extra
        widgets = {}

        def row(key, label, default=''):
            lbl = ttk.Label(f, text=label)
            var = tk.StringVar(value=default)
            ent = ttk.Entry(f, textvariable=var, width=10)
            widgets[key] = (lbl, ent, var)

        row('radius',    'Radio circunscrito (vacío = auto):')
        row('hexradius', 'Radio circunscrito (vacío = auto):')
        row('side',      'Lado del cuadrado  (vacío = auto):')
        row('width',     'Ancho (X) (vacío = auto):')
        row('height',    'Alto  (Y) (vacío = auto):')

        self._ap_extra_widgets = widgets

    def _update_ap_fields(self):
        """Muestra sólo los campos relevantes para la apertura seleccionada."""
        ap = self.ap_var.get()
        visible = {
            'Circular':    ['radius'],
            'Hexagonal':   ['hexradius'],
            'Cuadrada':    ['side'],
            'Rectangular': ['width', 'height'],
        }.get(ap, [])

        # Ocultar todos
        for lbl, ent, _ in self._ap_extra_widgets.values():
            lbl.grid_forget(); ent.grid_forget()

        # Mostrar los relevantes
        for col, key in enumerate(visible):
            lbl, ent, _ = self._ap_extra_widgets[key]
            lbl.grid(row=0, column=col * 2,     padx=(0, 2))
            ent.grid(row=0, column=col * 2 + 1, padx=(0, 12))

    # ── Acciones ────────────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de datos FEM",
            filetypes=[("Archivos de texto", "*.txt *.dat *.csv"), ("Todos", "*.*")])
        if path:
            self.fname_var.set(path)

    def _log(self, text):
        """Escribe en el widget de log (seguro desde cualquier hilo)."""
        def _write():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        self.after(0, _write)

    def _clear_log(self):
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state='disabled')

    def _embed_figure(self, fig):
        """Embebe una figura matplotlib en el panel inferior del GUI."""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

        # Eliminar figura anterior si existe
        if self._canvas is not None:
            try:
                self._canvas.get_tk_widget().destroy()
            except Exception:
                pass
            self._canvas = None

        # Eliminar todos los widgets del frame (incluyendo toolbar anterior)
        for widget in self.frm_fig.winfo_children():
            widget.destroy()

        # Crear canvas embebido
        canvas = FigureCanvasTkAgg(fig, master=self.frm_fig)
        canvas.draw()

        # Barra de navegación (zoom, pan, guardar…)
        # pack_toolbar=False requiere matplotlib >= 3.3; fallback para versiones antiguas
        try:
            toolbar = NavigationToolbar2Tk(canvas, self.frm_fig, pack_toolbar=False)
            toolbar.update()
            toolbar.grid(row=1, column=0, sticky='ew', padx=4, pady=(0, 2))
        except TypeError:
            # matplotlib antiguo: la toolbar usa pack internamente, la metemos en un frame
            frm_tb = tk.Frame(self.frm_fig)
            frm_tb.grid(row=1, column=0, sticky='ew')
            toolbar = NavigationToolbar2Tk(canvas, frm_tb)
            toolbar.update()

        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        self._canvas = canvas

    def _run(self):
        fname = self.fname_var.get().strip()
        if not fname:
            messagebox.showwarning("Sin archivo", "Selecciona primero un archivo de datos.")
            return
        if not os.path.isfile(fname):
            messagebox.showerror("Archivo no encontrado", f"No existe el archivo:\n{fname}")
            return

        nterms = self.nterms_var.get()
        if nterms < 0:
            messagebox.showwarning("Parámetro inválido", "El número de términos no puede ser negativo.")
            return

        # Recoger parámetros de apertura opcionales
        def _val(key):
            _, _, var = self._ap_extra_widgets[key]
            s = var.get().strip()
            return s if s else None

        params = {
            'fname':    fname,
            'rigid':    tuple(int(v.get()) for v in self.rigid_vars),
            'aperture': self.ap_var.get(),
            'nterms':   nterms,
            'norm':     self.norm_var.get(),
            'radius':   _val('radius'),
            'hexradius':_val('hexradius'),
            'side':     _val('side'),
            'width':    _val('width'),
            'height':   _val('height'),
        }

        self.btn_run.configure(state='disabled', text="Ejecutando…")
        self.btn_3d.configure(state='disabled')
        self._clear_log()
        self._result_store[0] = None   # borrar resultado anterior

        def _done():
            self.btn_run.configure(state='normal', text="▶  Ejecutar análisis")
            if self._result_store[0] is not None:
                self.btn_3d.configure(state='normal')

        def _thread():
            run_analysis(params, self._log, self.after,
                         embed_fig=self._embed_figure,
                         result_store=self._result_store)
            self.after(0, _done)

        threading.Thread(target=_thread, daemon=True).start()


    def _show_3d(self):
        """Abre una ventana Toplevel con la superficie deformada en 3D."""
        data = self._result_store[0]
        if data is None:
            messagebox.showinfo("Sin datos", "Ejecuta primero el análisis.")
            return

        scale_str = self.scale3d_var.get().strip().replace(',', '.')
        try:
            scale = float(scale_str)
            if scale == 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Escala inválida",
                                   "Introduce un número distinto de cero (p.ej. 10E6).")
            return

        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
        import matplotlib.tri as mtri
        import numpy as _np
        from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,
                                                        NavigationToolbar2Tk)

        x       = data['x']
        y       = data['y']
        z_res   = data['z_res']
        valid   = data['valid']
        rms_res = data['rms_res']
        pv_res  = data['pv_res']
        nterms  = data['nterms']
        aperture= data['aperture']

        xv = x[valid]
        yv = y[valid]
        zv = z_res[valid] * scale   # amplificado para que sea visible

        # ── Figura 3D ─────────────────────────────────────────────────
        fig = plt.figure(figsize=(9, 7))
        ax  = fig.add_subplot(111, projection='3d')

        tri  = mtri.Triangulation(xv, yv)
        surf = ax.plot_trisurf(tri, zv, cmap='gist_rainbow',
                               linewidth=0, antialiased=True, alpha=0.92)

        cb = fig.colorbar(surf, ax=ax, shrink=0.55, pad=0.1)
        cb.set_label(f'Despl. normal × {scale:g}', fontsize=8)
        # Reescalar etiquetas del colorbar a valores reales
        import matplotlib.ticker as mticker
        cb.formatter = mticker.FuncFormatter(lambda v, _: f'{v/scale:.2e}')
        cb.update_ticks()

        title2 = (f'Residuo Zernike ({nterms} términos) — apertura {aperture}'
                  if nterms > 0 else f'Apertura {aperture}')
        ax.set_title(
            f'Vista 3D — {title2}\n'
            f'RMS = {rms_res:.3e}   PV = {pv_res:.3e}   (escala Z × {scale:g})',
            fontsize=9)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel(f'Despl. × {scale:g}')

        # Relación de aspecto: X e Y a escala real; Z amplificado
        x_range = xv.max() - xv.min()
        y_range = yv.max() - yv.min()
        z_range = zv.max() - zv.min() if (zv.max() - zv.min()) > 0 else 1.0
        ax.set_box_aspect([x_range, y_range, z_range * 0.3])  # Z más comprimido visualmente

        plt.tight_layout()

        # ── Embeber en un Toplevel Tk para no bloquear la GUI ─────────
        top = tk.Toplevel(self)
        top.title(f"Vista 3D — escala Z × {scale:g}")
        top.geometry("920x720")
        top.columnconfigure(0, weight=1)
        top.rowconfigure(0, weight=1)

        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()

        try:
            toolbar = NavigationToolbar2Tk(canvas, top, pack_toolbar=False)
            toolbar.update()
            toolbar.grid(row=1, column=0, sticky='ew', padx=4, pady=(0, 2))
        except TypeError:
            frm_tb = tk.Frame(top)
            frm_tb.grid(row=1, column=0, sticky='ew')
            toolbar = NavigationToolbar2Tk(canvas, frm_tb)
            toolbar.update()

        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew', padx=4, pady=4)

        # Nota: rotar arrastrando con el botón izquierdo del ratón
        ttk.Label(top, text="Arrastra para rotar · Rueda para zoom · Botón derecho para desplazar",
                  foreground='gray').grid(row=2, column=0, pady=(0, 4))


# ═══════════════════════════════════════════════════════════════════
#  PUNTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app = App()
    app.mainloop()
