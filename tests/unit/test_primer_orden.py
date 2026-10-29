import sympy as sp
from hypothesis import HealthCheck, given, settings, strategies as st

from edo.core.lector import ED, leer_ed, x, y, ys
from edo.primer_orden.base import forma
from edo.primer_orden.resolutor import clasificar_metodos, resolver

_s = settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
_n = st.integers(1, 4)


def _ed_diferencial(M, N) -> ED:
    ed = ED("gen", "diferencial", sp.Integer(0), sp.Integer(0), 1, M=M, N=N)
    ed.lhs = (M + N * sp.Derivative(y(x), x)).subs(ys, y(x))
    return ed


@_s
@given(_n, _n, _n, _n)
def test_propiedad_exacta_desde_potencial(a, b, c, d):
    """f = a x^2 y + b x y^3 + c x + d y -> M = f_x, N = f_y; la solución f = C debe verificarse."""
    f = a * x ** 2 * ys + b * x * ys ** 3 + c * x + d * ys
    r = resolver(_ed_diferencial(sp.diff(f, x), sp.diff(f, ys)), "exacta")
    assert r.verificacion.ok
    assert sp.simplify(sp.diff(r.valor.izq, x) * sp.diff(f, ys) - sp.diff(r.valor.izq, ys) * sp.diff(f, x)) == 0


@_s
@given(_n, _n, _n)
def test_propiedad_lineal(a, b, c):
    ed = leer_ed(f"y' + {a} x y = {b} x + {c}")
    r = resolver(ed, "lineal_y")
    assert r.verificacion.ok and r.valor.explicita


@_s
@given(st.integers(2, 4), _n, _n)
def test_propiedad_bernoulli(n, a, b):
    ed = leer_ed(f"y' + {a} y = {b} x y^{n}")
    r = resolver(ed, "bernoulli_y")
    assert r.verificacion.ok


@_s
@given(_n, _n)
def test_propiedad_separable_con_condicion(a, b):
    ed = leer_ed(f"y' = {a} x (y^2 + {b})")
    r = resolver(ed, "separable")
    assert r.verificacion.ok


def test_clasificador_lista_todos_los_metodos():
    ids = [m["metodo"] for m in clasificar_metodos(leer_ed("y' = y/x"))]
    assert ids[0] == "separable" and "lineal_y" in ids and "homogenea" in ids
    assert clasificar_metodos(leer_ed("y'' + y = 0")) == []


def test_forma_no_expande_el_argumento():
    fm = forma(leer_ed("y' + 1 = (x+y+2)^3"))
    assert fm.f == (x + ys + 2) ** 3 - 1
