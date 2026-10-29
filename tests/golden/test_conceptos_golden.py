from pathlib import Path

import pytest
import sympy as sp
import yaml

from edo.conceptos.clasificacion import clasificar
from edo.conceptos.constantes import clasificar_solucion, determinar_constantes
from edo.conceptos.desde_raices import desde_raices, leer_raices
from edo.conceptos.verificacion import verificar_solucion
from edo.conceptos.wronskiano import analizar_dependencia
from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, leer_relacion, x, ys
from edo.core.lector_general import leer_general
from edo.core.verificador import es_cero

CASOS = yaml.safe_load((Path(__file__).parent / "conceptos.yaml").read_text(encoding="utf-8"))


def _leer(texto):
    ed = leer_ed(texto)
    return ed if ed.orden > 0 else leer_general(texto)


def _iguales(a, b) -> bool:
    return es_cero(sp.sympify(a) - sp.sympify(b)).ok


def _hay_nota(res, clave: str) -> bool:
    return any(p.discrepancia and f"[{clave}]" in p.discrepancia for p in res.pasos)


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    t = c["tipo"]
    if t == "clasificar":
        r = clasificar(_leer(c["ed"]))
        for k, v in c["esperado"].items():
            assert getattr(r, k) == v, f"{k}: {getattr(r, k)} != {v}"
    elif t == "verificar":
        ed = leer_ed(c["ed"])
        izq, der = leer_relacion(c["respuesta"])
        r = verificar_solucion(ed, izq, der)
        assert r.verificacion.ok == c["ok"]
        assert r.pasos[0].titulo.startswith("Primer paso")
        assert any(p.titulo.startswith("Cuarto paso") for p in r.pasos)
        if c.get("discrepancia"):
            assert _hay_nota(r, c["discrepancia"])
        if c.get("relacion"):
            extra = r.pasos[-1]
            assert extra.titulo == "Relación que sí cumple la función"
            esperado = leer_ed(c["relacion"]).expr
            # misma relación salvo el signo/forma: se compara con la derivada despejada
            from edo.conceptos.verificacion import _relacion_derivada
            G = leer_relacion(c["respuesta"])
            r_l, r_r = _relacion_derivada(G[0] - G[1])
            yp = sp.Symbol("y'")
            esp = esperado.subs(sp.Derivative(sp.Function("y")(x), x), yp).subs(sp.Function("y")(x), ys)
            assert sp.simplify((r_l - r_r) - esp) == 0
        if c.get("nota_trivial"):
            assert "trivial" in r.pasos[-1].explicacion
    elif t == "constantes":
        ed = leer_ed(c["ed"]) if c.get("ed") else None
        izq, der = leer_relacion(c["general"])
        r = determinar_constantes(ed, izq, der, leer_condiciones(c["condiciones"]))
        assert r.verificacion.ok
        if "solucion" in c:
            esperada = leer_expresion(c["solucion"])
            assert _iguales(r.valor, esperada)
        if "solucion_implicita" in c:
            assert sp.simplify(r.valor - leer_expresion(c["solucion_implicita"])) == 0
        if c.get("discrepancia"):
            assert _hay_nota(r, c["discrepancia"])
    elif t == "dependencia":
        funcs = [leer_expresion(s) for s in c["funciones"].split(";")]
        r = analizar_dependencia(funcs)
        if c["resultado"] == "dependientes_o_no":
            return
        assert r.solucion == "linealmente " + c["resultado"]
    elif t == "raices":
        r = desde_raices(leer_raices(c["raices"]))
        assert r.verificacion.ok and len(r.constantes) == c["orden"]
        if c.get("discrepancia"):
            assert _hay_nota(r, c["discrepancia"])
    elif t == "tipo_solucion":
        ed = leer_ed(c["ed"])
        izq, der = leer_relacion(c["respuesta"])
        gen = leer_relacion(c["general"]) if c.get("general") else None
        r = clasificar_solucion(ed, izq, der, gen)
        assert f"solución {c['esperado']}" in r.pasos[-1].explicacion
    else:  # pragma: no cover
        raise AssertionError(f"tipo desconocido {t}")
