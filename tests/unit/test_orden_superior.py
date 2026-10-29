import sympy as sp
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings, strategies as st

from edo.api.app import app
from edo.conceptos.desde_raices import desde_raices
from edo.core.lector import D, ED, leer_ed, x, y
from edo.core.verificador import es_cero
from edo.orden_superior.lineal_cc import _grupos, leer_lineal, raices_caracteristicas
from edo.resolutor import clasificar_metodos, resolver

c = TestClient(app)
_s = settings(max_examples=12, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _ed_desde_poli(P: sp.Expr, Q: sp.Expr) -> ED:
    pol = sp.Poly(P, D)
    lhs = sum(co * (y(x) if k == 0 else sp.Derivative(y(x), (x, k))) for (k,), co in pol.terms())
    return ED("gen", "operador", lhs, Q, pol.degree(), operador=P)


_raiz = st.integers(-2, 2)
_forzante = st.sampled_from([
    sp.Integer(1), x, x ** 2, sp.exp(x), sp.exp(-x), x * sp.exp(2 * x), sp.sin(x), sp.cos(2 * x),
    sp.exp(x) * sp.sin(x), x * sp.cos(x), sp.exp(2 * x) + x, sp.sin(x) + sp.exp(-x),
])


@_s
@given(st.lists(_raiz, min_size=2, max_size=3), _forzante)
def test_propiedad_dos_metodos_coinciden(raices, Q):
    """Se eligen raíces, se arma la ED, se resuelve por los dos métodos y se comparan las y_p."""
    P = sp.expand(sp.Mul(*[(D - r) for r in raices]))
    ed = _ed_desde_poli(P, Q)
    a = resolver(ed, "abreviado")
    b = resolver(ed, "coeficientes_indeterminados")
    assert a.verificacion.ok and b.verificacion.ok
    assert es_cero(a.particular - b.particular).ok
    # las raíces recuperadas son las elegidas
    rec, exactas = raices_caracteristicas(P)
    assert exactas and sorted((r, m) for r, m in rec) == sorted((sp.Integer(r), raices.count(r)) for r in set(raices))


@_s
@given(st.lists(st.tuples(st.integers(-2, 2), st.integers(1, 3)), min_size=1, max_size=2, unique_by=lambda t: t[0]),
       st.lists(st.integers(1, 3), min_size=0, max_size=1))
def test_propiedad_raices_a_solucion(reales, betas):
    raices = [(sp.Integer(a), 1) for a, _ in reales]
    for b in betas:
        raices += [(sp.I * b, 1), (-sp.I * b, 1)]
    r = desde_raices(raices)
    assert r.verificacion.ok
    ed = _ed_desde_poli(sp.expand(sp.Mul(*[(D - rr) for rr, _ in raices])), sp.Integer(0))
    res = resolver(ed)
    assert res.verificacion.ok and len(res.constantes) == ed.orden


def test_forma_de_q_no_soportada():
    assert clasificar_metodos(leer_ed("2y'' + 2y' + y = 4 sqrt(x)")) == []
    assert clasificar_metodos(leer_ed("y'' + y = tg(x)")) == []
    assert clasificar_metodos(leer_ed("x y'' + y = 0")) == []
    ids = [m["metodo"] for m in clasificar_metodos(leer_ed("y'' + y = x"))]
    assert ids == ["abreviado", "coeficientes_indeterminados"]


def test_grupos_de_q():
    g = _grupos(sp.expand((x ** 2 + 1) * sp.exp(2 * x) + 3 * sp.sin(2 * x + 1) + 5))
    assert len(g) == 3


def test_lector_acepta_notacion_D_en_resolver():
    r = resolver(leer_ed("(D^2 - 3D + 2)y = e^x"))
    assert r.verificacion.ok and r.metodo.startswith("método abreviado")


def test_api_orden_superior():
    r = c.post("/resolver", json={"entrada": "y''-4y'+4y = x e^(3x)"}).json()
    assert r["verificacion"]["ok"] and "x - 2" in r["pasos"][-2]["despues_latex"]
    assert any(p["discrepancia"] and "A11a" in p["discrepancia"] for p in r["pasos"])
    r = c.post("/clasificar", json={"entrada": "y'' + 4y = 3x^3"}).json()
    assert [m["metodo"] for m in r["metodos"]] == ["abreviado", "coeficientes_indeterminados"]
    r = c.post("/resolver", json={"entrada": "2y''+2y'+y=4 sqrt(x)"}).json()
    assert r["metodo"] == "ninguno" and not r["pasos"]
