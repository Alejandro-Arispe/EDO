import sympy as sp

from edo.core.latex import latex
from edo.core.lector import leer_ed, x, ys
from edo.core.verificador import es_cero, verificar_explicita, verificar_implicita


def test_latex_espanol():
    assert r"\operatorname{sen}" in latex(sp.sin(2 * x))
    assert r"\operatorname{tg}" in latex(sp.tan(x))
    assert r"\operatorname{arctg}" in latex(sp.atan(x))
    assert latex(leer_ed("y''-3y'+2y=0").lhs) == "y'' - 3 y' + 2 y"


def test_es_cero():
    assert es_cero(sp.sin(x) ** 2 + sp.cos(x) ** 2 - 1).ok
    assert not es_cero(x - 1).ok
    v = es_cero(sp.Symbol("a") * 0 + x * sp.exp(x) - x * sp.exp(x))
    assert v.ok and v.como == "simbólica"


def test_explicita():
    ed = leer_ed("y''-2y'+2y=0")
    assert verificar_explicita(ed, sp.exp(x) * sp.sin(x)).ok
    assert verificar_explicita(ed, sp.Symbol("C1") * sp.exp(x) * sp.cos(x)).ok
    assert not verificar_explicita(ed, sp.exp(x)).ok


def test_implicita_A4_A5():
    C = sp.Symbol("C")
    ed4 = leer_ed("(2xy+3)dy-y^2 dx=0")
    assert verificar_implicita(ed4, x / ys ** 2 + 1 / ys ** 3, C).ok
    assert not verificar_implicita(ed4, x / ys ** 2 + 3 / (4 * ys ** 4), C).ok  # lectura errónea del texto
    ed5 = leer_ed("(1+e^(x/y))dx+e^(x/y)(1-x/y)dy=0")
    assert verificar_implicita(ed5, x + ys * sp.exp(x / ys), C).ok


def test_implicita_A3():
    t = sp.Symbol("t")
    I = sp.Integral(sp.sin(t) / t, (t, 0, x))
    texto = leer_ed("xy'+x ln y = x sen x + y ln y")
    corregida = leer_ed("x y'(1+ln y) = x sen x + y ln y")
    assert not verificar_implicita(texto, x * I, ys * sp.log(ys)).ok
    assert verificar_implicita(corregida, x * I, ys * sp.log(ys)).ok
