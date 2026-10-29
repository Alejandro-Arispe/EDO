"""Punto de entrada único: elige el resolutor según el orden de la ED."""
from __future__ import annotations

from .core.lector import ED
from .core.paso import Resultado
from .orden_superior import resolutor as _superior
from .primer_orden import resolutor as _primero
from .primer_orden.base import NoAplica


def clasificar_metodos(ed: ED) -> list[dict]:
    if ed.orden == 1:
        return _primero.clasificar_metodos(ed)
    return _superior.clasificar_metodos(ed)


def resolver(ed: ED, metodo: str | None = None, condiciones=None) -> Resultado:
    if ed.orden == 1:
        return _primero.resolver(ed, metodo, condiciones)
    if ed.orden >= 2:
        return _superior.resolver(ed, metodo, condiciones)
    raise NoAplica("La ecuación no tiene derivadas: no es una ecuación diferencial.")
