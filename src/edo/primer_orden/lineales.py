"""Lineal (en y o en x), Bernoulli (en y o en x) y homogénea (y = t x, x = t y)."""
from __future__ import annotations

import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x, ys
from ..core.paso import Paso, Resultado
from .base import C, NOTA_ABS, NoAplica, Solucion, combinar, despejar_y, finalizar, forma, integ, paso_integral

t = sp.Symbol("t")


# ------------------------------------------------------------------ detección
def _lineal_en(f: sp.Expr, dep: sp.Symbol):
    """f = -P·dep + Q con P, Q sin dep  ->  (P, Q), o None."""
    if f is None:
        return None
    A = sp.diff(f, dep)
    if A.has(dep):
        return None
    B = sp.simplify(f - A * dep)
    if B.has(dep):
        return None
    return sp.simplify(-A), B


def _lado(ed: ED, en_x: bool):
    """(f, indep, dep): dy/dx = f(x,y) o dx/dy = h(x,y)."""
    fm = forma(ed)
    if fm.M is None or fm.N is None:
        return None
    if en_x:
        if fm.M == 0:
            return None
        return sp.together(-fm.N / fm.M), ys, x
    if fm.N == 0:
        return None
    return fm.f, x, ys


def aplica_lineal(ed: ED, en_x: bool = False) -> str | None:
    try:
        r = _lado(ed, en_x)
    except NoAplica:
        return None
    if r is None:
        return None
    f, ind, dep = r
    pq = _lineal_en(f, dep)
    if pq is None:
        return None
    return (f"dx/dy + P(y)x = Q(y) con P = {latex(pq[0])}, Q = {latex(pq[1])}" if en_x
            else f"dy/dx + P(x)y = Q(x) con P = {latex(pq[0])}, Q = {latex(pq[1])}")


def _nombre(ind, dep):
    return str(dep), str(ind)


def _resolver_lineal_core(res: Resultado, P: sp.Expr, Q: sp.Expr, ind: sp.Symbol, dep: sp.Symbol):
    """Pasos del factor integrante. Devuelve (G, mu) con G = dep·mu − ∫mu·Q = C."""
    d, i = _nombre(ind, dep)
    IP, adv, rg = integ(P, ind)
    res.advertencias += adv
    res.pasos.append(paso_integral("Resolver las integrales", rf"\int P\,d{i} = \int {latex(P)}\,d{i}", latex(IP), rg))
    if IP.has(sp.log):
        res.advertencias.append(NOTA_ABS)
    mu = simplificar(sp.exp(IP))
    res.pasos.append(Paso("Factor integrante", rf"\mu = e^{{\int P\,d{i}}}", "", rf"\mu = e^{{{latex(IP)}}} = {latex(mu)}"))
    integrando = simplificar(mu * Q)
    IQ, adv2, rg2 = integ(integrando, ind)
    res.advertencias += adv2
    res.pasos.append(Paso("Reemplazar en la solución", rf"{d}\,e^{{\int P d{i}}} = \int e^{{\int P d{i}}}\,Q\,d{i} + C", "",
                          rf"{d}\,{latex(mu)} = \int {latex(integrando)}\,d{i} + C"))
    res.pasos.append(paso_integral("Simplificar y resolver la integral", rf"\int {latex(integrando)}\,d{i}", latex(IQ), rg2))
    G = simplificar(dep * mu) - IQ
    return G, mu


def resolver_lineal(ed: ED, condiciones=None, en_x: bool = False) -> Resultado:
    r = _lado(ed, en_x)
    pq = _lineal_en(r[0], r[2]) if r else None
    if pq is None:
        raise NoAplica("La ecuación no es lineal en " + ("x" if en_x else "y") + ".")
    f, ind, dep = r
    P, Q = pq
    d, i = _nombre(ind, dep)
    res = Resultado("lineal en " + ("x" if en_x else "y"))
    forma_txt = rf"\frac{{d{d}}}{{d{i}}} + P({i})\,{d} = Q({i})"
    res.pasos.append(Paso("Reescribir la ecuación diferencial y comparar con la forma lineal", forma_txt,
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          rf"\frac{{d{d}}}{{d{i}}} + \left({latex(P)}\right){d} = {latex(Q)}", f"$P={latex(P)}$, $Q={latex(Q)}$."))
    G, mu = _resolver_lineal_core(res, P, Q, ind, dep)
    res.pasos.append(Paso("Escribir la solución", "solución general", "", latex(G) + " = C"))
    sol = Solucion(G, C)
    if not en_x:
        e = despejar_y(G, C)
        if e is not None:
            res.pasos.append(Paso("Despejar y (solución explícita)", "", latex(G) + " = C", "y = " + latex(e)))
            sol = Solucion(ys, e)
    return finalizar(res, ed, sol, condiciones)


# ------------------------------------------------------------------- Bernoulli
def _bernoulli_en(f: sp.Expr, dep: sp.Symbol):
    """f = -P·dep + Q·dep^n  ->  (P, Q, n) con n ∉ {0,1}."""
    if f is None:
        return None
    f = sp.expand(f)
    por_exp: dict[sp.Expr, sp.Expr] = {}
    for term in sp.Add.make_args(f):
        coef, resto = term.as_independent(dep, as_Add=False)
        if resto == 1:
            e = sp.Integer(0)
        else:
            b, e = resto.as_base_exp()
            if b != dep or e.has(dep) or e.free_symbols:
                return None
        por_exp[e] = por_exp.get(e, 0) + coef
    otros = [e for e in por_exp if e not in (0, 1)]
    if len(otros) != 1 or (0 in por_exp and False):
        return None
    n = otros[0]
    if 0 in por_exp and por_exp[0] != 0:
        return None
    P = -por_exp.get(sp.Integer(1), sp.Integer(0))
    Q = por_exp[n]
    return sp.simplify(P), sp.simplify(Q), n


def aplica_bernoulli(ed: ED, en_x: bool = False) -> str | None:
    try:
        r = _lado(ed, en_x)
    except NoAplica:
        return None
    if r is None:
        return None
    b = _bernoulli_en(r[0], r[2])
    if b is None:
        return None
    return f"Bernoulli con n = {latex(b[2])}"


def resolver_bernoulli(ed: ED, condiciones=None, en_x: bool = False) -> Resultado:
    r = _lado(ed, en_x)
    b = _bernoulli_en(r[0], r[2]) if r else None
    if b is None:
        raise NoAplica("La ecuación no es de Bernoulli en " + ("x" if en_x else "y") + ".")
    f, ind, dep = r
    P, Q, n = b
    d, i = _nombre(ind, dep)
    res = Resultado("Bernoulli en " + ("x" if en_x else "y"))
    res.pasos.append(Paso("Reescribir y comparar con la forma de Bernoulli", rf"\frac{{d{d}}}{{d{i}}} + P({i}){d} = Q({i}){d}^n",
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          rf"\frac{{d{d}}}{{d{i}}} + \left({latex(P)}\right){d} = \left({latex(Q)}\right){d}^{{{latex(n)}}}",
                          f"$n={latex(n)}$, $P={latex(P)}$, $Q={latex(Q)}$."))
    res.pasos.append(Paso(f"Dividir entre ${d}^{{{latex(n)}}}$", "", "",
                          rf"{d}^{{{latex(-n)}}}\frac{{d{d}}}{{d{i}}} + \left({latex(P)}\right){d}^{{{latex(1 - n)}}} = {latex(Q)}"))
    k = 1 - n
    res.pasos.append(Paso("Cambio de variable", rf"v = {d}^{{1-n}}", "",
                          rf"v = {d}^{{{latex(k)}}},\quad \frac{{dv}}{{d{i}}} = {latex(k)}\,{d}^{{{latex(-n)}}}\frac{{d{d}}}{{d{i}}}"))
    res.pasos.append(Paso("Ecuación lineal en v", "v' + (1−n)P v = (1−n)Q", "",
                          rf"\frac{{dv}}{{d{i}}} + \left({latex(sp.simplify(k * P))}\right)v = {latex(sp.simplify(k * Q))}"))
    v = sp.Symbol("v")
    Gv, mu = _resolver_lineal_core(res, sp.simplify(k * P), sp.simplify(k * Q), ind, v)
    G = Gv.subs(v, dep ** k)
    res.pasos.append(Paso("Volver a la variable original", rf"v = {d}^{{{latex(k)}}}", "", latex(G) + " = C"))
    sol = Solucion(G, C)
    if not en_x:
        e = despejar_y(G, C)
        if e is not None:
            res.pasos.append(Paso("Despejar y (solución explícita)", "", latex(G) + " = C", "y = " + latex(e)))
            sol = Solucion(ys, e)
    if n.is_positive:
        res.advertencias.append(f"Al dividir entre ${d}^{{{latex(n)}}}$ se pierde la solución ${d}=0$ (compruébala en la ecuación).")
    return finalizar(res, ed, sol, condiciones)


# ------------------------------------------------------------------ homogénea
_l = sp.Symbol("lam", positive=True)


def _es_homogenea(f: sp.Expr) -> bool:
    if f is None or not (f.has(x) and f.has(ys)):
        return False
    try:
        return sp.simplify(f.subs({x: _l * x, ys: _l * ys}, simultaneous=True) - f) == 0
    except Exception:
        return False


def aplica_homogenea(ed: ED) -> str | None:
    try:
        fm = forma(ed)
    except NoAplica:
        return None
    return "M y N son homogéneas del mismo grado: f(λx, λy) = f(x, y)" if _es_homogenea(fm.f) else None


def _homogenea_candidato(fm, variante: str):
    """Devuelve (g(t), integrando, descripción) para y = t x ('yx') o x = t y ('xy')."""
    if variante == "yx":
        g = sp.simplify(fm.f.subs({ys: t * x}).subs(x, 1))          # f(1, t)
        den = sp.simplify(g - t)
        return g, (sp.simplify(1 / den) if den != 0 else None), den
    if fm.M == 0:
        raise NoAplica("Con x = t y hace falta M ≠ 0.")
    h = sp.simplify((-fm.N / fm.M).subs({x: t * ys}).subs(ys, 1))     # dx/dy con y = 1
    den = sp.simplify(h - t)
    return h, (sp.simplify(1 / den) if den != 0 else None), den


def resolver_homogenea(ed: ED, condiciones=None, variante: str | None = None) -> Resultado:
    fm = forma(ed)
    if not _es_homogenea(fm.f):
        raise NoAplica("La ecuación no es homogénea (f(λx, λy) ≠ f(x, y)).")
    if variante is None:
        mejor = None
        for v in ("yx", "xy"):
            try:
                g, q, den = _homogenea_candidato(fm, v)
            except NoAplica:
                continue
            if q is None:
                continue
            ind = t
            val, adv, _ = integ(q, t)
            costo = sp.count_ops(val) + (1000 if adv else 0)
            if mejor is None or costo < mejor[0]:
                mejor = (costo, v)
        variante = mejor[1] if mejor else "yx"
    g, q, den = _homogenea_candidato(fm, variante)
    res = Resultado("homogénea (" + ("y = t x" if variante == "yx" else "x = t y") + ")")
    res.pasos.append(Paso("Verificar que la ecuación es homogénea", "f(λx, λy) = f(x, y)",
                          latex(ed.lhs) + " = " + latex(ed.rhs), rf"f(\lambda x,\lambda y) = f(x,y)",
                          "Todos los términos de $M$ y de $N$ tienen el mismo grado."))
    if variante == "yx":
        res.pasos.append(Paso("Cambio de variable y = t x", "dy = t dx + x dt", "",
                              r"y = t\,x,\quad dy = t\,dx + x\,dt", "Después $t = y/x$."))
        res.pasos.append(Paso("Reemplazar en la ecuación y simplificar", "x dt/dx = f(1,t) − t", rf"t + x\frac{{dt}}{{dx}} = {latex(g)}",
                              rf"x\,\frac{{dt}}{{dx}} = {latex(den)}", "Se simplifica la potencia de $x$ común."))
        sep_txt = rf"\int {latex(q)}\,dt = \int \frac{{dx}}{{x}}"
        izq_t, adv, rg = integ(q, t)
        res.advertencias += adv
        res.pasos.append(paso_integral("Separar variables e integrar", sep_txt, latex(izq_t) + r" = \ln x + C", rg))
        G = (izq_t - sp.log(x)).subs(t, ys / x)
        perdidas = []
        for t0 in sp.solve(den, t):
            if not t0.free_symbols and t0.is_real is not False:
                perdidas.append(f"y={latex(sp.simplify(t0))}x")
    else:
        res.pasos.append(Paso("Cambio de variable x = t y", "dx = t dy + y dt", "",
                              r"x = t\,y,\quad dx = t\,dy + y\,dt", "Después $t = x/y$."))
        res.pasos.append(Paso("Reemplazar en la ecuación y simplificar", "y dt/dy = dx/dy(1,t) − t", rf"t + y\frac{{dt}}{{dy}} = {latex(g)}",
                              rf"y\,\frac{{dt}}{{dy}} = {latex(den)}"))
        sep_txt = rf"\int {latex(q)}\,dt = \int \frac{{dy}}{{y}}"
        izq_t, adv, rg = integ(q, t)
        res.advertencias += adv
        res.pasos.append(paso_integral("Separar variables e integrar", sep_txt, latex(izq_t) + r" = \ln y + C", rg))
        G = (izq_t - sp.log(ys)).subs(t, x / ys)
        perdidas = []
        for t0 in sp.solve(den, t):
            if not t0.free_symbols and t0.is_real is not False:
                perdidas.append(f"x={latex(sp.simplify(t0))}y")
    res.advertencias.append(NOTA_ABS)
    if perdidas:
        res.advertencias.append("Al dividir entre el denominador se pierden las soluciones " + ", ".join(f"${p}$" for p in perdidas) + " (compruébalas).")
    G = combinar(G)
    res.pasos.append(Paso("Volver a la variable inicial y escribir la solución", "solución general", "", latex(G) + " = C"))
    sol = Solucion(G, C)
    e = despejar_y(G, C)
    if e is not None:
        sol = Solucion(ys, e)
    return finalizar(res, ed, sol, condiciones)
