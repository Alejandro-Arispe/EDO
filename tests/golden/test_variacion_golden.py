from pathlib import Path

import pytest
import sympy as sp
import yaml

from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, x
from edo.core.verificador import es_cero
from edo.orden_superior.lineal_cc import leer_lineal
from edo.resolutor import resolver

CASOS = yaml.safe_load((Path(__file__).parent / "variacion_parametros.yaml").read_text(encoding="utf-8"))


def _aplica_homogenea(L_, f):
    """F(D) f con la F de la ED (sin término independiente)."""
    pol = sp.Poly(L_.P, sp.Symbol("D"))
    return sum(c * sp.diff(f, x, k) for (k,), c in pol.terms())


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    ed = leer_ed(c["ed"])
    conds = leer_condiciones(c["condiciones"]) if c.get("condiciones") else None
    r = resolver(ed, "variacion_parametros", conds)
    assert r.verificacion is not None and r.verificacion.ok, (r.solucion, r.verificacion)
    titulos = [p.titulo for p in r.pasos]
    assert any(t.startswith("Tercer paso") for t in titulos) and any(t.startswith("Cuarto paso") for t in titulos)
    if "yp" in c:
        dif = r.particular - leer_expresion(c["yp"])
        assert es_cero(_aplica_homogenea(leer_lineal(ed), dif)).ok, dif
    if "solucion" in c:
        assert es_cero(r.valor - leer_expresion(c["solucion"])).ok
    if c.get("elemental") is False:
        assert any("no es elemental" in a for a in r.advertencias)
