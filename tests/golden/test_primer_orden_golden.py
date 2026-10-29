from pathlib import Path

import pytest
import sympy as sp
import yaml

from edo.conceptos.constantes import constantes_de
from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, leer_relacion, x, ys
from edo.core.verificador import es_cero
from edo.primer_orden.base import Solucion, misma_curva
from edo.primer_orden.resolutor import resolver

CASOS = yaml.safe_load((Path(__file__).parent / "primer_orden.yaml").read_text(encoding="utf-8"))


def _sol(texto) -> Solucion:
    izq, der = leer_relacion(texto)
    return Solucion(izq, der)


def _G(sol: Solucion):
    """G(x, y) tal que G = constante describe la familia (o la curva)."""
    if sol.explicita:
        cs = constantes_de(sol.der)
        if cs:
            raiz = sp.solve(sp.Eq(ys, sol.der), cs[0])
            return raiz[0] if len(raiz) == 1 else None
        return ys - sol.der
    return sol.izq - sol.der


def _cero_local(expr, x0=0.0) -> bool:
    """Una solución particular explícita solo vale cerca de x0 (rama de arctg, etc.)."""
    f = sp.lambdify(x, expr, "mpmath")
    return all(abs(complex(f(x0 + d))) < 1e-9 for d in (-0.2, -0.1, 0.05, 0.1, 0.2))


def _equivalentes(ours: Solucion, esperada: Solucion, particular: bool, x0=0.0) -> bool:
    if ours.explicita and esperada.explicita and es_cero(ours.der - esperada.der).ok:
        return True
    if particular and ours.explicita:   # la relación esperada debe anularse sobre nuestra curva
        e = (esperada.izq - esperada.der).subs(ys, ours.der)
        return es_cero(e).ok or _cero_local(e, x0)
    if particular and esperada.explicita:
        e = (ours.izq - ours.der).subs(ys, esperada.der)
        return es_cero(e).ok or _cero_local(e, x0)
    Go, Ge = _G(ours), _G(esperada)
    if Go is None or Ge is None:
        return False
    return misma_curva(Go, Ge)


def _hay_nota(res, clave):
    return any(s.discrepancia and f"[{clave}]" in s.discrepancia for s in res.pasos)


@pytest.mark.parametrize("c", CASOS, ids=[c["id"] for c in CASOS])
def test_caso(c):
    ed = leer_ed(c["ed"])
    conds = leer_condiciones(c["condiciones"]) if c.get("condiciones") else None
    if c.get("ninguno"):
        r = resolver(ed)
        assert r.metodo == "ninguno" and r.advertencias[0].startswith("No aplica con los métodos del temario")
        assert not r.pasos and r.valor is None
        return
    r = resolver(ed, c.get("metodo"), conds)
    assert r.verificacion is not None and r.verificacion.ok, (r.solucion, r.verificacion, r.advertencias)
    if c.get("discrepancia"):
        assert _hay_nota(r, c["discrepancia"])
    if "solucion" in c:
        esp = _sol(c["solucion"])
        assert _equivalentes(r.valor, esp, bool(conds), float(conds[0].x0) if conds else 0.0), f"{r.solucion} no equivale a {c['solucion']}"
        if conds:
            for cd in conds:
                v = esp.der.subs(x, cd.x0) if esp.explicita else None
                if v is not None:
                    assert es_cero(v - cd.valor).ok
    if "parametrica" in c:
        xe, ye = (leer_expresion(c["parametrica"][k]) for k in "xy")
        xo, yo = r.valor.param
        assert es_cero(xo - xe).ok and es_cero(yo - ye).ok, (xo, yo)
    if "singular" in c:
        sing = c["singular"]
        objs = r.extra
        assert objs, "falta la solución singular"
        if "x" in sing:
            xe, ye = leer_expresion(sing["x"]), leer_expresion(sing["y"])
            assert any(o.param and es_cero(o.param[0] - xe).ok and es_cero(o.param[1] - ye).ok for o in objs)
        else:
            ye = leer_expresion(sing["y"])
            assert any(o.explicita and es_cero(o.der - ye).ok for o in objs)
    if "perdida" in c:
        ye = leer_relacion(c["perdida"])[1]
        assert any(o.explicita and es_cero(o.der - ye).ok for o in r.extra)
    if "factores" in c:
        esperadas = [leer_relacion(f)[1] for f in c["factores"]]
        obtenidas = [s.der for s in r.valor if s.explicita]
        for e in esperadas:
            assert any(es_cero(o - e).ok for o in obtenidas), (e, obtenidas)
