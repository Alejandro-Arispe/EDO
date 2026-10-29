"""Clasificación de una ED: ordinaria/parcial, orden, grado, lineal, homogénea.

Definiciones del docente:
  * Orden: la mayor derivada que aparece.
  * Grado: exponente de la mayor derivada cuando la ED es polinomial en las derivadas
    (se racionalizan radicales); si una derivada está dentro de ln, sen, e^, ... no tiene grado.
  * Lineal: y y sus derivadas son de primer grado y los coeficientes dependen solo de x.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp
from sympy.core.function import AppliedUndef

from ..core.latex import latex
from ..core.lector import ED, y as _y, x as _x
from ..core.lector_general import EDGeneral
from ..core.paso import Paso

_ORDINALES = ["", "primer", "segundo", "tercer", "cuarto", "quinto", "sexto", "séptimo", "octavo", "noveno", "décimo"]


def ordinal(n: int) -> str:
    return _ORDINALES[n] if 0 < n < len(_ORDINALES) else f"de orden {n}"


@dataclass
class Clasificacion:
    tipo: str                       # "ordinaria" | "parcial"
    orden: int
    grado: int | None
    grado_motivo: str
    lineal: bool
    lineal_motivo: str
    homogenea: bool | None          # None si no es lineal
    lineal_en_x: bool | None = None  # solo forma diferencial
    pasos: list[Paso] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"tipo": self.tipo, "orden": self.orden, "grado": self.grado, "grado_motivo": self.grado_motivo,
                "lineal": self.lineal, "lineal_motivo": self.lineal_motivo, "homogenea": self.homogenea,
                "lineal_en_x": self.lineal_en_x, "pasos": [p.to_dict() for p in self.pasos]}


def _preparar(ed):
    """(F, f, indep_symbols) para ED o EDGeneral."""
    if isinstance(ed, ED):
        return ed.expr, _y(_x), [_x]
    if isinstance(ed, EDGeneral):
        return ed.expr, ed.f, [sp.Symbol(v) for v in ed.indep]
    raise TypeError("se espera una ED leída")


def _simbolos(F, f):
    ders = sorted(F.atoms(sp.Derivative), key=lambda d: (-int(d.derivative_count), str(d)))
    u0 = sp.Symbol("u0")
    sub = {}
    syms = []
    for k, d in enumerate(ders, 1):
        s = sp.Symbol(f"p{k}")
        sub[d] = s
        syms.append((d, s))
    G = F.subs(sub).subs(f, u0)
    return G, u0, syms


def _grado(G, u0, syms) -> tuple[int | None, str, sp.Expr | None]:
    dsyms = [s for _, s in syms]
    todos = dsyms
    for fn in G.atoms(sp.Function):
        if fn.has(*todos):
            return None, f"la derivada aparece dentro de {latex(fn)}, que no es una expresión polinomial en las derivadas", None
    top_orden = max(int(d.derivative_count) for d, _ in syms)
    tops = [s for d, s in syms if int(d.derivative_count) == top_orden]
    H = sp.expand(G)
    # denominadores con derivadas
    num, den = sp.fraction(sp.together(H))
    if den.has(*todos):
        H = sp.expand(num)
    # radicales con derivadas
    cambio = False
    for _ in range(6):
        radicales = [p for p in H.atoms(sp.Pow)
                     if p.exp.is_Rational and not p.exp.is_Integer and p.base.has(*todos)]
        if not radicales:
            break
        cambio = True
        p = radicales[0]
        q = p.exp.q
        r = sp.Dummy("r", positive=True)
        base = p.base
        H = H.xreplace({sp.Pow(base, sp.Rational(k, q)): r ** k for k in range(-2 * q, 2 * q + 1) if k % q})
        H = sp.expand(sp.fraction(sp.together(H))[0]) if H.has(r) and sp.fraction(sp.together(H))[1].has(r) else H
        if H.has(r):
            H = sp.expand(sp.resultant(H, r ** q - base, r))
    if H.has(*[sp.Pow]) and any(p.exp.is_Rational and not p.exp.is_Integer and p.base.has(*todos)
                                for p in H.atoms(sp.Pow)):
        return None, "no pude racionalizar los radicales de las derivadas", None
    if not H.is_polynomial(*todos):
        return None, "no es polinomial en las derivadas", None
    g = max(sp.degree(H, t) for t in tops)
    if g == 0:
        return None, "la derivada mayor desapareció al racionalizar", None
    motivo = ("Se racionaliza la ecuación para expresarla en forma polinomial en las derivadas." if cambio
              else "La ecuación está expresada en forma polinomial en las derivadas.")
    return int(g), motivo, (H if cambio else None)


def _lineal(G, u0, syms) -> tuple[bool, str, sp.Expr | None]:
    """¿Lineal en u0 y sus derivadas con coeficientes de las variables independientes?"""
    vars_ = [u0] + [s for _, s in syms]
    G = sp.expand(G)
    if not G.is_polynomial(*vars_):
        malos = [fn for fn in G.atoms(sp.Function) if fn.has(*vars_)]
        if malos:
            return False, f"la incógnita o una derivada está dentro de {latex(malos[0])}", None
        return False, "la incógnita o sus derivadas aparecen con exponente distinto de 1 (o en un denominador)", None
    P = sp.Poly(G, *vars_)
    if P.total_degree() > 1:
        for mon, _ in P.terms():
            if sum(mon) > 1:
                prod = sp.Mul(*[v ** e for v, e in zip(vars_, mon) if e])
                txt = latex(prod).replace("u_{0}", "y").replace("u0", "y")
                if max(mon) > 1:
                    return False, "una variable o derivada tiene exponente distinto de 1", None
                return False, "hay productos entre la incógnita y/o sus derivadas", None
        return False, "no es de primer grado en la incógnita y sus derivadas", None
    q = -P.coeff_monomial(1)
    return True, "y y sus derivadas son de primer grado y los coeficientes dependen solo de la variable independiente", q


def clasificar(ed) -> Clasificacion:
    F, f, indep = _preparar(ed)
    G, u0, syms = _simbolos(F, f)
    tipo = "parcial" if len(indep) > 1 else "ordinaria"
    if not syms:
        raise ValueError("No es una ecuación diferencial: no tiene derivadas.")
    orden = max(int(d.derivative_count) for d, _ in syms)
    mayor = next(d for d, _ in syms if int(d.derivative_count) == orden)
    pasos: list[Paso] = []
    nombre_f = f.func.__name__
    vars_txt = ", ".join(latex(v) for v in indep)
    pasos.append(Paso(
        "Ecuación diferencial " + tipo, "clasificación por número de variables independientes",
        latex(ed.lhs) + " = " + latex(ed.rhs), "",
        (f"La función incógnita ${nombre_f}$ depende de una sola variable independiente (${vars_txt}$): ecuación diferencial ordinaria."
         if tipo == "ordinaria" else
         f"La función incógnita ${nombre_f}$ depende de {len(indep)} variables independientes (${vars_txt}$) y aparecen derivadas parciales: ecuación diferencial parcial.")))
    pasos.append(Paso("Orden", "mayor derivada de la ecuación", latex(mayor), "",
                      f"La mayor derivada es ${latex(mayor)}$: la ecuación es de {ordinal(orden)} orden."))
    grado, motivo, racional = _grado(G, u0, syms)
    if grado is None:
        pasos.append(Paso("Grado", "exponente de la mayor derivada", "", "",
                          f"No tiene grado: {motivo}."))
    else:
        desp = ""
        if racional is not None:
            rac = racional.subs({s: d for d, s in syms}).subs(u0, f)
            desp = latex(rac) + " = 0"
        pasos.append(Paso("Grado", "exponente de la mayor derivada", "", desp,
                          f"{motivo} El exponente de la mayor derivada es {grado}: {ordinal(grado)} grado."))
    lineal, lmot, q = (False, "", None)
    lineal_en_x = None
    if tipo == "ordinaria":
        lineal, lmot, q = _lineal(G, u0, syms)
        if not lineal and isinstance(ed, ED) and ed.forma == "diferencial":
            lineal_en_x, _, _ = _lineal_en_x(ed)
    else:
        lineal, lmot, q = _lineal(G, u0, syms)
    homogenea = None
    if lineal:
        homogenea = (sp.simplify(q) == 0)
        pasos.append(Paso("Linealidad", "y y sus derivadas de primer grado; coeficientes solo de la variable independiente",
                          "", "", "Es lineal: " + lmot + "."))
        pasos.append(Paso("Homogénea / no homogénea", "término independiente q", "",
                          f"q = {latex(q)}",
                          "Homogénea: no queda término independiente de la incógnita ($q=0$)." if homogenea else
                          "No homogénea: queda un término independiente de la incógnita ($q\\neq 0$)."))
    else:
        extra = ""
        if lineal_en_x:
            extra = " Sin embargo es lineal si se toma $x$ como función de $y$ (lineal en $x$)."
        pasos.append(Paso("Linealidad", "y y sus derivadas de primer grado; coeficientes solo de la variable independiente",
                          "", "", "No lineal: " + lmot + "." + extra))
    return Clasificacion(tipo, orden, grado, motivo, lineal, lmot, homogenea, lineal_en_x, pasos)


def _lineal_en_x(ed: ED):
    """Forma diferencial M dx + N dy: lineal si se escribe x'(y) con x(y) y sus derivadas de grado 1."""
    X = sp.Function("x")(sp.Symbol("y"))
    yy = sp.Symbol("y")
    F = ed.M * sp.Derivative(X, yy) + ed.N
    F = F.subs(_x, X)
    G, u0, syms = _simbolos(F, X)
    if not syms:
        return False, "", None
    return _lineal(G, u0, syms)
