"""Verificar que una función (explícita o implícita) es solución de una ED, con los
cuatro pasos del docente."""
from __future__ import annotations

import sympy as sp

from ..calculo.derivadas import derivar
from ..core import discrepancias
from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, x, y, ys
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import derivadas_implicitas, verificar_explicita, verificar_implicita

yp = sp.Symbol("y'")


def _reglas(pasos) -> str:
    nombres = []
    for p in pasos:
        if p.titulo.startswith(("Regla", "Derivada de", "Teorema")) and p.titulo not in nombres:
            nombres.append(p.titulo)
    return ", ".join(n.lower() for n in nombres)


def _sustituir_derivadas(ed: ED, valores: dict[int, sp.Expr], f) -> tuple[sp.Expr, sp.Expr]:
    rep = {sp.Derivative(y(x), (x, k)): v for k, v in valores.items()}
    izq = ed.lhs.subs(rep).subs(y(x), f)
    der = ed.rhs.subs(rep).subs(y(x), f)
    return izq, der


def verificar_solucion(ed: ED, izq: sp.Expr, der: sp.Expr, condiciones=None) -> Resultado:
    explicita = izq == ys and ys not in der.free_symbols
    return _explicita(ed, der) if explicita else _implicita(ed, izq, der)


def _concluir(res: Resultado, ed: ED, v: Verificacion, texto_sol: str, trivial: bool = False):
    if v.ok:
        expl = f"Se verifica la identidad, entonces {texto_sol} es solución de la ecuación diferencial."
        if trivial:
            expl += " Nota: es la solución constante y=0, llamada solución trivial."
    else:
        expl = f"No se cumple la identidad: {texto_sol} NO es solución de la ecuación diferencial ({v.detalle or v.como})."
    p = Paso("Cuarto paso. Conclusión", "verificación", "", "", expl,
             discrepancia=discrepancias.nota("verificacion", ed))
    res.pasos.append(p)
    res.verificacion = v


def _explicita(ed: ED, f: sp.Expr) -> Resultado:
    res = Resultado("verificar solución explícita")
    n = max(ed.orden, 1)
    valores, partes, reglas = {}, [], []
    actual = f
    for k in range(1, n + 1):
        r = derivar(actual, x)
        actual = r.valor
        valores[k] = actual
        reglas += [p for p in r.pasos]
        partes.append(rf"y{'′' if False else chr(39) * k} = {latex(actual)}" if k <= 3 else rf"y^{{({k})}} = {latex(actual)}")
    res.pasos.append(Paso("Primer paso. Determinar las derivadas de la función y", "derivación por reglas",
                          rf"y = {latex(f)}", r" \quad ;\quad ".join(partes),
                          "Reglas usadas: " + (_reglas(reglas) or "tabla") + "."))
    izq, der = _sustituir_derivadas(ed, valores, f)
    res.pasos.append(Paso("Segundo paso. Reemplazar las derivadas y la función en la ecuación diferencial",
                          "sustitución", latex(ed.lhs) + " = " + latex(ed.rhs), latex(izq) + " = " + latex(der)))
    izq_s, der_s = simplificar(sp.expand(izq)), simplificar(sp.expand(der))
    diff_s = sp.simplify(izq - der)
    despues = latex(izq_s) + " = " + latex(der_s)
    if diff_s == 0 and not (izq_s == 0 and der_s == 0):
        despues += r"\;\Rightarrow\; 0 = 0"
    res.pasos.append(Paso("Tercer paso. Realizar operaciones algebraicas y simplificar para verificar la identidad",
                          "álgebra", latex(izq) + " = " + latex(der), despues))
    v = verificar_explicita(ed, f)
    res.solucion = "y = " + latex(f)
    _concluir(res, ed, v, f"la función $y={latex(f)}$", trivial=(sp.simplify(f) == 0))
    return res


def _relacion_derivada(G: sp.Expr):
    """Relación entre x, y, y' obtenida al derivar G(x,y)=0, eliminando integrales con G=0.

    Devuelve (lhs, rhs) con lhs = coeficiente·y' y rhs el resto, o None.
    """
    D = sp.diff(G, x) + sp.diff(G, ys) * yp
    ints = sorted(D.atoms(sp.Integral) | G.atoms(sp.Integral), key=str)
    for I in ints:
        if not G.has(I):
            continue
        sol = sp.solve(G, I)
        if sol:
            D = D.subs(I, sol[0])
            break
    num = sp.expand(sp.fraction(sp.together(D))[0])
    A = num.coeff(yp, 1)
    B = sp.expand(num - A * yp)
    if A == 0 or num.has(sp.Integral):
        return None
    return sp.factor_terms(-A) * yp, sp.expand(B)


def _implicita(ed: ED, izq: sp.Expr, der: sp.Expr) -> Resultado:
    res = Resultado("verificar solución implícita")
    G = izq - der
    n = max(ed.orden, 1)
    # Primer paso: derivar implícitamente
    Gf = G.subs(ys, y(x))
    rd = derivar(Gf, x)
    try:
        ders = derivadas_implicitas(G, n)
    except ValueError as exc:
        res.verificacion = Verificacion(False, "no verificada", str(exc))
        res.pasos.append(Paso("Primer paso", "", "", "", f"No pude derivar implícitamente: {exc}."))
        return res
    partes = [rf"y' = {latex(ders[0])}"] + [rf"y'' = {latex(ders[1])}" if k == 2 else rf"y^{{({k + 1})}} = {latex(d)}"
                                           for k, d in enumerate(ders[1:], 1)]
    res.pasos.append(Paso(
        "Primer paso. Determinar la derivada de la función y que está en forma implícita", "derivación implícita",
        rf"\frac{{d}}{{dx}}\left[{latex(izq)}\right] = \frac{{d}}{{dx}}\left[{latex(der)}\right]",
        r" \quad ;\quad ".join(partes),
        "Se deriva ambos lados respecto de $x$ tratando $y$ como función de $x$ y se despeja la derivada. "
        "Reglas usadas: " + (_reglas(rd.pasos) or "tabla") + "."))
    e = ed.expr
    for d in sorted(e.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        e = e.subs(d, ders[int(d.derivative_count) - 1])
    e = e.subs(y(x), ys)
    izq_ed = ed.lhs
    for d in sorted(ed.expr.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        izq_ed = izq_ed.subs(d, ders[int(d.derivative_count) - 1])
    der_ed = ed.rhs
    for d in sorted(ed.expr.atoms(sp.Derivative), key=lambda d: -d.derivative_count):
        der_ed = der_ed.subs(d, ders[int(d.derivative_count) - 1])
    res.pasos.append(Paso("Segundo paso. Reemplazar la derivada y la función en la ecuación diferencial",
                          "sustitución", latex(ed.lhs) + " = " + latex(ed.rhs),
                          latex(izq_ed.subs(y(x), ys)) + " = " + latex(der_ed.subs(y(x), ys))))
    residuo = sp.simplify(e)
    v = verificar_implicita(ed, izq, der)
    if residuo == 0:
        despues = r"0 = 0"
        expl = ""
    elif v.ok:
        despues = latex(residuo) + " = 0"
        expl = "El residuo no es idénticamente cero, pero se anula sobre la curva dada ($G=C$)."
    else:
        despues = latex(residuo) + r" \neq 0"
        expl = "Después de simplificar queda un residuo distinto de cero sobre la curva."
    res.pasos.append(Paso("Tercer paso. Realizar operaciones algebraicas y simplificar para verificar la identidad",
                          "álgebra", "", despues, expl))
    res.solucion = latex(izq) + " = " + latex(der)
    _concluir(res, ed, v, f"la función implícita ${latex(izq)}={latex(der)}$")
    if not v.ok:
        rel = _relacion_derivada(G)
        if rel is not None:
            r_l, r_r = rel
            res.pasos.append(Paso(
                "Relación que sí cumple la función", "derivar y eliminar con la relación dada", "",
                latex(r_l) + " = " + latex(r_r),
                "Derivando la función dada (y usando su propia relación para eliminar las integrales) se obtiene esta "
                "ecuación, que es distinta de la que se quería verificar."))
    return res
