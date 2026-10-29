"""Verificación por sustitución en la ED original (regla 2).

Primero simbólica; si no simplifica a 0, numérica en 5 puntos aleatorios.
"""
from __future__ import annotations

import random

import sympy as sp

from .lector import ED, x, y, ys
from .paso import Verificacion

N_PUNTOS = 5
TOL = 1e-7


def _numerico(expr: sp.Expr, simbolos: list[sp.Symbol], rng: random.Random,
              dominio=(0.3, 2.5), puntos: int = N_PUNTOS) -> tuple[bool, str]:
    """Evalúa expr en ``puntos`` puntos aleatorios. Falla si algún valor no es ~0."""
    f = sp.lambdify(simbolos, expr, modules=["mpmath"])
    validos = intentos = 0
    peor = 0.0
    while validos < puntos and intentos < 60:
        intentos += 1
        pt = [rng.uniform(*dominio) for _ in simbolos]
        try:
            v = complex(f(*pt))
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            continue
        if v != v or abs(v) == float("inf"):
            continue
        escala = max(1.0, max(abs(p) for p in pt))
        peor = max(peor, abs(v) / escala)
        validos += 1
    if validos < puntos:
        return False, "no se pudieron evaluar 5 puntos"
    return peor < TOL, f"error máximo {peor:.2e}"


def es_cero(expr: sp.Expr, simbolos: list[sp.Symbol] | None = None, *, semilla: int = 12345) -> Verificacion:
    """¿expr ≡ 0? Simbólico y, si no simplifica, numérico."""
    expr = sp.sympify(expr)
    if expr == 0:
        return Verificacion(True, "simbólica")
    try:
        s = sp.simplify(expr)
    except Exception:
        s = expr
    if s == 0:
        return Verificacion(True, "simbólica")
    simbolos = simbolos or sorted(expr.free_symbols, key=lambda v: v.name)
    if not simbolos:
        ok, det = _numerico(expr, [], random.Random(semilla), puntos=1)
        return Verificacion(ok, "numérica", det)
    ok, det = _numerico(expr, simbolos, random.Random(semilla))
    return Verificacion(ok, "numérica (5 puntos)", det)


def _derivadas_explicitas(ed: ED, f: sp.Expr) -> sp.Expr:
    """F(x, f, f', ...) para y = f(x)."""
    e = ed.expr
    for d in sorted(e.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        e = e.subs(d, sp.diff(f, x, d.derivative_count))
    return e.subs(y(x), f)


def verificar_explicita(ed: ED, f: sp.Expr) -> Verificacion:
    """Verifica y = f(x) (f puede llevar constantes C1, C2, ...)."""
    residuo = _derivadas_explicitas(ed, f)
    return es_cero(residuo)


def derivadas_implicitas(G: sp.Expr, n: int) -> list[sp.Expr]:
    """[y', y'', ...] como funciones de (x, y) para la curva G(x, y) = 0."""
    Gy = sp.diff(G, ys)
    if Gy == 0:
        raise ValueError("la relación no depende de y")
    p = -sp.diff(G, x) / Gy
    out = [p]
    for _ in range(1, n):
        p = sp.diff(p, x) + sp.diff(p, ys) * out[0]
        out.append(p)
    return out


def verificar_implicita(ed: ED, izq: sp.Expr, der: sp.Expr) -> Verificacion:
    """Verifica la solución implícita izq(x,y) = der (der puede llevar constantes).

    Se deriva implícitamente, se sustituyen y', y'' en la ED y se comprueba que el
    residuo se anule sobre la curva (no idénticamente).
    """
    G = izq - der
    try:
        ders = derivadas_implicitas(G, max(ed.orden, 1))
    except ValueError as exc:
        return Verificacion(False, "no verificada", str(exc))
    e = ed.expr
    for d in sorted(e.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        e = e.subs(d, ders[d.derivative_count - 1])
    e = e.subs(y(x), ys)
    residuo = sp.simplify(e)
    if residuo == 0:
        return Verificacion(True, "simbólica")
    # sobre la curva: despejar y si se puede
    try:
        ramas = sp.solve(G, ys)
    except Exception:
        ramas = []
    if ramas:
        res = [es_cero(sp.simplify(residuo.subs(ys, r))) for r in ramas]
        if all(r.ok for r in res):
            return Verificacion(True, res[0].como, "sustituyendo cada rama de y despejada")
    # numérico sobre la curva: se fija x, se resuelve y con nsolve
    rng = random.Random(2024)
    consts = sorted((G.free_symbols - {x, ys}), key=lambda s: s.name)
    ok_n = 0
    peor = 0.0
    for _ in range(40):
        if ok_n >= N_PUNTOS:
            break
        sub = {c: rng.uniform(0.5, 2.0) for c in consts}
        x0, y0 = rng.uniform(0.5, 2.0), rng.uniform(0.5, 2.0)
        try:
            Gn = G.subs(sub)
            yv = sp.nsolve(Gn.subs(x, x0), ys, y0)
            v = complex(residuo.subs(sub).subs({x: x0, ys: yv}).evalf())
        except Exception:
            continue
        peor = max(peor, abs(v))
        ok_n += 1
    if ok_n < N_PUNTOS:
        return Verificacion(False, "no verificada", "no se pudo evaluar la curva en 5 puntos")
    return Verificacion(peor < 1e-6, "numérica (5 puntos)", f"error máximo {peor:.2e}")
