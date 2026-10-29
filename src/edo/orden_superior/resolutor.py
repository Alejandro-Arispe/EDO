"""Despachador para ED lineales de orden superior (n ≥ 2)."""
from __future__ import annotations

from ..core.lector import ED
from ..core.paso import Resultado
from ..primer_orden.base import NoAplica
from . import lineal_cc

METODOS = {
    "abreviado": ("Método abreviado (operador D)", lineal_cc.aplica_abreviado, lineal_cc.resolver_abreviado),
    "coeficientes_indeterminados": ("Coeficientes indeterminados", lineal_cc.aplica_coef_indeterminados,
                                    lineal_cc.resolver_coef_indeterminados),
}
PREFERENCIA = ["abreviado", "coeficientes_indeterminados"]


def clasificar_metodos(ed: ED) -> list[dict]:
    if ed.orden < 2:
        return []
    out = []
    for m in PREFERENCIA:
        titulo, aplica, _ = METODOS[m]
        try:
            motivo = aplica(ed)
        except Exception:
            motivo = None
        if motivo:
            out.append({"metodo": m, "titulo": titulo, "motivo": motivo})
    return out


def resolver(ed: ED, metodo: str | None = None, condiciones=None) -> Resultado:
    cand = clasificar_metodos(ed)
    elegido = metodo or (cand[0]["metodo"] if cand else None)
    if elegido is None:
        return _ninguno(ed)
    if elegido not in METODOS:
        raise NoAplica(f"Método desconocido o todavía no disponible: {elegido}.")
    r = METODOS[elegido][2](ed, condiciones)
    r.otros_metodos_aplicables = [c for c in cand if c["metodo"] != elegido]
    r.advertencias = list(dict.fromkeys(r.advertencias))
    return r


def _ninguno(ed: ED) -> Resultado:
    res = Resultado("ninguno")
    res.advertencias.append(
        "No aplica con los métodos del temario implementados hasta ahora (método abreviado y coeficientes indeterminados). "
        "Si la ecuación es lineal de coeficientes constantes y Q(x) no es de la forma xᵏ e^(ax) sen/cos(bx), o si los coeficientes "
        "son variables (Euler, Cauchy-Legendre), faltan las fases de variación de parámetros y coeficiente variable.")
    try:
        lineal_cc.leer_lineal(ed)
    except NoAplica as exc:
        res.advertencias.append("Se intentó — coeficientes constantes: " + str(exc))
    else:
        try:
            lineal_cc._grupos(lineal_cc.leer_lineal(ed).Q)
        except NoAplica as exc:
            res.advertencias.append("Se intentó — forma de Q(x): " + str(exc))
    return res
