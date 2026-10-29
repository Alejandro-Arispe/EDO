"""Despachador para ED lineales de orden superior (n ≥ 2)."""
from __future__ import annotations

from ..core.lector import ED
from ..core.paso import Resultado
from ..primer_orden.base import NoAplica
from . import euler, lineal_cc, variacion

METODOS = {
    "abreviado": ("Método abreviado (operador D)", lineal_cc.aplica_abreviado, lineal_cc.resolver_abreviado),
    "coeficientes_indeterminados": ("Coeficientes indeterminados", lineal_cc.aplica_coef_indeterminados,
                                    lineal_cc.resolver_coef_indeterminados),
    "variacion_parametros": ("Variación de parámetros", variacion.aplica_variacion, variacion.resolver_variacion),
    "euler": ("Euler / Cauchy-Legendre (ax+b = eᵗ)", euler.aplica_euler, euler.resolver_euler),
}
PREFERENCIA = ["abreviado", "coeficientes_indeterminados", "variacion_parametros", "euler"]


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
        "No aplica con los métodos del temario implementados hasta ahora (método abreviado, coeficientes indeterminados "
        "variación de parámetros para coeficientes constantes, Euler y Cauchy-Legendre).")
    try:
        lineal_cc.leer_lineal(ed)
    except NoAplica as exc:
        res.advertencias.append("Se intentó — coeficientes constantes: " + str(exc))
    return res
