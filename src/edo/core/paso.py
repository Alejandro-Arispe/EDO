"""Modelo de salida: cada solver emite Pasos y devuelve un Resultado."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

NOTA_DISCREPANCIA = "Discrepancia con el texto del docente"


@dataclass
class Paso:
    titulo: str
    regla: str = ""
    antes_latex: str = ""
    despues_latex: str = ""
    explicacion: str = ""  # texto en español; las fórmulas van entre $...$
    discrepancia: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Verificacion:
    ok: bool
    como: str  # "simbólica", "numérica (5 puntos)", "no verificada", ...
    detalle: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Resultado:
    metodo: str
    pasos: list[Paso] = field(default_factory=list)
    solucion: str = ""  # LaTeX
    constantes: list[str] = field(default_factory=list)
    verificacion: Verificacion | None = None
    advertencias: list[str] = field(default_factory=list)
    otros_metodos_aplicables: list[dict] = field(default_factory=list)
    valor: object = None  # objeto SymPy de la solución (no se serializa)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("valor", None)
        d["verificacion"] = self.verificacion.to_dict() if self.verificacion else None
        return d
