"""Dependencia lineal y Wronskiano.

Definición: f1,...,fn son linealmente independientes si C1 f1 + ... + Cn fn = 0 solo
con todas las C = 0. El Wronskiano W != 0 en algún punto prueba independencia; W = 0
NO prueba dependencia, salvo que las funciones sean soluciones de una misma ED lineal
homogénea (docs/DISCREPANCIAS.md, A7).
"""
from __future__ import annotations

import mpmath as mp
import sympy as sp

from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import x
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import es_cero


def matriz_wronskiana(funcs: list[sp.Expr], var=x) -> sp.Matrix:
    n = len(funcs)
    return sp.Matrix([[sp.diff(f, var, k) for f in funcs] for k in range(n)])


def wronskiano(funcs: list[sp.Expr], var=x) -> sp.Expr:
    return simplificar(sp.simplify(matriz_wronskiana(funcs, var).det()))


def _latex_matriz(M: sp.Matrix, barras=True) -> str:
    filas = r" \\ ".join(" & ".join(latex(e) for e in M.row(i)) for i in range(M.rows))
    env = "vmatrix" if barras else "pmatrix"
    return rf"\begin{{{env}}} {filas} \end{{{env}}}"


def relacion_lineal(funcs: list[sp.Expr], var=x) -> list[sp.Expr] | None:
    """Coeficientes (C1..Cn) no todos nulos con ΣCi fi ≡ 0, o None si no existen."""
    n = len(funcs)
    mp.mp.dps = 40
    puntos = [mp.mpf(k) / 7 + mp.mpf("0.37") for k in range(n + 6)]
    fs = [sp.lambdify(var, f, modules="mpmath") for f in funcs]
    try:
        A = mp.matrix([[fs[j](p) for j in range(n)] for p in puntos])
        _, S, V = mp.svd_r(A, full_matrices=True)
    except Exception:
        return None
    sv = [S[i] for i in range(len(S))]
    if len(sv) < n or abs(sv[n - 1]) > mp.mpf("1e-25") * max(1, abs(sv[0])):
        return None
    v = [V[n - 1, j] for j in range(n)]
    mayor = max(v, key=abs)
    v = [c / mayor for c in v]
    coef = [sp.nsimplify(sp.Float(mp.nstr(c, 30), 30), rational=True, tolerance=1e-12) for c in v]
    # entero mínimo
    den = sp.ilcm(*[sp.fraction(c)[1] for c in coef])
    coef = [c * den for c in coef]
    if es_cero(sum(c * f for c, f in zip(coef, funcs))).ok:
        return coef
    return None


def analizar_dependencia(funcs: list[sp.Expr], mismo_ed: bool = False, var=x) -> Resultado:
    res = Resultado("dependencia lineal y Wronskiano")
    n = len(funcs)
    if n < 2:
        raise ValueError("Se necesitan al menos dos funciones.")
    if any(f.has(sp.Abs) for f in funcs):
        raise ValueError("Con valor absoluto el Wronskiano es por tramos: fuera del temario.")
    M = matriz_wronskiana(funcs, var)
    res.pasos.append(Paso(
        "Armar el Wronskiano", "W(f₁,…,fₙ) = det[fᵢ⁽ʲ⁾]",
        "f_1, \\dots, f_{%d} = %s" % (n, ",\\ ".join(latex(f) for f in funcs)),
        "W = " + _latex_matriz(M),
        "Cada columna lleva una función y sus derivadas hasta el orden $n-1$."))
    W = wronskiano(funcs, var)
    res.pasos.append(Paso("Calcular el determinante", "determinante", "", "W = " + latex(W),
                          "Se desarrolla el determinante y se simplifica."))
    cero = sp.simplify(W) == 0 or es_cero(W).ok
    if not cero:
        # punto de prueba
        for p0 in (1, 2, sp.Rational(1, 2), 3, -1):
            val = sp.simplify(W.subs(var, p0))
            if val != 0 and val.is_finite is not False:
                break
        res.pasos.append(Paso("Conclusión", "W ≠ 0 en algún punto ⇒ independientes", "", f"W({latex(p0)}) = {latex(val)} \\neq 0",
                              "El Wronskiano no es idénticamente cero: las funciones son linealmente independientes."))
        res.solucion = "linealmente independientes"
        res.verificacion = Verificacion(True, "Wronskiano ≠ 0")
        return res
    rel = relacion_lineal(funcs, var)
    if rel is not None:
        comb = " + ".join(f"({latex(c)})\\,({latex(f)})" for c, f in zip(rel, funcs) if c != 0)
        res.pasos.append(Paso("Buscar una combinación lineal nula", "definición de dependencia lineal", "",
                              comb + " = 0",
                              "Existen constantes no todas nulas con suma cero: las funciones son linealmente dependientes."))
        res.solucion = "linealmente dependientes"
        res.verificacion = Verificacion(True, "combinación lineal nula", comb)
        return res
    if mismo_ed:
        res.pasos.append(Paso("Conclusión", "teorema: soluciones de una misma ED lineal", "", "W \\equiv 0",
                              "Como son soluciones de una misma ecuación diferencial lineal homogénea y $W\\equiv 0$, son linealmente dependientes."))
        res.solucion = "linealmente dependientes"
        res.verificacion = Verificacion(True, "W ≡ 0 y soluciones de una misma ED lineal")
        return res
    res.pasos.append(Paso(
        "Conclusión", "W = 0 no basta", "", "W \\equiv 0",
        "$W\\equiv 0$ no alcanza para decir que son dependientes (solo sirve si son soluciones de la misma ED lineal homogénea). "
        "Además no existe una combinación lineal nula con constantes no todas cero: por la definición son linealmente independientes."))
    res.solucion = "linealmente independientes"
    res.advertencias.append("W ≡ 0 pero las funciones son independientes por definición.")
    res.verificacion = Verificacion(True, "definición (no hay combinación lineal nula)")
    return res
