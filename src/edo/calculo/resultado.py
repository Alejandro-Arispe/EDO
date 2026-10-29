"""Resultado común de derivadas e integrales con pasos."""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from ..core.latex import latex
from ..core.paso import Paso, Verificacion


class ErrorCalculo(ValueError):
    """La expresión queda fuera de las reglas programadas (mensaje en español)."""


@dataclass
class ResultadoCalculo:
    enunciado: sp.Expr | str
    valor: sp.Expr | None            # None si no se pudo (integral no elemental)
    pasos: list[Paso] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)
    verificacion: Verificacion | None = None
    elemental: bool = True
    enunciado_latex: str = ""
    resultado_latex: str = ""

    def to_dict(self) -> dict:
        return {
            "enunciado_latex": self.enunciado_latex,
            "resultado_latex": self.resultado_latex or (latex(self.valor) if self.valor is not None else ""),
            "pasos": [p.to_dict() for p in self.pasos],
            "advertencias": self.advertencias,
            "verificacion": self.verificacion.to_dict() if self.verificacion else None,
            "elemental": self.elemental,
        }
