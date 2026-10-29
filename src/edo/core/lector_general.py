"""Lector de EDO/EDP con cualquier variable: dP/dt = kP, ∂²z/∂x² + ∂z/∂y = 4, z_xx + z_yy = 0.

Sirve para clasificar (ordinaria/parcial, orden, grado, linealidad). Para resolver se usa
``leer_ed`` (y respecto de x).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from .lector import (
    _TRANSF, ErrorLectura, _funciones, _partir_igualdad, desde_latex,
)

_ORDEN_VARS = "xyzt"
_LETRAS = {c: sp.Symbol(c) for c in "abcdfghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"}
_LETRAS["pi"] = sp.pi


@dataclass
class EDGeneral:
    original: str
    dep: str
    indep: list[str]
    f: sp.Expr                # f(x1, ..., xk)
    lhs: sp.Expr
    rhs: sp.Expr
    orden: int

    @property
    def expr(self) -> sp.Expr:
        return self.lhs - self.rhs

    @property
    def tipo(self) -> str:
        return "parcial" if len(self.indep) > 1 else "ordinaria"


_RE_FRAC = re.compile(
    r"([d∂])\s*\^?\{?(\d*)\}?\s*([A-Za-z])\s*/\s*((?:[d∂]\s*[A-Za-z]\s*\^?\{?\d*\}?\s*)+)")
_RE_DEN = re.compile(r"[d∂]\s*([A-Za-z])\s*\^?\{?(\d*)\}?")
_RE_PRIMA = re.compile(r"(?<![A-Za-z_])([A-Za-z])('+)")
_RE_POT = re.compile(r"(?<![A-Za-z_])([A-Za-z])\^\{?\((\d+)\)\}?")
_RE_SUB = re.compile(r"(?<![A-Za-z_])([A-Za-z])_\{?([A-Za-z]{1,6})\}?")


def leer_general(texto: str, *, latex: bool = False) -> EDGeneral:
    original = texto
    if latex:
        texto = desde_latex(texto)
    texto = texto.replace("\\partial", "∂").replace("′", "'")
    izq_s, der_s = _partir_igualdad(texto)
    fichas: list[tuple[str, list[str]]] = []  # (dependiente, [variables de derivación])

    def nueva(dep: str, vars_: list[str]) -> str:
        fichas.append((dep, vars_))
        return f" Zd{len(fichas)} "

    def frac(m):
        dep, n = m.group(3), m.group(2)
        vars_: list[str] = []
        for v, k in _RE_DEN.findall(m.group(4)):
            vars_ += [v] * int(k or 1)
        if n and int(n) != len(vars_):
            raise ErrorLectura(f"En la derivada de {dep} el orden {n} no coincide con el denominador.")
        return nueva(dep, vars_)

    def prima(m):
        return nueva(m.group(1), ["#"] * len(m.group(2)))

    def potencia(m):
        return nueva(m.group(1), ["#"] * int(m.group(2)))

    def sub(m):
        return nueva(m.group(1), list(m.group(2)))

    def tokenizar(s: str) -> str:
        s = _RE_FRAC.sub(frac, s)
        s = _RE_POT.sub(potencia, s)
        s = _RE_PRIMA.sub(prima, s)
        return _RE_SUB.sub(sub, s)

    izq_t, der_t = tokenizar(izq_s), tokenizar(der_s)
    if not fichas:
        raise ErrorLectura("No veo derivadas: no es una ecuación diferencial.")
    deps = {d for d, _ in fichas}
    if len(deps) > 1:
        raise ErrorLectura("Hay más de una función incógnita (sistema): fuera del alcance.")
    dep = deps.pop()
    otras = {v for _, vs in fichas for v in vs if v != "#"}
    if any("#" in vs for _, vs in fichas):
        otras.add("x" if "x" in (otras | set(re.findall(r"[a-z]", izq_s + der_s))) or "t" not in izq_s + der_s else "t")
    indep = sorted(otras, key=lambda v: (_ORDEN_VARS.find(v) if v in _ORDEN_VARS else 99, v))
    if dep in indep:
        raise ErrorLectura("La función incógnita no puede ser también variable independiente.")
    var_prima = indep[0] if len(indep) == 1 else "x"
    f = sp.Function(dep)(*[sp.Symbol(v) for v in indep])

    local = {**_LETRAS}
    local["e"] = sp.E
    for k, (d, vs) in enumerate(fichas, 1):
        local[f"Zd{k}"] = sp.Derivative(
            f, *[sp.Symbol(var_prima if v == "#" else v) for v in vs])

    def parsear(s: str) -> sp.Expr:
        if not s.strip():
            raise ErrorLectura("La expresión está vacía.")
        try:
            e = parse_expr(_funciones(s), local_dict=dict(local), transformations=_TRANSF)
        except ErrorLectura:
            raise
        except Exception as exc:
            raise ErrorLectura(f"No pude interpretar «{s.strip()}»: {exc}") from exc
        return e.subs(sp.Symbol(dep), f)

    lhs, rhs = parsear(izq_t), parsear(der_t)
    orden = max(int(d.derivative_count) for d in (lhs - rhs).atoms(sp.Derivative))
    return EDGeneral(original, dep, indep, f, lhs, rhs, orden)
