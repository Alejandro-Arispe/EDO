import pytest
import sympy as sp
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings, strategies as st

from edo.api.app import app
from edo.calculo.derivadas import derivar
from edo.conceptos.desde_raices import desde_raices, leer_raices, polinomio_caracteristico, _validar
from edo.core.lector import D, ErrorLectura, x

c = TestClient(app)


def test_regresion_derivada_constante_sobre_funcion():
    """1/(2√u) provocaba recursión infinita al tratar c/g(x)."""
    r = derivar(1 / (2 * sp.sqrt(x ** 2 + 1)), x)
    assert r.verificacion.ok


def test_raiz_compleja_sin_conjugada_es_error():
    with pytest.raises(ErrorLectura):
        desde_raices(leer_raices("1+2i"))


def test_formatos_de_raices():
    a = leer_raices("D1=D2=5+2i; D3=D4=5-2i; D5=D6=0")
    b = leer_raices("5+2i (2), 5-2i (2), 0 doble")
    c_ = leer_raices("5+2i, 5+2i, 5-2i, 5-2i, 0, 0")
    assert a == b == c_ == [(5 + 2 * sp.I, 2), (5 - 2 * sp.I, 2), (0, 2)]


def test_B1_forma_de_la_solucion():
    r = desde_raices(leer_raices("D1=D2=5+2i; D3=D4=5-2i; D5=D6=0"))
    C = sp.symbols("C1:7")
    esperada = (sp.exp(5 * x) * ((C[0] + C[1] * x) * sp.cos(2 * x) + (C[2] + C[3] * x) * sp.sin(2 * x))
                + C[4] + C[5] * x)
    assert sp.simplify(r.valor - esperada) == 0


_reales = st.integers(-3, 3)
_par = st.tuples(st.integers(-2, 2), st.integers(1, 3))
_mult = st.integers(1, 3)


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(st.tuples(_reales, _mult), min_size=0, max_size=2, unique_by=lambda t: t[0]),
       st.lists(st.tuples(_par, st.integers(1, 2)), min_size=0, max_size=2, unique_by=lambda t: t[0]))
def test_propiedad_raices_ed_solucion(reales, complejos):
    raices = [(sp.Integer(r), m) for r, m in reales]
    for (a, b), m in complejos:
        raices += [(a + b * sp.I, m), (a - b * sp.I, m)]
    if not raices:
        return
    r = desde_raices(raices)
    assert r.verificacion.ok
    P = polinomio_caracteristico(_validar(raices))
    esperadas = {}
    for rr, m in raices:
        esperadas[rr] = m
    assert sp.roots(sp.Poly(P, D)) == esperadas


def test_api_clasificar_general_y_ordinaria():
    r = c.post("/clasificar", json={"entrada": "z_xx + z_yy = 0"}).json()
    assert r["clasificacion"]["tipo"] == "parcial" and r["clasificacion"]["homogenea"] is True
    r = c.post("/clasificar", json={"entrada": "(x-1)y'' - 4xy = e^x"}).json()
    k = r["clasificacion"]
    assert (k["orden"], k["grado"], k["lineal"], k["homogenea"]) == (2, 1, True, False)
    assert [p["titulo"] for p in r["pasos"]][:3] == ["Ecuación diferencial ordinaria", "Orden", "Grado"]


def test_api_verificar_con_pasos_y_discrepancia():
    r = c.post("/verificar", json={"ed": "xy' + x ln y = x sen x + y ln y",
                                   "respuesta": "x*Integral(sin(t)/t,(t,0,x)) = y ln y"}).json()
    assert r["verificacion"]["ok"] is False
    assert any(p["discrepancia"] and "A3" in p["discrepancia"] for p in r["pasos"])
    assert r["pasos"][-1]["titulo"] == "Relación que sí cumple la función"


def test_api_constantes_A1():
    r = c.post("/conceptos/constantes", json={"ed": "y'=3-2x", "respuesta": "y=3x-x^2+C", "condiciones": "y(1)=2"}).json()
    assert r["solucion"] == "y = - x^{2} + 3 x" and r["verificacion"]["ok"]
    assert any(p["discrepancia"] and "A1" in p["discrepancia"] for p in r["pasos"])
    mal = c.post("/conceptos/constantes", json={"respuesta": "y=C", "condiciones": "y(1"})
    assert mal.status_code == 422


def test_api_dependencia_y_raices_y_tipo():
    r = c.post("/conceptos/dependencia", json={"entrada": "x; 2x; x^2"}).json()
    assert r["solucion"] == "linealmente dependientes"
    r = c.post("/conceptos/raices", json={"entrada": "2i, -2i"}).json()
    assert r["verificacion"]["ok"] and "y_h" in r["pasos"][-2]["titulo"]
    r = c.post("/conceptos/tipo_solucion", json={"ed": "y'=2y", "respuesta": "y=C e^(2x)"}).json()
    assert "general" in r["pasos"][-1]["explicacion"]
