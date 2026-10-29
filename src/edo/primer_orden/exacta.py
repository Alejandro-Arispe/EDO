"""Ecuaciones exactas M dx + N dy = 0, con ∂M/∂y = ∂N/∂x; y hallar M, N o un parámetro k
para que lo sean."""
from __future__ import annotations

import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import QQ, ED, ErrorLectura, leer_ed, x, ys
from ..core.paso import Paso, Resultado
from ..core.verificador import es_cero
from .base import C, NoAplica, Solucion, despejar_y, finalizar, forma, integ, paso_integral

g = sp.Function("g")


def _MN(ed: ED):
    if ed.forma == "diferencial":
        return ed.M, ed.N
    fm = forma(ed)
    return fm.M, fm.N


def aplica_exacta(ed: ED) -> str | None:
    try:
        M, N = _MN(ed)
    except NoAplica:
        return None
    if M is None or N is None or M.has(QQ) or N.has(QQ):
        return None
    if es_cero(sp.diff(M, ys) - sp.diff(N, x)).ok:
        return "∂M/∂y = ∂N/∂x"
    return None


def resolver_exacta(ed: ED, condiciones=None) -> Resultado:
    M, N = _MN(ed)
    if M is None or N is None:
        raise NoAplica("La ecuación no tiene la forma M dx + N dy = 0.")
    if M.has(QQ) or N.has(QQ):
        return hallar_para_exacta(ed, condiciones)
    My, Nx = sp.diff(M, ys), sp.diff(N, x)
    res = Resultado("exacta")
    res.pasos.append(Paso("Escribir la ecuación en la forma M dx + N dy = 0", "M(x,y) dx + N(x,y) dy = 0",
                          latex(ed.lhs) + " = " + latex(ed.rhs),
                          rf"M = {latex(M)}\ ;\quad N = {latex(N)}"))
    ok = es_cero(My - Nx).ok
    res.pasos.append(Paso("Verificar si la ecuación es exacta", r"\partial M/\partial y = \partial N/\partial x",
                          rf"\frac{{\partial M}}{{\partial y}} = {latex(My)}\ ;\quad \frac{{\partial N}}{{\partial x}} = {latex(Nx)}",
                          r"\frac{\partial M}{\partial y} = \frac{\partial N}{\partial x}" if ok else r"\frac{\partial M}{\partial y} \neq \frac{\partial N}{\partial x}",
                          "Son iguales: la ecuación es exacta." if ok else "No son iguales: la ecuación NO es exacta."))
    if not ok:
        raise NoAplica("∂M/∂y ≠ ∂N/∂x: la ecuación no es exacta.")
    f = None
    for primero in ("x", "y"):
        f = _construir(res, M, N, primero)
        if f is not None:
            break
    if f is None:
        raise NoAplica("No pude determinar la función f(x,y) con integrales elementales.")
    res.pasos.append(Paso("Escribir la solución", "f(x,y) = C", "", latex(f) + " = C"))
    sol = Solucion(f, C)
    e = despejar_y(f, C)
    if e is not None:
        sol = Solucion(ys, e)
    return finalizar(res, ed, sol, condiciones)


def _construir(res: Resultado, M, N, primero: str):
    """Integra M respecto de x (primero='x') o N respecto de y. Devuelve f o None; añade pasos solo si funciona."""
    pasos = []
    if primero == "x":
        I, adv, rg = integ(M, x)
        if adv:
            return None
        pasos.append(paso_integral("Integrar M respecto de x", rf"f(x,y) = \int M\,dx + g(y) = \int \left({latex(M)}\right)dx + g(y)",
                                   rf"f(x,y) = {latex(I)} + g(y)", rg))
        resto = simplificar(N - sp.diff(I, ys))
        pasos.append(Paso("Derivar f respecto de y y comparar con N", r"\partial f/\partial y = N", rf"\frac{{\partial f}}{{\partial y}} = {latex(sp.diff(I, ys))} + g'(y)",
                          rf"g'(y) = {latex(resto)}"))
        if resto.has(x):
            return None
        gy, adv, rg2 = integ(resto, ys)
        if adv:
            return None
        pasos.append(paso_integral("Integrar g'(y)", rf"g(y) = \int {latex(resto)}\,dy", "g(y) = " + latex(gy), rg2))
        f = I + gy
    else:
        I, adv, rg = integ(N, ys)
        if adv:
            return None
        pasos.append(paso_integral("Integrar N respecto de y", rf"f(x,y) = \int N\,dy + h(x) = \int \left({latex(N)}\right)dy + h(x)",
                                   rf"f(x,y) = {latex(I)} + h(x)", rg))
        resto = simplificar(M - sp.diff(I, x))
        pasos.append(Paso("Derivar f respecto de x y comparar con M", r"\partial f/\partial x = M", rf"\frac{{\partial f}}{{\partial x}} = {latex(sp.diff(I, x))} + h'(x)",
                          rf"h'(x) = {latex(resto)}"))
        if resto.has(ys):
            return None
        hx, adv, rg2 = integ(resto, x)
        if adv:
            return None
        pasos.append(paso_integral("Integrar h'(x)", rf"h(x) = \int {latex(resto)}\,dx", "h(x) = " + latex(hx), rg2))
        f = I + hx
    res.pasos += pasos
    return simplificar(f)


# ------------------------------------------------ hallar M, N o k para que sea exacta
def hallar_para_exacta(ed: ED, condiciones=None) -> Resultado:
    """M o N desconocido (escrito «?»), o un parámetro k: se halla lo necesario y se resuelve."""
    M, N = _MN(ed)
    res = Resultado("hallar M, N o k para que sea exacta")
    if M.has(QQ):
        if N.has(QQ):
            raise NoAplica("Hay dos incógnitas (M y N): no es posible determinarlas.")
        Mnuevo = sp.integrate(sp.diff(N, x), ys)   # ∫ ∂N/∂x dy, sin g(x)
        res.pasos.append(Paso("Condición de exactitud", r"\partial M/\partial y = \partial N/\partial x", "",
                              rf"\frac{{\partial M}}{{\partial y}} = {latex(sp.diff(N, x))}"))
        Mn, adv, rg = integ(sp.diff(N, x), ys)
        res.pasos.append(paso_integral("Integrar respecto de y para hallar M", rf"M = \int {latex(sp.diff(N, x))}\,dy + g(x)",
                                       rf"M(x,y) = {latex(Mn)} + g(x)", rg))
        res.pasos.append(Paso("Elegir g(x)", "cualquier g(x) sirve", "", rf"M(x,y) = {latex(Mn)}",
                              "Se toma $g(x)=0$ (la forma más simple); cualquier $g(x)$ también hace exacta la ecuación."))
        M, N = Mn, N
    elif N.has(QQ):
        res.pasos.append(Paso("Condición de exactitud", r"\partial M/\partial y = \partial N/\partial x", "",
                              rf"\frac{{\partial N}}{{\partial x}} = {latex(sp.diff(M, ys))}"))
        Nn, adv, rg = integ(sp.diff(M, ys), x)
        res.pasos.append(paso_integral("Integrar respecto de x para hallar N", rf"N = \int {latex(sp.diff(M, ys))}\,dx + h(y)",
                                       rf"N(x,y) = {latex(Nn)} + h(y)", rg))
        res.pasos.append(Paso("Elegir h(y)", "cualquier h(y) sirve", "", rf"N(x,y) = {latex(Nn)}",
                              "Se toma $h(y)=0$ (la forma más simple)."))
        M, N = M, Nn
    else:
        raise NoAplica("No hay incógnita «?».")
    nuevo = ED(ed.original, "diferencial", sp.Integer(0), sp.Integer(0), 1, M=M, N=N)
    nuevo.lhs = M + N * sp.Derivative(sp.Function("y")(x), x)
    nuevo.lhs = nuevo.lhs.subs(ys, sp.Function("y")(x))
    sub = resolver_exacta(nuevo, condiciones)
    res.pasos += sub.pasos
    res.advertencias += sub.advertencias
    res.solucion, res.valor, res.verificacion, res.constantes = sub.solucion, sub.valor, sub.verificacion, sub.constantes
    res.metodo = "exacta (hallando M o N)"
    res.advertencias.append(f"M = {latex(M)}, N = {latex(N)} hacen exacta la ecuación.")
    return res


def hallar_k(ed: ED, k: sp.Symbol, condiciones=None) -> Resultado:
    """Valor de la constante k para que M dx + N dy = 0 sea exacta; resuelve con ese valor."""
    M, N = _MN(ed)
    res = Resultado("hallar k para que sea exacta")
    dif = sp.expand(sp.diff(M, ys) - sp.diff(N, x))
    res.pasos.append(Paso("Condición de exactitud", r"\partial M/\partial y = \partial N/\partial x",
                          rf"\frac{{\partial M}}{{\partial y}} = {latex(sp.diff(M, ys))}\ ;\quad \frac{{\partial N}}{{\partial x}} = {latex(sp.diff(N, x))}",
                          rf"{latex(dif)} = 0", "La diferencia debe ser cero para todo $x$, $y$."))
    coef = sp.Poly(dif, x, ys).coeffs() if dif != 0 else []
    sol = sp.solve(coef, k, dict=True) if coef else [{}]
    if not sol:
        raise NoAplica(f"Ningún valor de {k} hace exacta la ecuación.")
    kv = sol[0].get(k)
    res.pasos.append(Paso(f"Hallar el valor de {k}", "igualar a cero los coeficientes", "", f"{latex(k)} = {latex(kv)}"))
    M2, N2 = M.subs(k, kv), N.subs(k, kv)
    nuevo = ED(ed.original, "diferencial", sp.Integer(0), sp.Integer(0), 1, M=M2, N=N2)
    nuevo.lhs = (M2 + N2 * sp.Derivative(sp.Function("y")(x), x)).subs(ys, sp.Function("y")(x))
    sub = resolver_exacta(nuevo, condiciones)
    res.pasos += sub.pasos
    res.advertencias += sub.advertencias
    res.solucion, res.valor, res.verificacion, res.constantes = sub.solucion, sub.valor, sub.verificacion, sub.constantes
    return res
