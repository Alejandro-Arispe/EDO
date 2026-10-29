from pathlib import Path

import pytest
import sympy as sp
import yaml

from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, x
from edo.core.verificador import es_cero
from edo.resolutor import resolver

CASOS = yaml.safe_load((Path(__file__).parent / "coeficiente_variable.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    ed = leer_ed(c["ed"])
    conds = leer_condiciones(c["condiciones"]) if c.get("condiciones") else None
    r = resolver(ed, None, conds)
    if c.get("ninguno"):
        assert r.metodo == "ninguno" and not r.pasos
        return
    assert r.metodo.startswith(("Euler", "Cauchy-Legendre"))
    assert r.verificacion is not None and r.verificacion.ok, (r.solucion, r.verificacion)
    if "constantes" in c and not conds:
        assert len(r.constantes) == c["constantes"]
    if "solucion" in c:
        assert es_cero(r.valor - leer_expresion(c["solucion"])).ok, r.valor
    if "yp" in c:
        assert es_cero(r.particular - leer_expresion(c["yp"])).ok, r.particular
    if c.get("discrepancia"):
        assert any(p.discrepancia and f"[{c['discrepancia']}]" in p.discrepancia for p in r.pasos)
    if "raices_t" in c:
        # las raíces de 4D²−10D+2 son (5±√17)/4: los exponentes de (2x+1) en la solución
        exps = {sp.simplify(e) for e in map(lambda s: leer_expresion(s), c["raices_t"].split(","))}
        base = sp.Symbol("u", positive=True)
        for e in exps:
            f = (2 * x + 1) ** e
            ed_t = ed.expr
            res_ = es_cero((ed_t + ed.rhs).subs(sp.Function("y")(x), f).doit())
            assert res_.ok
