import pytest
import sympy as sp

from edo.core.lector import ErrorLectura, Condicion, desde_latex, leer_condiciones, leer_ed, leer_relacion, x, y, ys

Y = y(x)


def dy(n=1):
    return sp.Derivative(Y, (x, n))


@pytest.mark.parametrize("texto,lhs,rhs", [
    ("y'+2y=x e^x", dy() + 2 * Y, x * sp.exp(x)),
    ("dy/dx = 3-2x", dy(), 3 - 2 * x),
    ("d^2y/dx^2 - 3 dy/dx + 2y = sen2x", dy(2) - 3 * dy() + 2 * Y, sp.sin(2 * x)),
    ("y''''+y''=sen 2x", dy(4) + dy(2), sp.sin(2 * x)),
    ("y^(4)-y=0", dy(4) - Y, 0),
    ("xy'+2y=xe^-x", x * dy() + 2 * Y, x * sp.exp(-x)),
    ("y'=tg x sec^2 x", dy(), sp.tan(x) * sp.sec(x) ** 2),
    ("y'=arctg(x)/ln x", dy(), sp.atan(x) / sp.log(x)),
    ("2y''+2y'+y=4 sqrt(x)", 2 * dy(2) + 2 * dy() + Y, 4 * sp.sqrt(x)),
    ("y''-4y'+4y=x e^3x", dy(2) - 4 * dy() + 4 * Y, x * sp.exp(3 * x)),
    ("y' = e^(x/y)", dy(), sp.exp(x / Y)),
])
def test_forma_derivada(texto, lhs, rhs):
    ed = leer_ed(texto)
    assert ed.forma == "derivada"
    assert sp.simplify(ed.lhs - lhs) == 0 and sp.simplify(ed.rhs - rhs) == 0


def test_orden():
    assert leer_ed("y'''-y'=0").orden == 3
    assert leer_ed("y=x^2").orden == 0


def test_forma_diferencial():
    ed = leer_ed("(x+y)dx-(x-y)dy=0")
    assert ed.forma == "diferencial"
    assert sp.expand(ed.M - (x + ys)) == 0 and sp.expand(ed.N + (x - ys)) == 0
    ed = leer_ed("(2xy+3)dy-y^2 dx=0")
    assert sp.expand(ed.M + ys ** 2) == 0 and sp.expand(ed.N - (2 * x * ys + 3)) == 0
    ed = leer_ed("(1+e^(x/y))dx+e^(x/y)(1-x/y)dy=0")
    assert sp.simplify(ed.M - (1 + sp.exp(x / ys))) == 0


def test_notacion_D():
    ed = leer_ed("(D^2-3D+2)y=e^x")
    assert ed.forma == "operador" and ed.orden == 2
    assert sp.simplify(ed.lhs - (dy(2) - 3 * dy() + 2 * Y)) == 0
    assert sp.simplify(ed.rhs - sp.exp(x)) == 0
    ed = leer_ed("(D^2+5)y=cos(sqrt5 x)")
    assert sp.simplify(ed.rhs - sp.cos(sp.sqrt(5) * x)) == 0
    ed = leer_ed("D^3 y - D y = 0")
    assert ed.orden == 3


def test_latex_mathlive():
    ed = leer_ed(r"\frac{d^2y}{dx^2}+3\frac{dy}{dx}=\sqrt{x}\sin\left(2x\right)", latex=True)
    assert sp.simplify(ed.lhs - (dy(2) + 3 * dy())) == 0
    assert sp.simplify(ed.rhs - sp.sqrt(x) * sp.sin(2 * x)) == 0
    ed = leer_ed(r"y^{\prime}+2y=xe^{x}", latex=True)
    assert sp.simplify(ed.rhs - x * sp.exp(x)) == 0
    assert desde_latex(r"\frac{1}{x}") == "((1)/(x))"


def test_condiciones():
    c = leer_condiciones("y(1)=2, y'(0)=-1; y''(pi)=3")
    assert c == [Condicion(0, 1, 2), Condicion(1, 0, -1), Condicion(2, sp.pi, 3)]


def test_relacion():
    izq, der = leer_relacion("x/y^2+1/y^3=C")
    assert sp.simplify(izq - (x / ys ** 2 + 1 / ys ** 3)) == 0


@pytest.mark.parametrize("malo", ["", "y''+=3", "y'=e^", "y=1=2", "y(0)=", "(x+y)dx+y'=0"])
def test_entradas_malas(malo):
    with pytest.raises(ErrorLectura):
        leer_ed(malo)
