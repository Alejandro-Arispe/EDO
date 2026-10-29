from pathlib import Path

import pytest
import yaml

from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, x
from edo.core.verificador import es_cero, verificar_explicita
from edo.resolutor import resolver

CASOS = yaml.safe_load((Path(__file__).parent / "orden_superior_cc.yaml").read_text(encoding="utf-8"))


def _nota(res, clave):
    return any(p.discrepancia and f"[{clave}]" in p.discrepancia for p in res.pasos)


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    ed = leer_ed(c["ed"])
    conds = leer_condiciones(c["condiciones"]) if c.get("condiciones") else None
    if c.get("ninguno"):
        r = resolver(ed)
        assert r.metodo == "ninguno" and not r.pasos and r.advertencias[0].startswith("No aplica con los métodos del temario")
        return
    metodos = ["abreviado", "coeficientes_indeterminados"] if c.get("ambos") else [None]
    for m in metodos:
        r = resolver(ed, m, conds)
        assert r.verificacion is not None and r.verificacion.ok, (m, r.solucion, r.verificacion)
        if "constantes" in c and not conds:
            assert len(r.constantes) == c["constantes"]
        if "yp" in c:
            assert es_cero(r.particular - leer_expresion(c["yp"])).ok, (m, r.particular)
        if "solucion" in c:
            assert es_cero(r.valor - leer_expresion(c["solucion"])).ok, r.valor
        if c.get("discrepancia"):
            assert _nota(r, c["discrepancia"])
        if c.get("numerica"):
            assert any("transcripción" in a for a in r.advertencias)
