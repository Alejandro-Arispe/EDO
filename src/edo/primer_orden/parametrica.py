"""Verificación de soluciones paramétricas (x(p), y(p)) de F(x, y, y') = 0."""
from __future__ import annotations

import sympy as sp

from ..core.lector import ED, x, ys
from ..core.paso import Verificacion
from ..core.verificador import es_cero
from .base import forma, p


def verificar_parametrica(ed: ED, xp: sp.Expr, yp: sp.Expr) -> Verificacion:
    """Comprueba F(x(p), y(p), p) = 0 y dy/dp = p·dx/dp."""
    F = forma(ed).F
    r1 = es_cero(F.subs({x: xp, ys: yp}, simultaneous=True))
    r2 = es_cero(sp.diff(yp, p) - p * sp.diff(xp, p))
    ok = r1.ok and r2.ok
    como = r1.como if r1.como == r2.como else f"{r1.como} / {r2.como}"
    detalle = "" if ok else ("no cumple F(x(p), y(p), p) = 0" if not r1.ok else "no cumple dy = p dx")
    return Verificacion(ok, como, detalle or "se verificó F(x(p), y(p), p) = 0 y dy/dp = p·dx/dp")
