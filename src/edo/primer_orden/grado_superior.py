"""ED de primer orden y grado superior (Tema 3 del docente): y = f(y'), x = f(y'),
Clairaut y Lagrange, con solución paramétrica y solución singular."""
from __future__ import annotations

import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x, ys
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import es_cero, verificar_explicita
from .base import C, NoAplica, Solucion, forma, integ, p, paso_integral
from .lineales import _resolver_lineal_core
from .parametrica import verificar_parametrica


# ------------------------------------------------------------------ detección
def _resolver_y(F: sp.Expr):
    """y = expr(x, p) si F se puede despejar en y de forma única."""
    if not F.has(ys):
        return None
    try:
        sols = sp.solve(F, ys)
    except Exception:
        return None
    if len(sols) != 1 or sols[0].has(ys):
        return None
    return sols[0]


def _resolver_x(F: sp.Expr):
    if F.has(ys) or not F.has(x):
        return None
    try:
        sols = sp.solve(F, x)
    except Exception:
        return None
    if len(sols) != 1 or sols[0].has(x):
        return None
    return sols[0]


def _clasificar(ed: ED):
    """('y_p', f) | ('x_p', f) | ('lagrange', (φ, ψ)) | ('clairaut', ψ) | None."""
    try:
        fm = forma(ed)
    except NoAplica:
        return None
    F = fm.F
    ye = _resolver_y(F)
    if ye is not None and ye.has(p) and not ye.has(ys):
        if not ye.has(x):
            return "y_p", ye
        phi = sp.diff(ye, x)
        psi = sp.simplify(ye - x * phi)
        if not phi.has(x) and not psi.has(x) and phi.has(p) or (phi != 0 and not phi.has(x) and not psi.has(x)):
            if sp.simplify(phi - p) == 0:
                return "clairaut", psi
            return "lagrange", (phi, psi)
    xe = _resolver_x(F)
    if xe is not None and xe.has(p):
        return "x_p", xe
    return None


def aplica_grado_superior(ed: ED, caso: str) -> str | None:
    c = _clasificar(ed)
    if c is None or c[0] != caso:
        return None
    return {"y_p": "y = f(y')", "x_p": "x = f(y')", "clairaut": "y = x y' + ψ(y') (Clairaut)",
            "lagrange": "y = x φ(y') + ψ(y'), φ(p) ≠ p (Lagrange)"}[caso]


def _parametrica(sol_x, sol_y) -> Solucion:
    return Solucion(param=(sol_x, sol_y))


def _constante_p0(res: Resultado, ed: ED, F: sp.Expr, p0, y_expr_fn):
    """Solución recta/constante que se pierde al dividir (p = p0)."""
    yv = sp.simplify(y_expr_fn(p0))
    if yv.has(p) or not es_cero(F.subs({ys: yv, p: p0}, simultaneous=True)).ok:
        return
    s = Solucion(ys, yv)
    res.adicionales.append({"tipo": "perdida", "latex": s.latex()})
    res.extra.append(s)


# ---------------------------------------------------------------------- y = f(p)
def resolver_y_f_p(ed: ED, condiciones=None) -> Resultado:
    c = _clasificar(ed)
    if not c or c[0] != "y_p":
        raise NoAplica("La ecuación no tiene la forma y = f(y').")
    f = c[1]
    F = forma(ed).F
    res = Resultado("y = f(y')")
    res.pasos.append(Paso("Sustitución y' = p", "y' = p", latex(ed.lhs) + " = " + latex(ed.rhs), "y = " + latex(f) + r"\quad (1)"))
    fp = sp.diff(f, p)
    res.pasos.append(Paso("Derivar respecto de x", "y' = f'(p)·dp/dx", "", rf"p = {latex(fp)}\,\frac{{dp}}{{dx}}"))
    q = sp.simplify(fp / p)
    res.pasos.append(Paso("Separar las variables", "dx = f'(p)/p dp", "", rf"dx = {latex(q)}\,dp"))
    X, adv, rg = integ(q, p)
    res.advertencias += adv
    res.pasos.append(paso_integral("Integrar", rf"x = \int {latex(q)}\,dp", "x = " + latex(X) + r" + C\quad (2)", rg))
    sol = _parametrica(X + C, f)
    res.pasos.append(Paso("Solución paramétrica", "de (1) y (2)", "", sol.latex()))
    _constante_p0(res, ed, F, sp.Integer(0), lambda p0: f.subs(p, p0))
    return _cerrar_param(res, ed, sol, condiciones)


# ---------------------------------------------------------------------- x = f(p)
def resolver_x_f_p(ed: ED, condiciones=None) -> Resultado:
    c = _clasificar(ed)
    if not c or c[0] != "x_p":
        raise NoAplica("La ecuación no tiene la forma x = f(y').")
    f = c[1]
    res = Resultado("x = f(y')")
    res.pasos.append(Paso("Sustitución y' = p", "y' = p", latex(ed.lhs) + " = " + latex(ed.rhs), "x = " + latex(f) + r"\quad (1)"))
    fp = sp.diff(f, p)
    res.pasos.append(Paso("Derivar respecto de p", "dx = f'(p) dp", "", rf"dx = {latex(fp)}\,dp"))
    res.pasos.append(Paso("Usar dy = p dx", "dy = p dx", "", rf"dy = {latex(sp.simplify(p * fp))}\,dp"))
    Y, adv, rg = integ(sp.simplify(p * fp), p)
    res.advertencias += adv
    res.pasos.append(paso_integral("Integrar", rf"y = \int p\,f'(p)\,dp", "y = " + latex(Y) + r" + C\quad (2)", rg))
    sol = _parametrica(f, Y + C)
    res.pasos.append(Paso("Solución paramétrica", "de (1) y (2)", "", sol.latex()))
    return _cerrar_param(res, ed, sol, condiciones)


# --------------------------------------------------------- Lagrange y Clairaut
def resolver_lagrange(ed: ED, condiciones=None) -> Resultado:
    c = _clasificar(ed)
    if not c or c[0] != "lagrange":
        raise NoAplica("La ecuación no tiene la forma de Lagrange y = x φ(y') + ψ(y').")
    phi, psi = c[1]
    F = forma(ed).F
    res = Resultado("Lagrange")
    res.pasos.append(Paso("Sustitución y' = p", "y = x φ(p) + ψ(p)", latex(ed.lhs) + " = " + latex(ed.rhs),
                          "y = " + latex(sp.expand(x * phi + psi)) + r"\quad (1)",
                          f"$\\varphi(p)={latex(phi)}$, $\\psi(p)={latex(psi)}$, con $\\varphi(p)\\neq p$."))
    res.pasos.append(Paso("Derivar respecto de x", "p = φ + (xφ' + ψ')·dp/dx", "",
                          rf"p = {latex(phi)} + \left({latex(sp.simplify(x * sp.diff(phi, p) + sp.diff(psi, p)))}\right)\frac{{dp}}{{dx}}"))
    den = sp.simplify(p - phi)
    P = sp.simplify(-sp.diff(phi, p) / den)
    Q = sp.simplify(sp.diff(psi, p) / den)
    res.pasos.append(Paso("Escribir x como función de p (ecuación lineal en x)", "dx/dp + P(p) x = Q(p)",
                          rf"({latex(den)})\frac{{dx}}{{dp}} = x\,{latex(sp.diff(phi, p))} + {latex(sp.diff(psi, p))}",
                          rf"\frac{{dx}}{{dp}} + \left({latex(P)}\right)x = {latex(Q)}"))
    G, mu = _resolver_lineal_core(res, P, Q, p, x)
    xs = sp.solve(sp.Eq(G, C), x)
    if len(xs) != 1:
        raise NoAplica("No pude despejar x(p) de la ecuación lineal.")
    xp_ = simplificar(xs[0])
    yp_ = simplificar(sp.expand(xp_ * phi + psi))
    res.pasos.append(Paso("Despejar x", "solución (2)", "", "x = " + latex(xp_) + r"\quad (2)"))
    res.pasos.append(Paso("Reemplazar (2) en (1) para hallar y", "", "", "y = " + latex(yp_) + r"\quad (3)"))
    sol = _parametrica(xp_, yp_)
    res.pasos.append(Paso("Solución paramétrica", "de (2) y (3)", "", sol.latex()))
    try:
        for p0 in sp.solve(den, p):
            if not p0.free_symbols and p0.is_real is not False:
                _constante_p0(res, ed, F, p0, lambda q, ph=phi, ps=psi: ph.subs(p, q) * x + ps.subs(p, q))
    except Exception:
        pass
    if res.adicionales:
        res.advertencias.append("Al dividir entre p − φ(p) se pierden soluciones con p constante (recta o constante); aparecen en «soluciones adicionales».")
    return _cerrar_param(res, ed, sol, condiciones)


def resolver_clairaut(ed: ED, condiciones=None) -> Resultado:
    c = _clasificar(ed)
    if not c or c[0] != "clairaut":
        raise NoAplica("La ecuación no tiene la forma de Clairaut y = x y' + ψ(y').")
    psi = c[1]
    res = Resultado("Clairaut")
    res.pasos.append(Paso("Sustitución y' = p", "y = x p + ψ(p)", latex(ed.lhs) + " = " + latex(ed.rhs),
                          "y = x p + " + latex(psi) + r"\quad (1)", f"$\\psi(p)={latex(psi)}$."))
    res.pasos.append(Paso("Derivar respecto de x y simplificar", "p = p + (x + ψ'(p))·p'", "",
                          rf"x\,p' + {latex(sp.diff(psi, p))}\,p' = 0"))
    res.pasos.append(Paso("Factorizar e igualar a cero cada factor", "(x + ψ'(p))·dp/dx = 0", "",
                          rf"\left(x + {latex(sp.diff(psi, p))}\right)\frac{{dp}}{{dx}} = 0",
                          "Es una ecuación de Clairaut: de $dp/dx=0$ sale la solución general y de $x+\\psi'(p)=0$ la singular."))
    res.pasos.append(Paso("Factor dp/dx = 0: solución general", "p = C", "", r"\frac{dp}{dx} = 0 \Rightarrow p = C",
                          "Se reemplaza $p=C$ en (1)."))
    general = Solucion(ys, C * x + psi.subs(p, C))
    res.pasos.append(Paso("Solución general", "y = Cx + ψ(C)  (A13)", "", general.latex(),
                          discrepancia="[A13] La solución general de y = x y' + f(y') es y = Cx + f(C); el texto escribió y = C + f(C). "
                                       "La singular sale de x + f'(p) = 0."))
    xs_ = sp.simplify(-sp.diff(psi, p))
    ys_ = simplificar(sp.expand(xs_ * p + psi))
    res.pasos.append(Paso("Factor x + ψ'(p) = 0: solución singular", "x = −ψ'(p), y = xp + ψ(p)", rf"x + {latex(sp.diff(psi, p))} = 0",
                          rf"x = {latex(xs_)}\ ;\quad y = {latex(ys_)}"))
    sing = _parametrica(xs_, ys_)
    adic = {"tipo": "singular", "latex": sing.latex()}
    extra = sing
    try:
        ps = [r for r in sp.solve(sp.Eq(x, xs_), p) if not r.has(sp.I, sp.LambertW)]
        if len(ps) == 1:
            ye = simplificar(sp.expand(x * ps[0] + psi.subs(p, ps[0])))
            if not ye.has(p) and verificar_explicita(ed, ye).ok:
                extra = Solucion(ys, ye)
                adic = {"tipo": "singular", "latex": extra.latex() + r"\ \ \left(\text{o en forma paramétrica: }" + sing.latex() + r"\right)"}
                res.pasos.append(Paso("Eliminar p en la solución singular", "", "", extra.latex()))
        elif len(ps) > 1:
            ramas = []
            for r in ps:
                ye = simplificar(sp.expand(x * r + psi.subs(p, r)))
                if not ye.has(p) and verificar_explicita(ed, ye).ok:
                    ramas.append(ye)
            if ramas:
                extra = Solucion(ys, ramas[0])
                adic = {"tipo": "singular", "latex": " ;\\ ".join("y = " + latex(r) for r in ramas)}
                res.pasos.append(Paso("Eliminar p en la solución singular", "", "", adic["latex"]))
                res.extra += [Solucion(ys, r) for r in ramas[1:]]
    except Exception:
        pass
    res.adicionales.append(adic)
    res.extra.insert(0, extra)
    from .base import finalizar
    return finalizar(res, ed, general, condiciones)


# ---------------------------------------------------------------------- común
def _cerrar_param(res: Resultado, ed: ED, sol: Solucion, condiciones) -> Resultado:
    res.valor = sol
    res.solucion = sol.latex()
    v = verificar_parametrica(ed, sol.param[0], sol.param[1])
    res.verificacion = v
    res.constantes = ["C"]
    if condiciones:
        res.advertencias.append("Las condiciones iniciales no se aplican a la solución paramétrica de este método; "
                                "se hallaría el valor de C y de p que pasan por el punto dado.")
    if not v.ok:
        res.advertencias.append("La verificación por sustitución no confirmó la solución: no la tomes como correcta.")
    return res
