"""Registro de los errores conocidos del texto del docente (docs/DISCREPANCIAS.md, Anexo A).

Si el problema que se está resolviendo coincide con uno del registro, el paso afectado
lleva la nota "Discrepancia con el texto del docente".
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import sympy as sp

from .lector import leer_condiciones, leer_ed


@dataclass(frozen=True)
class Entrada:
    id: str
    ed: str
    condiciones: str | None
    paso: str      # clave del paso afectado: "verificacion", "constantes", ...
    nota: str


REGISTRO: list[Entrada] = [
    Entrada("A1", "y'=3-2x", "y(1)=2", "constantes",
            "El texto usó x=2, y=1 (invirtió el par) y obtuvo C=-1. Como y(1)=2 significa x=1, y=2, "
            "se tiene 2 = 3(1) - 1² + C, es decir C=0 y la solución particular es y=3x-x²."),
    Entrada("A2", "(y+3)dx+(4-x)dy=0", "y(7)=0", "constantes",
            "El texto usó x=0, y=7 (invirtió el par). Como y(7)=0 significa x=7, y=0, la solución "
            "particular es y=x-7."),
    Entrada("A6", "y''+4y=3x^3", None, "particular",
            "El texto escribió (4/3)x³ − (9/8)x. Con F(D)=D²+4: 1/(4(1+D²/4))·3x³ = (3/4)(x³ − (3/2)x), "
            "así que y_p = (3/4)x³ − (9/8)x."),
    Entrada("A9", "y''''+y''=sen(2x)", None, "particular",
            "El texto omitió C₃ y C₄: y_h = C₁ + C₂x + C₃cos x + C₄sen x, y la solución es "
            "y = C₁ + C₂x + C₃cos x + C₄sen x + sen(2x)/12."),
    Entrada("A10", "y''-2y'+y=x^3+4x", None, "particular",
            "El texto resolvió con −y. Con F(D)=(D−1)²: 1/(1−D)² = 1+2D+3D²+4D³+…, y_p = x³+6x²+22x+32."),
    Entrada("A11a", "y''-4y'+4y=x e^(3x)", None, "particular",
            "El texto multiplicó por x², pero 3 no es raíz de la ecuación característica (las raíces son 2, 2): "
            "no hay que modificar. y_p = (x − 2)e^(3x)."),
    Entrada("A11b", "y''-4y'+4y=x e^(2x)", None, "particular",
            "La raíz 2 tiene multiplicidad 2: se multiplica por x² (s = multiplicidad, no «grado de Q ≤ orden»). "
            "y_p = (x³/6)e^(2x)."),
    Entrada("A4","(2xy+3)dy-y^2dx=0", None, "solucion",
            "El texto escribió x/y² + 3/(4y⁴) = C. Al integrar queda ∫3/y⁴ dy = −1/y³, así que la solución correcta es "
            "x/y² + 1/y³ = C."),
    Entrada("A5", "(1+e^(x/y))dx+e^(x/y)(1-x/y)dy=0", "y(1)=1", "solucion",
            "El texto escribió ln(x/y) en vez de ln y al volver a la variable original. La solución correcta es "
            "ln(x/y + e^(x/y)) + ln y = ln(1+e), es decir x + y e^(x/y) = 1 + e."),
    Entrada("A3","xy'+x ln y = x sen x + y ln y", None, "verificacion",
            "El texto perdió y' al derivar ln y. Derivando correctamente se obtiene "
            "x y'(1+ln y) = x sen x + y ln y, que no es la ecuación escrita en el texto."),
]


@lru_cache(maxsize=None)
def _ed(texto: str):
    return leer_ed(texto)


@lru_cache(maxsize=None)
def _conds(texto: str):
    return tuple((c.orden, c.x0, c.valor) for c in leer_condiciones(texto))


def _misma_ed(a, b) -> bool:
    try:
        return sp.simplify(a.expr - b.expr) == 0 or sp.simplify(a.expr + b.expr) == 0
    except Exception:
        return False


def nota(paso: str, ed, condiciones=None) -> str | None:
    """Nota de discrepancia para ``paso`` si el problema coincide con uno del registro."""
    conds = tuple((c.orden, c.x0, c.valor) for c in (condiciones or []))
    for e in REGISTRO:
        if e.paso != paso or not _misma_ed(ed, _ed(e.ed)):
            continue
        if e.condiciones is not None and conds != _conds(e.condiciones):
            continue
        return f"[{e.id}] {e.nota}"
    return None
