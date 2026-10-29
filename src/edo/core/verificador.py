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
              dominio=(0.3, 2.5), puntos: int = N_PUNTOS, ramas: bool = False) -> tuple[bool, str]:
    """Evalúa expr en ``puntos`` puntos aleatorios. Falla si algún valor no es ~0.

    Con ``ramas=True`` (ED con raíces o valores absolutos) una solución explícita solo vale en las
    ramas donde la raíz toma el signo correcto: basta que se anule en al menos 5 puntos y en el 20 %
    de los evaluados (una función incorrecta no se anula en un conjunto así).
    """
    try:
        f = sp.lambdify(simbolos, expr, modules=["mpmath"])
    except Exception:
        return False, "no se pudo evaluar numéricamente"
    validos = intentos = buenos = 0
    peor = peor_bueno = 0.0
    limite = 400 if ramas else 60
    while intentos < limite and (validos < puntos or (ramas and buenos < puntos)):
        intentos += 1
        pt = [rng.uniform(*dominio) for _ in simbolos]
        try:
            v = complex(f(*pt))
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            continue
        if v != v or abs(v) == float("inf"):
            continue
        if ramas and abs(v.imag) > 1e-9 * (1 + abs(v)):
            continue   # fuera del dominio real de la solución (p. ej. arcsen x con x > 1)
        escala = max([1.0] + [abs(p) for p in pt])
        err = abs(v) / escala
        validos += 1
        if err < TOL:
            buenos += 1
            peor_bueno = max(peor_bueno, err)
        else:
            peor = max(peor, err)
    if validos < puntos:
        return False, "no se pudieron evaluar 5 puntos"
    if peor < TOL:
        return True, f"error máximo {max(peor, peor_bueno):.2e}"
    if ramas and buenos >= puntos and buenos >= 0.2 * validos:
        return True, (f"se anula en {buenos} de {validos} puntos probados: la solución vale en una rama "
                      "(donde la raíz o el valor absoluto toma el signo correcto)")
    return False, f"error máximo {peor:.2e}"


def es_cero(expr: sp.Expr, simbolos: list[sp.Symbol] | None = None, *, semilla: int = 12345, ramas: bool = False) -> Verificacion:
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
    ok, det = _numerico(expr, simbolos, random.Random(semilla), ramas=ramas)
    return Verificacion(ok, "numérica (5 puntos)", det)


def _derivadas_explicitas(ed: ED, f: sp.Expr) -> sp.Expr:
    """F(x, f, f', ...) para y = f(x)."""
    e = ed.expr
    for d in sorted(e.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        e = e.subs(d, sp.diff(f, x, d.derivative_count))
    return e.xreplace({y(x): f})


def verificar_explicita(ed: ED, f: sp.Expr) -> Verificacion:
    """Verifica y = f(x) (f puede llevar constantes C1, C2, ...)."""
    residuo = _derivadas_explicitas(ed, f)
    radicales = ed.expr.has(sp.Abs) or any(q.exp.is_Rational and not q.exp.is_Integer for q in ed.expr.atoms(sp.Pow))
    return es_cero(residuo, ramas=radicales)


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


def _grado_alto(G: sp.Expr) -> bool:
    """¿G es un polinomio en y de grado mayor que 2?"""
    try:
        return G.is_polynomial(ys) and sp.degree(G, ys) > 2
    except Exception:
        return False


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
    # sobre la curva: despejar y si se puede (no se intenta con polinomios de grado > 2 en y: Cardano es muy pesado)
    try:
        ramas = [] if _grado_alto(G) else sp.solve(G, ys)
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
