"""Modelos de examen «parciales 1-2025» (docs/fuentes/parciales_1_2025.pdf), M.Sc. Ing. Eudal Avendaño.

Cada solución se contrasta con una integración numérica independiente (Runge-Kutta) del problema de valores
iniciales, sin usar los solvers del programa.
"""
import math

import pytest
import sympy as sp

from edo.conceptos.constantes import constantes_de
from edo.conceptos.desde_raices import desde_raices, leer_raices
from edo.conceptos.verificacion import verificar_solucion
from edo.core.lector import leer_condiciones, leer_ed, leer_expresion, leer_relacion, x, y, ys
from edo.core.verificador import es_cero, verificar_explicita
from edo.problemas import resolver_plantilla
from edo.resolutor import resolver
from edo.tramos import resolver_por_tramos


def rk4(f, x0, v0, xf, pasos=4000):
    """Integra v' = f(x, v) (lista) de x0 a xf."""
    h = (xf - x0) / pasos
    t, v = x0, list(v0)
    for _ in range(pasos):
        k1 = f(t, v)
        k2 = f(t + h / 2, [a + h / 2 * b for a, b in zip(v, k1)])
        k3 = f(t + h / 2, [a + h / 2 * b for a, b in zip(v, k2)])
        k4 = f(t + h, [a + h * b for a, b in zip(v, k3)])
        v = [a + h / 6 * (b1 + 2 * b2 + 2 * b3 + b4) for a, b1, b2, b3, b4 in zip(v, k1, k2, k3, k4)]
        t += h
    return v


def referencia(ed, x0, ini, xf):
    """y(xf) del PVI de la ED (resuelta para la derivada mayor)."""
    n = ed.orden
    top = sp.Derivative(y(x), (x, n))
    simb = sp.symbols(f"u0:{n}")
    G = ed.expr.subs(top, sp.Symbol("T"))
    for k in range(n - 1, 0, -1):
        G = G.subs(sp.Derivative(y(x), (x, k)), simb[k])
    G = G.subs(y(x), simb[0])
    f = sp.lambdify([x, *simb], sp.solve(G, sp.Symbol("T"))[0], "math")
    return rk4(lambda t, v: [*v[1:], f(t, *v)], x0, ini, xf)[0]


def comparar(ed, general, x0, ini, xf):
    """Impone las condiciones iniciales a la solución general y la compara con Runge-Kutta."""
    cs = constantes_de(general)
    ecs = [sp.diff(general, x, k).subs(x, x0) - ini[k] for k in range(len(ini))]
    sol = sp.solve(ecs, cs, dict=True)[0] if cs else {}
    val = float(sp.N(general.subs(sol).subs(x, xf)))
    assert abs(val - referencia(ed, x0, ini, xf)) < 1e-6 * max(1, abs(val))


# ----------------------------------------------------------------- I Evaluación
def test_I_2_demostrar_que_es_solucion():
    ed = leer_ed("2x sen(y)^2 dx - (x^2+10) cos(y) dy = 0")
    izq, der = leer_relacion("ln(x^2+10) + csc(y) = 10")
    r = verificar_solucion(ed, izq, der)
    assert r.verificacion.ok and r.pasos[0].titulo.startswith("Primer paso")
    mal = verificar_solucion(ed, *leer_relacion("ln(x^2+10) + sec(y) = 10"))
    assert not mal.verificacion.ok


def test_I_3_lineal_con_P_por_tramos():
    r = resolver_por_tramos([{"ed": "y' - (2/x) y = 4x", "desde": "0", "hasta": "2"},
                             {"ed": "y' + 2y = 4x", "desde": "2", "hasta": "oo"}], "y(1)=4")
    assert r.verificacion.ok
    f1, f2 = (c[0] for c in r.valor.args)
    assert es_cero(f1 - 4 * x ** 2 * (sp.log(x) + 1)).ok
    assert es_cero(f2 - (2 * x - 1 + (13 + 16 * sp.log(2)) * sp.exp(4 - 2 * x))).ok
    assert sp.simplify(f1.subs(x, 2) - f2.subs(x, 2)) == 0          # continuidad en x = 2

    def tramo1(t, v):                                                # P(x) = −2/x en (0, 2]
        return [4 * t + 2 / t * v[0]]

    def tramo2(t, v):                                                # P(x) = 2 en (2, ∞)
        return [4 * t - 2 * v[0]]
    en_2 = rk4(tramo1, 1.0, [4.0], 2.0)                              # se integra tramo por tramo (la ED salta en x = 2)
    for xf in (1.5, 3.0):
        esperado = rk4(tramo1, 1.0, [4.0], xf)[0] if xf <= 2 else rk4(tramo2, 2.0, en_2, xf)[0]
        valor = float(sp.N(r.valor.subs(x, xf)))
        assert abs(valor - esperado) < 1e-7 * abs(valor)


def test_I_4_hallar_N_para_que_sea_exacta():
    ed = leer_ed("(x^(-1/2) y^(1/2) + x/(x^2+y)) dx + (?) dy = 0")
    r = resolver(ed)
    assert r.metodo.startswith("exacta") and r.verificacion.ok
    M = leer_expresion("x^(-1/2) y^(1/2) + x/(x^2+y)")
    N = leer_expresion("x^(1/2) y^(-1/2) + 1/(2 (x^2+y))")      # una N posible (con h(y) = 0)
    assert es_cero(sp.diff(M, ys) - sp.diff(N, x)).ok           # con esa N la ecuación es exacta
    f = r.valor.izq
    assert es_cero(sp.diff(f, x) - M).ok and es_cero(sp.diff(f, ys) - N).ok


# ---------------------------------------------------------------- II Evaluación A
def test_II_1_clairaut_general_constante_y_singular():
    ed = leer_ed("y' = y sqrt(1+y'^2)/(x sqrt(1+y'^2)+1)")
    r = resolver(ed)
    assert r.metodo == "Clairaut" and r.verificacion.ok
    assert es_cero(r.valor.der - (sp.Symbol("C") * x + sp.Symbol("C") / sp.sqrt(1 + sp.Symbol("C") ** 2))).ok
    sing = [o for o in r.extra if o.explicita]
    assert len(sing) == 2
    for o in sing:                                               # astroide x^(2/3) + y^(2/3) = 1, para −1 < x < 0
        xv = -0.4
        yv = float(sp.N(o.der.subs(x, xv)))
        assert abs(abs(xv) ** (2 / 3) + abs(yv) ** (2 / 3) - 1) < 1e-9
        assert verificar_explicita(ed, o.der).ok
    assert any(a["tipo"] == "singular" for a in r.adicionales)


def test_II_2_lagrange_parametrica_y_sin_singular():
    ed = leer_ed("x = (y + 2 y'^2)/(y'+3)")
    r = resolver(ed)
    assert r.metodo == "Lagrange" and r.verificacion.ok
    xp, yp = r.valor.param
    assert es_cero(xp - (sp.Symbol("C") * sp.exp(-sp.Symbol("p") / 3) + 4 * sp.Symbol("p") - 12)).ok
    assert not any(a["tipo"] == "singular" for a in r.adicionales)      # la curva del discriminante no cumple la ED
    assert any("no hay solución singular" in p.explicacion for p in r.pasos)


def test_II_3_ED_desde_las_raices():
    r = desde_raices(leer_raices("D1=D2=5+2i; D3=D4=5-2i; D5=D6=0"))
    assert r.verificacion.ok and len(r.constantes) == 6
    assert "y^{(6)} - 20 y^{(5)} + 158 y^{(4)} - 580 y''' + 841 y'' = 0" in [p.despues_latex for p in r.pasos][3]


def test_II_4_PVI():
    ed = leer_ed("y'' + 4y' + 5y = 10 e^(-3x)")
    r = resolver(ed, None, leer_condiciones("y(0)=1, y'(0)=1"))
    assert r.verificacion.ok
    for xf in (0.5, 1.0):
        assert abs(float(sp.N(r.valor.subs(x, xf))) - referencia(ed, 0.0, [1.0, 1.0], xf)) < 1e-7


# ------------------------------------------------------------- Evaluación final
def test_final_1_variacion_con_raiz_cuadrada():
    """El enunciado impreso dice 4y'' − 4y + y; se resuelve como 4y'' − 4y' + y (raíz doble 1/2)."""
    ed = leer_ed("4y'' - 4y' + y = e^(x/2) sqrt(1-x^2)")
    r = resolver(ed)
    assert r.metodo == "variación de parámetros" and r.verificacion.ok and len(r.constantes) == 2
    comparar(ed, r.valor, 0.0, [1.0, 0.5], 0.5)
    literal = resolver(leer_ed("4y'' - 4y + y = e^(x/2) sqrt(1-x^2)"))     # lectura literal: integrales no elementales
    assert literal.verificacion.ok and any("no es elemental" in a for a in literal.advertencias)


def test_final_2_abreviado():
    ed = leer_ed("y'' + 3y' - 10y = x e^(-2x)")
    r = resolver(ed)
    assert r.verificacion.ok and es_cero(r.particular - (1 - 12 * x) * sp.exp(-2 * x) / 144).ok
    comparar(ed, r.valor, 0.0, [1.0, -1.0], 0.5)


def test_final_3_euler():
    ed = leer_ed("x^2 y'' - 2 ln(x) = 2x y' - 2y + ln(x)^2")
    r = resolver(ed)
    assert r.metodo.startswith("Euler") and r.verificacion.ok
    L = sp.log(x)
    assert es_cero(r.particular - (L ** 2 / 2 + 5 * L / 2 + sp.Rational(13, 4))).ok
    comparar(ed, r.valor, 1.0, [1.0, 0.0], 1.5)


def test_final_4_circuito_RL():
    r = resolver_plantilla("circuito_rl", {"L": "1/2", "R": "10", "E": "12", "i0": "0", "t2": "0.1"})
    assert es_cero(r.valor - sp.Rational(6, 5) * (1 - sp.exp(-20 * x))).ok
    assert abs(float(r.respuestas[0]["aprox"]) - 1.2 * (1 - math.exp(-2))) < 1e-4
    assert r.respuestas[-1]["aprox"] == "1.2"            # corriente estacionaria E/R
    sol = resolver(leer_ed("1/2 y' + 10 y = 12"), None, leer_condiciones("y(0)=0"))
    assert es_cero(sol.valor.der - sp.Rational(6, 5) * (1 - sp.exp(-20 * x))).ok
