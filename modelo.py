"""
modelo.py
Modelo matemático de la concentración de contaminantes C(x, y).

x = intensidad de emisiones, y = velocidad del viento.
Utiliza SymPy para permitir ecuaciones personalizadas y calcular de forma
exacta: derivadas parciales, gradiente, derivada direccional, Hessiana,
puntos críticos y plano tangente.
"""
import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor,
)

# Símbolos globales para SymPy
x_sym, y_sym = sp.symbols("x y", real=True)

# Permite escribir "2x", "3xy", "x^2", "sin x", etc.
_TRANSFORMACIONES = standard_transformations + (
    implicit_multiplication_application, convert_xor,
)
# Solo se permiten estos nombres dentro de la ecuación.
_NOMBRES_PERMITIDOS = {
    "x": x_sym, "y": y_sym,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "exp": sp.exp, "log": sp.log, "ln": sp.log, "sqrt": sp.sqrt,
    "abs": sp.Abs, "pi": sp.pi, "e": sp.E, "E": sp.E,
}


# ----------------------------- PARSEO ------------------------------------

def parsear_ecuacion(ecuacion_str):
    """Convierte un string en una expresión de SymPy en x e y."""
    if not ecuacion_str or not ecuacion_str.strip():
        raise ValueError("La ecuación está vacía.")
    try:
        expr = parse_expr(
            ecuacion_str.strip(), local_dict=_NOMBRES_PERMITIDOS,
            transformations=_TRANSFORMACIONES, evaluate=True,
        )
    except Exception as e:
        raise ValueError(f"No se pudo interpretar la ecuación: {e}")

    if not isinstance(expr, sp.Expr):
        raise ValueError("La entrada no es una expresión matemática válida.")

    extras = expr.free_symbols - {x_sym, y_sym}
    if extras:
        nombres = ", ".join(sorted(str(s) for s in extras))
        raise ValueError(f"Solo se permiten las variables x e y (encontré: {nombres}).")
    return expr


def obtener_funciones(ecuacion_str):
    """Devuelve (f_c, f_gx, f_gy, diff_x, diff_y): funciones numéricas y derivadas simbólicas."""
    expr = parsear_ecuacion(ecuacion_str)
    diff_x = sp.diff(expr, x_sym)
    diff_y = sp.diff(expr, y_sym)
    f_c = _lambdify(expr)
    f_gx = _lambdify(diff_x)
    f_gy = _lambdify(diff_y)
    return f_c, f_gx, f_gy, diff_x, diff_y


def _lambdify(expr):
    """Crea una función numpy que siempre devuelve float/array real (NaN donde no está definida)."""
    base = sp.lambdify((x_sym, y_sym), expr, "numpy")

    def f(x, y):
        # Se evalúa siempre con arrays de NumPy, incluso cuando x e y son escalares:
        # así una división entre cero (o log(0)) da inf/NaN en lugar de lanzar
        # ZeroDivisionError, y la app puede avisar de que C no está definida.
        xa = np.asarray(x, dtype=float)
        ya = np.asarray(y, dtype=float)
        with np.errstate(all="ignore"):
            z = base(xa, ya)
        z = np.asarray(z, dtype=complex)
        # Parte imaginaria distinta de cero -> no está definida en los reales
        z = np.where(np.abs(z.imag) > 1e-12, np.nan, z.real)
        z = np.broadcast_to(z, np.broadcast(xa, ya).shape)
        return z.astype(float) if z.ndim else float(z)

    return f


# ----------------------------- EVALUACIÓN --------------------------------

def concentracion(x, y, f_c):
    """Evalúa la concentración en (x, y)."""
    return float(f_c(x, y))


def gradiente(x, y, f_gx, f_gy):
    """Vector gradiente ∇C = (∂C/∂x, ∂C/∂y) en (x, y)."""
    return float(f_gx(x, y)), float(f_gy(x, y))


def magnitud_gradiente(gx, gy):
    """|∇C| = tasa máxima de cambio."""
    return float(np.hypot(gx, gy))


def angulo_gradiente(gx, gy):
    """Ángulo (grados, 0-360) del gradiente respecto al eje +x."""
    return float(np.degrees(np.arctan2(gy, gx)) % 360)


def unitario(ux, uy):
    """Normaliza un vector (ux, uy) a longitud 1."""
    norma = float(np.hypot(ux, uy))
    if norma == 0:
        raise ValueError("La dirección no puede ser el vector cero.")
    return ux / norma, uy / norma


def derivada_direccional(x, y, ux, uy, f_gx, f_gy):
    """D_u C = ∇C · û."""
    ux, uy = unitario(ux, uy)
    gx, gy = gradiente(x, y, f_gx, f_gy)
    return gx * ux + gy * uy


def angulo_a_vector(grados):
    """Convierte un ángulo (grados) a vector unitario."""
    rad = np.radians(grados)
    return float(np.cos(rad)), float(np.sin(rad))


def direcciones_predefinidas(x, y, f_gx, f_gy):
    """Diccionario nombre -> vector (ux, uy) de direcciones útiles."""
    gx, gy = gradiente(x, y, f_gx, f_gy)
    dirs = {
        "Reducir emisiones (-x)": (-1.0, 0.0),
        "Aumentar emisiones (+x)": (1.0, 0.0),
        "Reducir viento (-y)": (0.0, -1.0),
        "Aumentar viento (+y)": (0.0, 1.0),
    }
    if np.hypot(gx, gy) > 1e-12:
        dirs["Máximo aumento (+∇C)"] = (gx, gy)
        dirs["Descenso más rápido (-∇C)"] = (-gx, -gy)
        # Perpendicular al gradiente: sigue la curva de nivel (D_u C = 0)
        dirs["Sin cambio (curva de nivel)"] = (-gy, gx)
    return dirs


# --------------------------- SEGUNDO ORDEN -------------------------------

def hessiana(ecuacion_str):
    """Matriz Hessiana simbólica [[Cxx, Cxy], [Cxy, Cyy]]."""
    expr = parsear_ecuacion(ecuacion_str)
    return sp.hessian(expr, (x_sym, y_sym))


def hessiana_en(ecuacion_str, x, y):
    """Hessiana evaluada en (x, y): devuelve (Cxx, Cxy, Cyy, determinante)."""
    H = hessiana(ecuacion_str).subs({x_sym: x, y_sym: y})
    cxx, cxy, cyy = float(H[0, 0]), float(H[0, 1]), float(H[1, 1])
    return cxx, cxy, cyy, cxx * cyy - cxy ** 2


def clasificar_punto(cxx, cxy, cyy):
    """Criterio de la segunda derivada (D = Cxx·Cyy − Cxy²)."""
    D = cxx * cyy - cxy ** 2
    if abs(D) < 1e-12:
        return "no concluyente (D = 0)"
    if D < 0:
        return "punto silla"
    return "mínimo local" if cxx > 0 else "máximo local"


def puntos_criticos(ecuacion_str, solo_reales=True):
    """
    Resuelve ∇C = 0. Devuelve lista de dicts con x, y, C y clasificación.
    Si el sistema no tiene solución finita, devuelve lista vacía.
    """
    expr = parsear_ecuacion(ecuacion_str)
    gx, gy = sp.diff(expr, x_sym), sp.diff(expr, y_sym)
    try:
        soluciones = sp.solve([gx, gy], [x_sym, y_sym], dict=True)
    except Exception:
        return []
    H = sp.hessian(expr, (x_sym, y_sym))
    resultado = []
    for sol in soluciones:
        px, py = sol.get(x_sym), sol.get(y_sym)
        if px is None or py is None:          # familia infinita de soluciones
            continue
        if solo_reales and not (px.is_real and py.is_real):
            continue
        Hs = H.subs(sol)
        cxx, cxy, cyy = float(Hs[0, 0]), float(Hs[0, 1]), float(Hs[1, 1])
        resultado.append({
            "x": float(px), "y": float(py),
            "C": float(expr.subs(sol)),
            "tipo": clasificar_punto(cxx, cxy, cyy),
        })
    return resultado


def plano_tangente(ecuacion_str, x0, y0):
    """
    Linealización L(x, y) = C(x0,y0) + Cx·(x−x0) + Cy·(y−y0).
    Devuelve la expresión simbólica simplificada.
    """
    expr = parsear_ecuacion(ecuacion_str)
    c0 = expr.subs({x_sym: x0, y_sym: y0})
    gx = sp.diff(expr, x_sym).subs({x_sym: x0, y_sym: y0})
    gy = sp.diff(expr, y_sym).subs({x_sym: x0, y_sym: y0})
    return sp.expand(c0 + gx * (x_sym - x0) + gy * (y_sym - y0))


def aproximacion_lineal(x0, y0, c0, gx, gy, dx, dy):
    """Estimación ΔC ≈ Cx·Δx + Cy·Δy (diferencial total)."""
    return gx * dx + gy * dy


# ---------------------------- GRÁFICAS -----------------------------------

def malla(xmax, ymax, f_c, n=80, xmin=0.0, ymin=0.0):
    """Cuadrícula (xs, ys, Z) para gráficas. Z tiene NaN donde C no está definida."""
    xs = np.linspace(xmin, xmax, n)
    ys = np.linspace(ymin, ymax, n)
    X, Y = np.meshgrid(xs, ys)
    Z = np.asarray(f_c(X, Y), dtype=float)
    if Z.shape != X.shape:                 # ecuación constante u otra rareza
        Z = np.broadcast_to(Z, X.shape).copy()
    Z = np.where(np.isfinite(Z), Z, np.nan)  # ±inf -> NaN (Plotly los ignora)
    return xs, ys, Z


def flechas_gradiente(xmax, ymax, f_gx, f_gy, paso_x=6, paso_y=6, largo=0.06):
    """
    Genera las líneas (con punta) del campo de gradiente para Plotly.
    Las flechas se dibujan en coordenadas normalizadas para que se vean
    bien aunque los ejes tengan escalas muy distintas.
    """
    fx, fy = [], []
    for px in np.linspace(xmax / (paso_x + 1), xmax * paso_x / (paso_x + 1), paso_x):
        for py in np.linspace(ymax / (paso_y + 1), ymax * paso_y / (paso_y + 1), paso_y):
            gx, gy = gradiente(px, py, f_gx, f_gy)
            if not (np.isfinite(gx) and np.isfinite(gy)):
                continue
            dx = gx / xmax if xmax != 0 else gx
            dy = gy / ymax if ymax != 0 else gy
            n = np.hypot(dx, dy)
            if n == 0:
                continue
            ux, uy = dx / n, dy / n
            x0, y0 = px / xmax, py / ymax
            x1, y1 = x0 + ux * largo, y0 + uy * largo
            cabeza = largo * 0.35
            seg_x, seg_y = [x0, x1], [y0, y1]
            for ang in (np.radians(150), np.radians(-150)):
                hx = x1 + cabeza * (ux * np.cos(ang) - uy * np.sin(ang))
                hy = y1 + cabeza * (ux * np.sin(ang) + uy * np.cos(ang))
                seg_x += [None, x1, hx]
                seg_y += [None, y1, hy]
            fx += [v * xmax if v is not None else None for v in seg_x] + [None]
            fy += [v * ymax if v is not None else None for v in seg_y] + [None]
    return fx, fy
