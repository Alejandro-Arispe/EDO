"""Variables separables y ecuaciones reducibles a separables: y'=f(ax+by+c) y y'=(y/x)h(xy)."""
from __future__ import annotations

import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x, ys
from ..core.paso import Paso, Resultado
from ..core.verificador import es_cero
from .base import C, NOTA_ABS, NoAplica, Solucion, despejar_y, finalizar, forma, integ, paso_integral

u = sp.Symbol("u")


def _separar(f: sp.Expr):
    """f(x,y) = k·f1(x)·f2(y) -> (f1, f2) con la constante k dentro de f1, o None."""
    if f is None or f.has(sp.Derivative):
        return None
    try:
        d = sp.separatevars(f, dict=True, symbols=[x, ys])
    except Exception:
        return None
    if not d:
        return None
    f1 = d.get("coeff", 1) * d.get(x, 1)
    f2 = d.get(ys, 1)
    if f1.has(ys) or f2.has(x):
        return None
    return f1, f2


def aplica_separable(ed: ED) -> str | None:
    try:
        fm = forma(ed)
    except NoAplica:
        return None
    if _separar(fm.f) is None:
        return None
    return "y' = f(x,y) se puede escribir como f₁(x)·f₂(y)"


def _perdidas(f2: sp.Expr, ed: ED, G: sp.Expr, exp_y=None) -> list[str]:
    out = []
    try:
        raices = sp.solve(f2, ys)
    except Exception:
        raices = []
    for r in raices:
        if r.has(x) or r.free_symbols - {x} or r.is_real is False:
            continue
        # ¿y = r pertenece a la familia G(x,y)=C? (G(x,r) constante en x)
        if exp_y is not None:
            try:
                dentro = any(not s.has(x) and sp.simplify(exp_y.subs(C, s) - r) == 0 for s in sp.solve(sp.simplify(exp_y - r), C))
            except Exception:
                dentro = False
        else:
            dentro = sp.simplify(sp.diff(G.subs(ys, r), x)) == 0
        out.append(f"Al dividir entre ${latex(f2)}$ se pierde la solución constante $y={latex(r)}$"
                   + (" (ya está contenida en la familia para algún valor de la constante)." if dentro else
                      " (NO está contenida en la familia: es una solución perdida)."))
    return out


def resolver_separable(ed: ED, condiciones=None) -> Resultado:
    fm = forma(ed)
    sep = _separar(fm.f)
    if sep is None:
        raise NoAplica("No se puede separar f(x,y) en un producto f₁(x)·f₂(y).")
    f1, f2 = sep
    res = Resultado("variables separables")
    res.pasos.append(Paso("Escribir la ecuación en la forma y' = f₁(x)·f₂(y)", "y' = f₁(x) f₂(y)",
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          rf"\frac{{dy}}{{dx}} = \left({latex(f1)}\right)\left({latex(f2)}\right)"))
    izq_int = 1 / f2
    res.pasos.append(Paso("Agrupar las variables con su diferencial", "dy / f₂(y) = f₁(x) dx", "",
                          rf"\frac{{dy}}{{{latex(f2)}}} = {latex(f1)}\,dx" if f2 != 1 else rf"dy = {latex(f1)}\,dx"))
    Fy, adv1, r1 = integ(izq_int, ys)
    Fx, adv2, r2 = integ(f1, x)
    res.advertencias += adv1 + adv2
    res.pasos.append(paso_integral("Integrar ambos lados", rf"\int {latex(izq_int)}\,dy = \int {latex(f1)}\,dx",
                                   latex(Fy) + " = " + latex(Fx) + " + C", "; ".join(t for t in (r1, r2) if t)))
    if Fy.has(sp.log) or Fx.has(sp.log):
        res.advertencias.append(NOTA_ABS)
    G = Fy - Fx
    exp_y = despejar_y(G, C)
    res.pasos.append(Paso("Escribir la solución", "solución general", "", latex(G) + " = C"))
    sol = Solucion(G, C)
    if exp_y is not None:
        res.pasos.append(Paso("Despejar y (solución explícita)", "", latex(G) + " = C", "y = " + latex(exp_y)))
        sol = Solucion(ys, exp_y)
    for t in _perdidas(f2, ed, G, exp_y):
        res.advertencias.append(t)
    return finalizar(res, ed, sol, condiciones)


# ---------------------------------------------------------------- y' = f(ax+by+c)
def _buscar_lineal(f: sp.Expr):
    """(a, b, c, g(u)) con f = g(a x + b y + c), o None."""
    cands = []
    for s in sp.preorder_traversal(f):
        if s.has(x) and s.has(ys) and s not in cands and not isinstance(s, (sp.Symbol,)):
            cands.append(s)
    for s in cands:
        try:
            P = sp.Poly(s, x, ys)
        except sp.PolynomialError:
            continue
        if P.total_degree() != 1:
            continue
        a, b, c = P.coeff_monomial(x), P.coeff_monomial(ys), P.coeff_monomial(1)
        if a == 0 or b == 0:
            continue
        g = sp.simplify(f.subs(ys, (u - a * x - c) / b))
        if not g.has(x):
            return a, b, c, g
    return None


def aplica_reducible_lineal(ed: ED) -> str | None:
    try:
        fm = forma(ed)
    except NoAplica:
        return None
    if fm.f is None or _separar(fm.f) is not None:
        return None
    r = _buscar_lineal(fm.f)
    if r is None:
        return None
    a, b, c, _ = r
    return f"y' = f(ax+by+c) con ax+by+c = {latex(a * x + b * ys + c)}"


def resolver_reducible_lineal(ed: ED, condiciones=None) -> Resultado:
    fm = forma(ed)
    r = _buscar_lineal(fm.f) if fm.f is not None else None
    if r is None:
        raise NoAplica("y' no es una función de a x + b y + c.")
    a, b, c, g = r
    L = a * x + b * ys + c
    res = Resultado("reducible a separable: y' = f(ax+by+c)")
    res.pasos.append(Paso("Reescribir la ecuación diferencial", "", latex(ed.lhs) + " = " + latex(ed.rhs),
                          "y' = " + latex(fm.f)))
    res.pasos.append(Paso("Realizar un cambio de variable", f"u = ax + by + c, du = a dx + b dy", "",
                          rf"u = {latex(L)}, \quad du = {latex(a)}\,dx + {latex(b)}\,dy" if b != 1 or a != 1 else rf"u = {latex(L)}, \quad du = dx + dy",
                          "Se deriva respecto de $x$: $u' = a + b\\,y'$."))
    rhs = sp.simplify(a + b * g)
    res.pasos.append(Paso("Reemplazar la nueva variable en la ecuación", "u' = a + b f(u)",
                          "u' = " + latex(a) + " + " + latex(b) + r"\,y'", rf"\frac{{du}}{{dx}} = {latex(rhs)}"))
    if rhs == 0:
        raise NoAplica("u' = 0: la ecuación se reduce a u = constante.")
    sep = _separar(rhs.subs(u, ys))  # u ocupa el lugar de y para separar
    Fu, adv, rg = integ(sp.simplify(1 / rhs), u)
    res.advertencias += adv
    res.pasos.append(paso_integral("Separar variables, integrar y volver a la variable inicial",
                                   rf"\int \frac{{du}}{{{latex(rhs)}}} = \int dx", latex(Fu) + " = x + C", rg))
    G = (Fu - x).subs(u, L)
    res.pasos.append(Paso("Escribir la solución", "solución general", "", latex(G) + " = C"))
    sol = Solucion(G, C)
    exp_y = despejar_y(G, C)
    if exp_y is not None:
        res.pasos.append(Paso("Despejar y (solución explícita)", "", latex(G) + " = C", "y = " + latex(exp_y)))
        sol = Solucion(ys, exp_y)
    try:
        for u0 in sp.solve(rhs, u):
            if u0.free_symbols or u0.is_real is False:
                continue
            res.advertencias.append(f"Al dividir entre ${latex(rhs)}$ se pierde la solución $u={latex(u0)}$, "
                                    f"es decir $y={latex(sp.simplify((u0 - a * x - c) / b))}$.")
    except Exception:
        pass
    return finalizar(res, ed, sol, condiciones)


# -------------------------------------------------------------- y' = (y/x)·h(xy)
def _buscar_xy(f: sp.Expr):
    if f is None:
        return None
    h = sp.simplify((f * x / ys).subs(ys, u / x))
    if h.has(x) or not f.has(x) or not f.has(ys):
        return None
    return h


def aplica_reducible_xy(ed: ED) -> str | None:
    try:
        fm = forma(ed)
    except NoAplica:
        return None
    if fm.f is None or _separar(fm.f) is not None or _buscar_xy(fm.f) is None:
        return None
    return "y' = (y/x)·h(xy): se reduce con u = xy"


def resolver_reducible_xy(ed: ED, condiciones=None) -> Resultado:
    fm = forma(ed)
    h = _buscar_xy(fm.f)
    if h is None:
        raise NoAplica("La ecuación no tiene la forma y f(xy) dx + x g(xy) dy = 0.")
    res = Resultado("reducible a separable: función de xy")
    res.pasos.append(Paso("Reescribir la ecuación diferencial", "y' = (y/x)·h(xy)",
                          latex(ed.lhs) + " = " + latex(ed.rhs), rf"y' = \frac{{y}}{{x}}\left({latex(h)}\right)\quad\text{{con }}u = xy"))
    res.pasos.append(Paso("Realizar un cambio de variable", "u = x y,  u' = y + x y'", "",
                          r"u = xy,\quad \frac{du}{dx} = y + x\,y'",
                          "Se deriva $u=xy$ respecto de $x$."))
    rhs = sp.simplify(u * (1 + h) / x)
    res.pasos.append(Paso("Reemplazar en la ecuación", "u' = y + y h(u) = (u/x)(1 + h(u))", "",
                          rf"\frac{{du}}{{dx}} = \frac{{{latex(sp.simplify(u * (1 + h)))}}}{{x}}"))
    q = sp.simplify(1 / (u * (1 + h)))
    Fu, adv, rg = integ(q, u)
    res.advertencias += adv
    res.pasos.append(paso_integral("Separar variables e integrar", rf"\int {latex(q)}\,du = \int \frac{{dx}}{{x}}",
                                   latex(Fu) + r" = \ln x + C", rg))
    G = (Fu - sp.log(x)).subs(u, x * ys)
    res.pasos.append(Paso("Escribir la solución (volver a la variable inicial)", "solución general", "", latex(G) + " = C"))
    res.advertencias.append(NOTA_ABS)
    sol = Solucion(G, C)
    exp_y = despejar_y(G, C)
    if exp_y is not None:
        sol = Solucion(ys, exp_y)
    res.advertencias.append("Al dividir se pierden y=0 (u=0) y las curvas xy=u₀ con 1+h(u₀)=0, si existen.")
    return finalizar(res, ed, sol, condiciones)
