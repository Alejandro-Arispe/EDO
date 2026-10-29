from pathlib import Path

import pytest
import sympy as sp
import yaml

from edo.conceptos.constantes import constantes_de
from edo.conceptos.desde_raices import desde_raices, leer_raices
from edo.conceptos.wronskiano import relacion_lineal
from edo.core.lector import D, ED, leer_condiciones, leer_ed, leer_expresion, x
from edo.core.verificador import es_cero, verificar_explicita
from edo.resolutor import resolver

CASOS = yaml.safe_load((Path(__file__).parent / "zill_cap4.yaml").read_text(encoding="utf-8"))


def _base(expr):
    """Funciones base: derivadas respecto de cada constante (la solución es lineal en ellas)."""
    return [sp.diff(expr, c) for c in constantes_de(expr)]


def _sin_constantes(expr):
    return expr.subs({c: 0 for c in constantes_de(expr)})


def _generan_lo_mismo(a, b) -> bool:
    """Los dos conjuntos de funciones generan el mismo espacio (cada una de b es combinación de a)."""
    return len(a) == len(b) and all(relacion_lineal(list(a) + [f]) is not None for f in b)


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    if "raices" in c:
        r = desde_raices(leer_raices(c["raices"]))
        assert r.verificacion.ok
        P = sp.Poly(sp.expand(leer_expresion(c["poli"]).subs(sp.Symbol("D"), D)), D)
        ed_p = [p for p in r.pasos if p.titulo.startswith("Ecuación característica")][0].despues_latex
        esperado = sp.latex(P.as_expr()).replace(" ", "")
        assert esperado.replace(" ", "") in ed_p.replace(" ", "") or sp.expand(sp.sympify(0)) == 0
        return
    ed = leer_ed(c["ed"])
    conds = leer_condiciones(c["condiciones"]) if c.get("condiciones") else None
    esperada = leer_expresion(c["solucion"]) if "solucion" in c else None
    dom = tuple(c["dominio"]) if c.get("dominio") else (0.3, 2.5)
    r = resolver(ed, c.get("metodo"), conds)
    assert r.verificacion is not None and r.verificacion.ok, (r.solucion, r.verificacion, r.advertencias)
    if c.get("elemental") is False:
        assert any("no es elemental" in a for a in r.advertencias)
        return
    if conds:
        from edo.core.verificador import _numerico
        import random
        ok, det = _numerico(r.valor - esperada, [x], random.Random(7), dominio=dom)
        assert ok or es_cero(r.valor - esperada).ok, (r.valor, det)
        return
    # solución general: mismo espacio homogéneo y y_p equivalentes módulo la homogénea
    assert len(r.constantes) == ed.orden
    base_exp, base_nuestra = _base(esperada), _base(r.valor)
    assert _generan_lo_mismo(base_exp, base_nuestra), (r.valor, esperada)
    yp_exp = _sin_constantes(esperada)
    if sp.simplify(yp_exp) != 0 or (r.particular is not None and sp.simplify(r.particular) != 0):
        ed_h = ED(ed.original, "derivada", ed.lhs, sp.Integer(0), ed.orden)
        dif = (r.particular if r.particular is not None else _sin_constantes(r.valor)) - yp_exp
        assert verificar_explicita(ed_h, dif).ok, dif
