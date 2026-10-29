"""Variación de parámetros para F(D)y = Q(x) de coeficientes constantes, orden n ≥ 2.

y_p = L₁y₁ + … + Lₙyₙ con el sistema  Σ Lᵢ' yᵢ⁽ᵏ⁾ = 0 (k = 0..n−2),  Σ Lᵢ' yᵢ⁽ⁿ⁻¹⁾ = Q/aₙ,
resuelto por Cramer: Lᵢ' = Δᵢ/Δ con Δ = Wronskiano. Si el coeficiente principal aₙ ≠ 1 se divide Q entre aₙ.
Las integrales no elementales se dejan indicadas (integral definida desde un límite fijo, que solo
cambia las constantes).
"""
from __future__ import annotations

import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x
from ..core.paso import Paso, Resultado
from ..primer_orden.base import NoAplica, integ
from .lineal_cc import L, EDLineal, _finalizar, leer_lineal, solucion_homogenea

_t = sp.Dummy("t")


def aplica_variacion(ed: ED) -> str | None:
    if ed.orden < 2:
        return None
    try:
        L_ = leer_lineal(ed)
    except NoAplica:
        return None
    if L_.homogenea:
        return None
    return "coeficientes constantes con cualquier Q(x) continua (sistema de Lᵢ', Cramer y Wronskiano)"


def _vmatrix(M: sp.Matrix) -> str:
    filas = r" \\ ".join(" & ".join(L(e) for e in M.row(i)) for i in range(M.rows))
    return rf"\begin{{vmatrix}} {filas} \end{{vmatrix}}"


def _limite_inferior(f: sp.Expr) -> sp.Expr:
    for a in (1, 2, 3, sp.Rational(1, 2)):
        v = f.subs(x, a)
        try:
            ok = v.is_finite is not False and not v.has(sp.zoo, sp.nan, sp.oo, -sp.oo) and abs(complex(sp.N(v))) < 1e12
        except Exception:
            ok = False
        if ok:
            return sp.Integer(a) if isinstance(a, int) else a
    return sp.Integer(1)


def resolver_variacion(ed: ED, condiciones=None) -> Resultado:
    L_: EDLineal = leer_lineal(ed)
    if L_.homogenea:
        raise NoAplica("La ecuación es homogénea: no hay solución particular que buscar.")
    n = L_.n
    res = Resultado("variación de parámetros")
    yh, cs, raices = solucion_homogenea(L_, res)
    base = [simplificar(sp.expand(sp.diff(yh, c))) for c in cs]
    an = sp.Poly(L_.P, sp.Symbol("D")).LC()
    g = sp.simplify(L_.Q / an)
    if an != 1:
        res.pasos.append(Paso("Dejar el coeficiente principal en 1", "dividir la ecuación entre aₙ",
                              rf"{latex(an)}\,y^{{({n})}} + \cdots = {L(L_.Q)}", rf"y^{{({n})}} + \cdots = {L(g)}",
                              f"El coeficiente de la derivada mayor es ${latex(an)}\\neq 1$: se divide toda la ecuación entre él; "
                              "el término independiente del sistema pasa a ser $g(x)=Q(x)/a_n$."))
    res.pasos.append(Paso("Segundo paso. Escribir la solución propuesta y_p", "y_p = L₁y₁ + … + Lₙyₙ", "",
                          "y_p = " + " + ".join(f"L_{{{i}}}\\,y_{{{i}}}" for i in range(1, n + 1)) +
                          r"\ ;\quad " + r",\ ".join(f"y_{{{i}}} = {L(b)}" for i, b in enumerate(base, 1)),
                          "$L_i$ son funciones de $x$ (incógnitas); $y_i$ son las soluciones de $y_h$."))
    # Wronskiano y sistema
    W = sp.Matrix([[sp.diff(b, x, k) for b in base] for k in range(n)])
    filas = []
    for k in range(n):
        izq = " + ".join(f"L_{{{i}}}'\\,\\left({L(W[k, i - 1])}\\right)" for i in range(1, n + 1))
        filas.append(izq + " = " + (L(g) if k == n - 1 else "0"))
    res.pasos.append(Paso("Tercer paso. Formar el sistema de ecuaciones para L′", "Σ Lᵢ′ yᵢ⁽ᵏ⁾ = 0 (k < n−1);  Σ Lᵢ′ yᵢ⁽ⁿ⁻¹⁾ = g(x)",
                          "", r"\begin{cases} " + r" \\ ".join(filas) + r" \end{cases}",
                          "Las primeras $n-1$ ecuaciones valen cero; la última es $g(x)$."))
    Delta = simplificar(sp.simplify(W.det()))
    if Delta == 0:
        raise NoAplica("El Wronskiano de las soluciones es cero: no forman una base.")
    rhs = sp.Matrix([0] * (n - 1) + [g])
    Lp, deltas = [], []
    for i in range(n):
        Mi = W.copy()
        Mi[:, i] = rhs
        di = simplificar(sp.simplify(Mi.det()))
        deltas.append(di)
        Lp.append(simplificar(sp.simplify(di / Delta)))
    res.pasos.append(Paso("Cuarto paso. Resolver el sistema por Cramer", "Lᵢ′ = Δᵢ / Δ,  Δ = W(y₁,…,yₙ)",
                          r"\Delta = " + _vmatrix(W),
                          rf"\Delta = {L(Delta)}\ ;\quad " + r",\ ".join(f"\\Delta_{{{i}}} = {L(d)}" for i, d in enumerate(deltas, 1)),
                          "$\\Delta_i$ es el determinante de $\\Delta$ con la columna $i$ cambiada por $(0,\\dots,0,g)$."))
    res.pasos.append(Paso("Valores de las derivadas L′", "Lᵢ′ = Δᵢ / Δ", "",
                          r"\ ;\quad ".join(f"L_{{{i}}}' = {L(l)}" for i, l in enumerate(Lp, 1))))
    # integrar
    Ls, textos = [], []
    elemental = True
    for i, lp in enumerate(Lp, 1):
        val, adv, regla = integ(lp, x)
        if adv:
            elemental = False
            a = _limite_inferior(lp)
            val = sp.Integral(lp.subs(x, _t), (_t, a, x))
            res.advertencias.append(
                f"La integral de L_{i}' = {L(lp)} no es elemental y queda indicada (integral definida desde x = {a}; "
                "el límite inferior solo cambia las constantes C).")
            textos.append(rf"L_{{{i}}} = \int {L(lp)}\,dx \ \text{{(no elemental; se toma }}\int_{{{a}}}^{{x}})")
        else:
            val = simplificar(val)
            textos.append(rf"L_{{{i}}} = \int \left({L(lp)}\right)dx = {L(val)}")
        Ls.append(val)
    res.pasos.append(Paso("Quinto paso. Integrar para hallar L₁, …, Lₙ", "Lᵢ = ∫ Lᵢ′ dx (se omiten las constantes: ya están en y_h)",
                          "", r"\ ;\quad ".join(textos),
                          "No se suman constantes de integración: ya están en $y_h$." +
                          ("" if elemental else " Alguna integral es no elemental: se deja indicada.")))
    yp = sum(l * b for l, b in zip(Ls, base))
    yp_s = simplificar(sp.expand(yp)) if elemental else yp
    res.pasos.append(Paso("Sexto paso. Solución particular y_p (el texto la llama y_c)", "reemplazar Lᵢ en y_p", "",
                          "y_p = " + L(yp_s)))
    general = yh + yp_s
    res.pasos.append(Paso("Séptimo paso. Escribir la solución final", "y = y_h + y_p", "", "y = " + L(general)))
    out = _finalizar(res, L_, general, cs, condiciones, yp_s)
    if not elemental and out.verificacion is not None and not out.verificacion.ok:
        out.advertencias.append("Con integrales no elementales la verificación numérica puede no completarse.")
    return out
