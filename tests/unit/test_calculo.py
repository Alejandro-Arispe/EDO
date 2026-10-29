import pytest
import sympy as sp
from hypothesis import HealthCheck, given, settings, strategies as st

from edo.calculo.derivadas import derivar
from edo.calculo.integrales import integrar
from edo.calculo.resultado import ErrorCalculo
from edo.core.lector import leer_expresion, x, y
from edo.core.verificador import es_cero

t = sp.Symbol("t")


@pytest.mark.parametrize("texto", [
    "x^2 sen x", "sen(x)/x", "e^(x^2) cos 3x", "x^x", "sqrt(1+x^2)", "ln(tg x)", "3x^4-2/x",
    "x e^x sen x", "arctg(2x)", "(x^2+1)/(x-1)", "x^3 ln x", "sec(x)^2", "e^-x", "1/x^3", "2^x",
    "arcsen(x/2)", "x sen x cos x", "(2x+1)^5", "ctg x", "x^(1/3)",
])
def test_derivadas_coinciden_con_sympy(texto):
    e = leer_expresion(texto)
    r = derivar(e, x)
    assert es_cero(r.valor - sp.diff(e, x)).ok
    assert r.verificacion.ok and r.pasos and r.pasos[-1].titulo.startswith("Resultado")


def test_pasos_de_producto_y_cadena():
    r = derivar(leer_expresion("e^(x^2) cos 3x"), x)
    reglas = " ".join(p.titulo for p in r.pasos)
    assert "producto" in reglas and "cadena" in reglas


def test_derivada_orden_2():
    r = derivar(leer_expresion("x^4"), x, orden=2)
    assert sp.simplify(r.valor - 12 * x ** 2) == 0


def test_derivada_implicita_A3():
    """d/dx[y ln y] = y'(1 + ln y): el texto perdió y' en ln y."""
    r = derivar(y(x) * sp.log(y(x)), x)
    esperado = sp.Derivative(y(x), x) * (1 + sp.log(y(x)))
    assert sp.simplify(r.valor - esperado) == 0
    assert any("incógnita" in p.titulo for p in r.pasos)


def test_teorema_fundamental_A3():
    I = sp.Integral(sp.sin(t) / t, (t, 0, x))
    r = derivar(x * I, x)
    assert sp.simplify(r.valor - (I + sp.sin(x))) == 0
    assert any("fundamental" in p.titulo for p in r.pasos)


def test_derivada_sin_regla():
    with pytest.raises(ErrorCalculo):
        derivar(sp.besselj(0, x), x)


@pytest.mark.parametrize("texto", [
    "x e^x", "x^3", "sen^2 x", "1/(x^2+1)", "e^x sen x", "sqrt(1-x^2)", "1/(x^2-1)", "ln x", "tg x",
    "e^(2x)", "1/(x^2+2x+5)", "x^2 cos 3x", "(2x+1)^5", "sec x", "x/(x^2+1)", "1/sqrt(4-x^2)",
    "x^2 e^x", "cos x/sen x", "1/x", "x ln x",
])
def test_integrales_verifican_por_derivacion(texto):
    e = leer_expresion(texto)
    r = integrar(e, x)
    assert r.elemental and r.valor is not None
    assert es_cero(sp.diff(r.valor, x) - e).ok
    assert r.verificacion.ok
    assert r.resultado_latex.endswith("+ C")


@pytest.mark.parametrize("texto", ["e^(x^2)", "sen x/x", "e^x/x", "1/ln x"])
def test_integrales_no_elementales_quedan_indicadas(texto):
    r = integrar(leer_expresion(texto), x)
    assert not r.elemental and r.valor is None
    assert r.advertencias and "indicada" in r.advertencias[0]
    assert r.pasos[0].titulo == "Integral no elemental"


# ---- propiedad: derivar cualquier expresión armada con la gramática coincide con sympy
_hojas = st.sampled_from([x, sp.Integer(2), sp.Integer(3), sp.Rational(1, 2), x ** 2, x ** 3])
_unarias = [sp.sin, sp.cos, sp.exp, sp.atan, lambda u: sp.log(u ** 2 + 1), lambda u: sp.sqrt(u ** 2 + 1)]


def _expr(profundidad):
    if profundidad == 0:
        return _hojas
    sub = _expr(profundidad - 1)
    return st.one_of(
        sub,
        st.tuples(sub, sub).map(lambda p: p[0] + p[1]),
        st.tuples(sub, sub).map(lambda p: p[0] * p[1]),
        st.tuples(sub, sub).map(lambda p: p[0] / (p[1] ** 2 + 1)),
        st.tuples(st.sampled_from(_unarias), sub).map(lambda p: p[0](p[1])),
    )


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(_expr(2))
def test_propiedad_derivada(e):
    r = derivar(e, x)
    assert es_cero(r.valor - sp.diff(e, x)).ok


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(1, 4), st.integers(1, 3), st.sampled_from([sp.sin, sp.cos, sp.exp]))
def test_propiedad_integral_poli_por_funcion(n, a, f):
    e = x ** n * f(a * x)
    r = integrar(e, x)
    assert r.elemental and es_cero(sp.diff(r.valor, x) - e).ok
