"""Simplificación suave: factorizar y juntar fracciones sin reescribir trigonometría."""
from __future__ import annotations

import sympy as sp


def simplificar(e: sp.Expr) -> sp.Expr:
    """Devuelve la forma equivalente más corta entre las candidatas algebraicas.

    ``sp.simplify`` a veces cambia sen/cos por formas que el docente no escribiría
    (p. ej. sen(2x) o sen(x+π/4)); aquí solo se usan operaciones algebraicas.
    """
    candidatas = [e]
    for f in (sp.expand, sp.factor_terms, sp.together, sp.factor, sp.cancel, sp.powsimp):
        try:
            candidatas.append(f(e))
        except Exception:
            continue
    try:
        candidatas.append(sp.factor_terms(sp.together(sp.expand(e))))
    except Exception:
        pass
    return min(candidatas, key=lambda c: (sp.count_ops(c), 0))
