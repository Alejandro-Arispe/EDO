"""Piezas comunes de los métodos de primer orden."""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..calculo.integrales import integrar
from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x, y, ys
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import (
    es_cero, verificar_explicita, verificar_implicita,
)

p = sp.Symbol("p")   # p = y'
C = sp.Symbol("C")
NOTA_ABS = ("Se escribe ln u en lugar de ln|u|; vale en los intervalos donde el argumento es positivo "
            "(en general la solución lleva valor absoluto).")


class NoAplica(Exception):
    """El método no se puede aplicar a esta ecuación (el mensaje dice por qué)."""


@dataclass
class Solucion:
    """Relación izq = der (der puede ser la constante C), o curva paramétrica (x(p), y(p))."""
    izq: sp.Expr | None = None
    der: sp.Expr | None = None
    param: tuple[sp.Expr, sp.Expr] | None = None  # (x(p), y(p))

    @property
    def explicita(self) -> bool:
        return self.param is None and self.izq == ys and ys not in self.der.free_symbols

    def latex(self) -> str:
        if self.param is not None:
            return (r"\begin{cases} x = " + latex(self.param[0]) + r" \\ y = " + latex(self.param[1]) + r"\end{cases}")
        return latex(self.izq) + " = " + latex(self.der)


@dataclass
class Forma:
    F: sp.Expr                 # F(x, y, p) = 0 con p = y'
    M: sp.Expr | None = None   # M dx + N dy = 0 (si F es lineal en p)
    N: sp.Expr | None = None
    f: sp.Expr | None = None   # y' = f(x, y)


def forma(ed: ED) -> Forma:
    if ed.orden != 1:
        raise NoAplica("No es de primer orden.")
    d1 = sp.Derivative(y(x), x)
    F = ed.expr.subs(d1, p).subs(y(x), ys)
    if ed.forma == "diferencial":
        M, N = ed.M, ed.N
    else:
        N, M = sp.diff(F, p), F.subs(p, 0)
        if N.has(p) or N == 0 or not F.is_polynomial(p):
            return Forma(F)
    if N == 0:
        return Forma(F, M, N, None)
    return Forma(F, M, N, sp.together(-M / N))


def _agrupar_cociente(expr: sp.Expr) -> sp.Expr:
    """n/d -> suma de (coeficiente/d)·función para cada función trascendente de n (p. ej. e^y)."""
    n, d = sp.fraction(sp.together(expr))
    if d == 1:
        return expr
    funcs = [f for f in sp.expand(n).atoms(sp.Function)] + [e for e in sp.expand(n).atoms(sp.Pow) if e.exp.has(sp.Symbol)]
    if not funcs:
        return expr
    partes = sp.collect(sp.expand(n), funcs, evaluate=False)
    return sp.Add(*[sp.cancel(c / d) * k for k, c in partes.items()])


def integ(expr: sp.Expr, var: sp.Symbol) -> tuple[sp.Expr, list[str], str]:
    """∫ expr d var (sin constante). Devuelve (valor, advertencias, reglas usadas)."""
    expr = sp.sympify(expr)
    if expr == 0:
        return sp.Integer(0), [], ""
    variantes = [expr]
    def _sec_csc(e):
        return e.replace(lambda a: isinstance(a, sp.Pow) and isinstance(a.base, (sp.cos, sp.sin)) and a.exp.is_negative,
                         lambda a: (sp.sec if isinstance(a.base, sp.cos) else sp.csc)(a.base.args[0]) ** (-a.exp))
    def _pitagoras(e, por):
        s = e.replace(sp.tan, lambda u: sp.sin(u) / sp.cos(u)).replace(sp.cot, lambda u: sp.cos(u) / sp.sin(u))
        s = s.replace(sp.sec, lambda u: 1 / sp.cos(u)).replace(sp.csc, lambda u: 1 / sp.sin(u))
        s = sp.expand(s)
        a, b = (sp.sin, sp.cos) if por == "sin" else (sp.cos, sp.sin)
        s = s.replace(lambda q: isinstance(q, sp.Pow) and isinstance(q.base, a) and q.exp == 2,
                      lambda q: 1 - b(q.base.args[0]) ** 2)
        return _sec_csc(sp.expand(s))
    def _solo_sen_cos(e):
        s = e.replace(sp.tan, lambda u: sp.sin(u) / sp.cos(u)).replace(sp.cot, lambda u: sp.cos(u) / sp.sin(u))
        return sp.expand(s.replace(sp.sec, lambda u: 1 / sp.cos(u)).replace(sp.csc, lambda u: 1 / sp.sin(u)))
    for g in (_sec_csc, _solo_sen_cos, lambda e: _pitagoras(e, "sin"), lambda e: _pitagoras(e, "cos"), lambda e: e.rewrite(sp.cot), sp.expand, _agrupar_cociente, lambda e: sp.apart(e, var), sp.simplify):
        try:
            v = g(expr)
        except Exception:
            continue
        if v != expr and v not in variantes:
            variantes.append(v)
    mejor = None
    for v in variantes:
        r = integrar(v, var)
        if r.valor is not None:
            costo = sp.count_ops(r.valor)
            if mejor is None or costo < mejor[0]:
                mejor = (costo, r)
    r = mejor[1] if mejor else integrar(expr, var)
    if r.valor is None:
        return sp.Integral(expr, var), [f"La integral de {latex(expr)} no es elemental y queda indicada."], "integral no elemental"
    reglas = []
    for s in r.pasos:
        t = s.titulo
        if t not in ("Simplificar", "Resultado") and t not in reglas:
            reglas.append(t)
    return r.valor, [], ", ".join(reglas[:4]).lower()


def paso_integral(titulo: str, antes: str, valor_latex: str, reglas: str) -> Paso:
    return Paso(titulo, "integral indefinida", antes, valor_latex,
                ("Reglas: " + reglas + ".") if reglas else "")


def sustituir_y(e: sp.Expr, nuevo: sp.Expr) -> sp.Expr:
    return e.subs(ys, nuevo)


def despejar_y(izq: sp.Expr, der: sp.Expr) -> sp.Expr | None:
    """Solución explícita única y elemental de izq = der respecto de y, o None."""
    G = izq - der
    if G.is_polynomial(ys) and sp.degree(G, ys) > 2:
        return None   # Cardano: la solución explícita no sería legible
    try:
        sols = sp.solve(sp.Eq(izq, der), ys)
    except Exception:
        return None
    sols = [s for s in sols if not s.has(sp.LambertW, sp.RootOf, sp.CRootOf, sp.I)]
    if len(sols) == 1 and not sols[0].has(sp.Integral):
        return sols[0]
    return None


def combinar(G: sp.Expr) -> sp.Expr:
    """Agrupa logaritmos y radicales de una relación implícita G(x, y) = C (con x, y > 0)."""
    xp, yp = sp.Symbol("x", positive=True), sp.Symbol("y", positive=True)
    try:
        H = sp.simplify(sp.logcombine(G.subs({x: xp, ys: yp}), force=True)).subs({xp: x, yp: ys})
    except Exception:
        return G
    return H if sp.count_ops(H) < sp.count_ops(G) else G


def verificar(ed: ED, sol: Solucion) -> Verificacion:
    if sol.param is not None:
        from .parametrica import verificar_parametrica
        return verificar_parametrica(ed, sol.param[0], sol.param[1])
    if sol.explicita:
        return verificar_explicita(ed, sol.der)
    return verificar_implicita(ed, sol.izq, sol.der)


def finalizar(res: Resultado, ed: ED, sol: Solucion, condiciones=None) -> Resultado:
    """Aplica condiciones iniciales (si hay), verifica en la ED original y completa el Resultado."""
    from ..conceptos.constantes import determinar_constantes, constantes_de
    res.valor = sol
    res.solucion = sol.latex()
    cs = constantes_de(sol.izq - sol.der) if sol.param is None else []
    res.constantes = [c.name for c in cs]
    if condiciones and sol.param is None:
        det = determinar_constantes(ed, sol.izq, sol.der, condiciones)
        res.pasos += [s for s in det.pasos[1:] if s.titulo != "Comprobación"]
        res.advertencias += det.advertencias
        if det.valor is not None:
            sol = Solucion(ys, det.valor) if sol.explicita else Solucion(det.valor, sp.Integer(0))
            res.valor, res.solucion = sol, sol.latex()
            res.verificacion, res.constantes = det.verificacion, []
            return res
        res.verificacion = Verificacion(False, "no verificada", "no se pudieron determinar las constantes")
        return res
    if condiciones and sol.param is not None:
        res.advertencias.append("Las condiciones iniciales no se aplican a la solución paramétrica (cada valor de p da un punto).")
    v = verificar(ed, sol)
    res.verificacion = v
    if not v.ok:
        res.advertencias.append("La verificación por sustitución no confirmó la solución: no la tomes como correcta.")
    return res


def misma_curva(G1: sp.Expr, G2: sp.Expr) -> bool:
    """¿G1=const y G2=const tienen las mismas curvas de nivel? (gradientes paralelos)."""
    cruz = sp.diff(G1, x) * sp.diff(G2, ys) - sp.diff(G1, ys) * sp.diff(G2, x)
    return es_cero(cruz).ok
