"""Comandos de GeoGebra para graficar las soluciones.

Las constantes C, C1, C2… se escriben c, c_1, c_2… (en GeoGebra «C1» es una celda de la hoja de
cálculo) y se acompañan de deslizadores para ver la familia de curvas.
"""
from __future__ import annotations

import re

import sympy as sp
from sympy.printing.str import StrPrinter

from .lector import x, ys

_CTE = re.compile(r"^C(\d*)$")


class _Impresor(StrPrinter):
    def _print_Symbol(self, e):
        m = _CTE.match(e.name)
        if m:
            return "c" + (f"_{m.group(1)}" if m.group(1) else "")
        return super()._print_Symbol(e)

    def _print_log(self, e):
        return f"ln({self._print(e.args[0])})"

    def _print_Pow(self, e):
        return super()._print_Pow(e).replace("**", "^")

    def _print_Abs(self, e):
        return f"abs({self._print(e.args[0])})"

    def _print_Exp1(self, e):
        return "e"

    def _print_Integral(self, e):
        f, (t, a, b) = e.function, e.limits[0]
        return f"Integral({self._print(f.subs(t, x))}, {self._print(a)}, {self._print(b)})"


_imp = _Impresor()


def expr(e) -> str:
    return _imp.doprint(sp.sympify(e)).replace("**", "^")


def _deslizadores(*exprs) -> list[str]:
    nombres = set()
    for e in exprs:
        for s in sp.sympify(e).free_symbols:
            if _CTE.match(s.name):
                nombres.add(s.name)
    return [f"{expr(sp.Symbol(n))} = Slider(-5, 5, 0.1)" for n in sorted(nombres)]


def comandos(valor, extra=()) -> list[str]:
    """Lista de comandos (uno por línea) para pegar en la barra de entrada de GeoGebra."""
    from ..primer_orden.base import Solucion
    objetos = []
    if isinstance(valor, (list, tuple)):
        objetos += list(valor)
    elif valor is not None:
        objetos.append(valor)
    objetos += list(extra)
    sliders: list[str] = []
    lineas: list[str] = []
    n = 0
    for o in objetos:
        if isinstance(o, Solucion):
            if o.param is not None:
                xp, yp = o.param
                sliders += _deslizadores(xp, yp)
                p = [s for s in (xp.free_symbols | yp.free_symbols) if s.name == "p"]
                lineas.append(f"Curve({expr(xp)}, {expr(yp)}, p, -5, 5)")
            elif o.explicita:
                n += 1
                sliders += _deslizadores(o.der)
                lineas.append(f"f_{n}(x) = {expr(o.der)}")
            else:
                sliders += _deslizadores(o.izq, o.der)
                lineas.append(f"{expr(o.izq)} = {expr(o.der)}")
        elif isinstance(o, sp.Basic):
            n += 1
            sliders += _deslizadores(o)
            lineas.append(f"f_{n}(x) = {expr(o)}")
    vistos = []
    for s in sliders:
        if s not in vistos:
            vistos.append(s)
    return vistos + lineas
