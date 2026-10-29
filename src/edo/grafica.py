"""Muestreo de soluciones para graficar en el navegador (sin librerías de gráficas).

* explícitas y = f(x): puntos con cortes donde la función no existe o explota,
* implícitas G(x, y) = c: curvas de nivel por cuadrículas (marching squares),
* paramétricas (x(p), y(p)).
Las familias con constantes se dibujan para varios valores de la constante, como en el texto.
"""
from __future__ import annotations

import math

import sympy as sp

from .core.lector import x, ys
from .core.paso import Resultado
from .primer_orden.base import Solucion
from .core.geogebra import _CTE


def _constantes(*exprs) -> list[sp.Symbol]:
    cs = set()
    for e in exprs:
        cs |= {s for s in sp.sympify(e).free_symbols if _CTE.match(s.name)}
    return sorted(cs, key=lambda s: s.name)


def _evaluador(expr, variables):
    f = sp.lambdify(variables, expr, modules=["math"])

    def g(*args):
        try:
            v = f(*args)
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            return None
        if isinstance(v, complex):
            return v.real if abs(v.imag) < 1e-12 else None
        return v if isinstance(v, (int, float)) and math.isfinite(v) else None
    return g


def _linea(g, xmin, xmax, n=600, ycorte=1e3):
    segmentos, actual = [], []
    prev = None
    for i in range(n + 1):
        xv = xmin + (xmax - xmin) * i / n
        v = g(xv)
        if v is None or abs(v) > ycorte or (prev is not None and abs(v - prev) > ycorte / 4):
            if len(actual) > 1:
                segmentos.append(actual)
            actual = []
            prev = None if v is None or abs(v) > ycorte else v
            if prev is not None:
                actual.append([xv, v])
            continue
        actual.append([xv, v])
        prev = v
    if len(actual) > 1:
        segmentos.append(actual)
    return segmentos


def _nivel(g, nivel, xmin, xmax, ymin, ymax, n=140):
    """Curva de nivel g(x, y) = nivel como segmentos sueltos (marching squares)."""
    xs = [xmin + (xmax - xmin) * i / n for i in range(n + 1)]
    yv = [ymin + (ymax - ymin) * j / n for j in range(n + 1)]
    z = [[g(a, b) for b in yv] for a in xs]
    segs = []

    def interp(p0, p1, z0, z1):
        t = (nivel - z0) / (z1 - z0) if z1 != z0 else 0.5
        return [p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])]
    for i in range(n):
        for j in range(n):
            esq = [(xs[i], yv[j], z[i][j]), (xs[i + 1], yv[j], z[i + 1][j]),
                   (xs[i + 1], yv[j + 1], z[i + 1][j + 1]), (xs[i], yv[j + 1], z[i][j + 1])]
            if any(c[2] is None for c in esq):
                continue
            pts = []
            for a in range(4):
                p, q = esq[a], esq[(a + 1) % 4]
                if (p[2] - nivel) * (q[2] - nivel) < 0:
                    pts.append(interp(p[:2], q[:2], p[2], q[2]))
            if len(pts) == 2:
                segs.append(pts)
            elif len(pts) == 4:
                segs += [[pts[0], pts[1]], [pts[2], pts[3]]]
    return segs


def _valores_familia(familia: list[float] | None, cs: list[sp.Symbol]):
    if not cs:
        return [{}]
    vals = familia or [-2, -1, 0, 1, 2]
    return [{cs[0]: v, **{c: 1 for c in cs[1:]}} for v in vals]


def series(res: Resultado, xmin=-5.0, xmax=5.0, ymin=-5.0, ymax=5.0, familia: list[float] | None = None) -> list[dict]:
    """Lista de series {nombre, color, segmentos}. Cada segmento es una lista de [x, y]."""
    objetos = []
    v = res.valor
    if isinstance(v, (list, tuple)):
        objetos += [(o, "solución") for o in v]
    elif v is not None:
        objetos.append((v, "solución"))
    objetos += [(o, "singular/perdida") for o in res.extra]
    out = []
    for obj, rol in objetos:
        if isinstance(obj, Solucion):
            izq, der, param = obj.izq, obj.der, obj.param
        elif isinstance(obj, sp.Basic):
            izq, der, param = ys, obj, None
        else:
            continue
        if param is not None:
            xp, yp = param
            cs = _constantes(xp, yp)
            for k, sub in enumerate(_valores_familia(familia, cs)):
                fx = _evaluador(xp.subs(sub), [sp.Symbol("p")])
                fy = _evaluador(yp.subs(sub), [sp.Symbol("p")])
                pts, segs = [], []
                for i in range(-400, 401):
                    p = i / 80.0 + 1e-3
                    a, b = fx(p), fy(p)
                    if a is None or b is None or abs(a) > 1e3 or abs(b) > 1e3:
                        if len(pts) > 1:
                            segs.append(pts)
                        pts = []
                        continue
                    pts.append([a, b])
                if len(pts) > 1:
                    segs.append(pts)
                out.append({"nombre": _nombre(rol, sub), "segmentos": segs, "singular": rol != "solución"})
        elif izq == ys and ys not in der.free_symbols:
            cs = _constantes(der)
            for sub in _valores_familia(familia, cs):
                g = _evaluador(der.subs(sub), [x])
                out.append({"nombre": _nombre(rol, sub), "segmentos": _linea(g, xmin, xmax), "singular": rol != "solución"})
        else:
            G = izq - der
            cs = _constantes(G)
            # G = C con C constante: se dibujan varios niveles de C; si no, el nivel 0
            if cs and der in cs:
                g = _evaluador(izq, [x, ys])
                for lv in (familia or [-2, -1, 0, 1, 2]):
                    out.append({"nombre": f"C = {lv:g}", "segmentos": _nivel(g, lv, xmin, xmax, ymin, ymax),
                                "singular": rol != "solución"})
            else:
                sub = {c: (familia or [1])[0] for c in cs}
                g = _evaluador(G.subs(sub), [x, ys])
                out.append({"nombre": _nombre(rol, sub), "segmentos": _nivel(g, 0, xmin, xmax, ymin, ymax), "singular": rol != "solución"})
    return out


def _nombre(rol: str, sub: dict) -> str:
    if not sub:
        return rol
    return ", ".join(f"{k} = {float(v):g}" for k, v in sub.items())
