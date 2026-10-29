"""Coeficiente variable: ecuaciones de Euler y de Cauchy-Legendre.

Euler:           a_k x^k y^(k)            -> x = e^t
Cauchy-Legendre: c_k (ax+b)^k y^(k)       -> ax+b = e^t

Con D = d/dt:  (ax+b)^k y^(k) = a^k · D(D−1)···(D−k+1) y      (A12: no es a^k D^k)
La ecuación queda de coeficientes constantes en t y se resuelve con los métodos de F4/F5.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import sympy as sp

from ..core import discrepancias  # noqa: F401
from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, D, x, y
from ..core.paso import Paso, Resultado
from ..primer_orden.base import NoAplica
from . import resolutor as _resolutor
from .lineal_cc import L, _finalizar

NOTA_A12 = ("[A12] (ax+b)ⁿ y⁽ⁿ⁾ = aⁿ·D(D−1)···(D−n+1) con ax+b = eᵗ. El texto usó aⁿDⁿ (y por eso dio otras raíces); "
            "la forma correcta lleva los factores (D−1), (D−2), …")


@dataclass
class Euler:
    ed: ED
    n: int
    a: sp.Expr            # u = a x + b
    b: sp.Expr
    c: list               # c_k tal que a_k(x) = c_k u^k
    Q: sp.Expr


def _leer_euler(ed: ED) -> Euler:
    if ed.orden < 2:
        raise NoAplica("Euler y Cauchy-Legendre se usan desde el orden 2.")
    F = ed.expr
    ders = {k: (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for k in range(ed.orden + 1)}
    coefs = [sp.diff(F, d) for d in ders.values()]
    if any(a.has(y) or a.has(sp.Derivative) for a in coefs):
        raise NoAplica("La ecuación no es lineal en y y sus derivadas.")
    resto = F.subs({d: 0 for d in reversed(list(ders.values()))})
    if sp.simplify(F - (sum(a * d for a, d in zip(coefs, ders.values())) + resto)) != 0:
        raise NoAplica("La ecuación no es lineal en y y sus derivadas.")
    top = sp.simplify(coefs[-1])
    if top == 0 or not top.has(x):
        raise NoAplica("El coeficiente de la derivada mayor es constante: no es de Euler (usa los métodos de coeficientes constantes).")
    try:
        _, factores = sp.factor_list(sp.Poly(top, x))
    except Exception:
        raise NoAplica("El coeficiente de la derivada mayor no es de la forma c(ax+b)ⁿ.")
    if len(factores) != 1 or factores[0][0].degree() != 1 or factores[0][1] != ed.orden:
        raise NoAplica("El coeficiente de la derivada mayor no es de la forma c(ax+b)ⁿ, con n el orden de la ecuación.")
    lin = factores[0][0]
    a, b = lin.coeff_monomial(x), lin.coeff_monomial(1)
    u = a * x + b
    c = []
    for k, ak in enumerate(coefs):
        r = sp.simplify(ak / u ** k)
        if r.has(x):
            raise NoAplica(f"El coeficiente de y^({k}) no es c·(ax+b)^{k}: no es una ecuación de Euler / Cauchy-Legendre.")
        c.append(r)
    return Euler(ed, ed.orden, a, b, c, sp.simplify(-resto))


def aplica_euler(ed: ED) -> str | None:
    try:
        e = _leer_euler(ed)
    except NoAplica:
        return None
    u = e.a * x + e.b
    return f"aₖ(x) = cₖ·({latex(u)})ᵏ: se usa {latex(u)} = eᵗ" + (" (Euler)" if e.b == 0 and e.a == 1 else " (Cauchy-Legendre)")


def _prod_descendente(k: int) -> sp.Expr:
    return sp.Mul(*[D - j for j in range(k)]) if k else sp.Integer(1)


def resolver_euler(ed: ED, condiciones=None, metodo_t: str | None = None) -> Resultado:
    E = _leer_euler(ed)
    n, a, b = E.n, E.a, E.b
    u = a * x + b
    tipo = "Euler" if (b == 0 and a == 1) else "Cauchy-Legendre"
    res = Resultado(f"{tipo} ({latex(u)} = e^t)")
    res.pasos.append(Paso(f"Reconocer la ecuación de {tipo}", "aₖ(x) = cₖ (ax+b)ᵏ",
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          r"\ ;\quad ".join(f"a_{{{k}}}(x) = {latex(sp.simplify(ck * u ** k))}" for k, ck in enumerate(E.c) if ck != 0),
                          f"El coeficiente de cada derivada de orden $k$ es una constante por $({latex(u)})^k$."))
    ops = " ;\\quad ".join(
        rf"({latex(u)})^{{{k}}}y^{{({k})}} = {latex(a ** k) + r'\,' if a != 1 else ''}{latex(_prod_descendente(k))}\,y"
        for k in range(1, n + 1))
    res.pasos.append(Paso("Cambio de variable " + latex(u) + " = e^t", "t = ln(ax+b),  D = d/dt", "", ops,
                          "Se toma $D=d/dt$. Con $ax+b=e^t$ resulta $(ax+b)^k y^{(k)} = a^k\\,D(D-1)\\cdots(D-k+1)\\,y$.",
                          discrepancia=NOTA_A12 if a != 1 else None))
    P = sp.expand(sum(c * a ** k * _prod_descendente(k) for k, c in enumerate(E.c)))
    Qt = simplificar(sp.expand(sp.simplify(E.Q.subs(x, (sp.exp(x) - b) / a))))
    lhs_t = sum(co * (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for (k,), co in sp.Poly(P, D).terms())
    ed_t = ED("en t", "operador", lhs_t, Qt, sp.Poly(P, D).degree(), operador=P)
    res.pasos.append(Paso("Reemplazar en la ecuación diferencial", "ecuación de coeficientes constantes en t",
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          rf"\left({latex(P)}\right)y = {latex(Qt)}",
                          "En el término independiente se reemplaza $x=(e^t-b)/a$. Desde aquí la variable independiente es $t$ "
                          "(en los pasos siguientes se escribe $x$ en lugar de $t$)."))
    sub = _resolutor.resolver(ed_t, metodo_t, None)
    if sub.metodo == "ninguno" or sub.valor is None:
        raise NoAplica("La ecuación en t no se resuelve con los métodos de coeficientes constantes del temario.")
    for p in sub.pasos:
        res.pasos.append(Paso("En t: " + p.titulo, p.regla, p.antes_latex, p.despues_latex, p.explicacion, p.discrepancia))
    res.advertencias += sub.advertencias
    t = sp.log(u)
    general = sub.valor.subs(x, t)
    general = sp.simplify(general) if not general.has(sp.Float, sp.Integral) else general
    yp = None if sub.particular is None else sub.particular.subs(x, t)
    res.pasos.append(Paso("Volver a la variable original x", f"t = ln({latex(u)})", "",
                          "y = " + L(general),
                          f"Se reemplaza $t=\\ln({latex(u)})$; $e^{{rt}}=({latex(u)})^r$. Se supone ${latex(u)}>0$ (si es negativo, "
                          "se usa su valor absoluto)."))
    res.advertencias.append(f"Se supone {latex(u)} > 0; con {latex(u)} < 0 se escribe |{latex(u)}| dentro del logaritmo.")
    cs = [sp.Symbol(c) for c in sub.constantes]
    return _finalizar(res, SimpleNamespace(ed=ed), general, cs, condiciones, yp)
