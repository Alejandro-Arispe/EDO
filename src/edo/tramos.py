"""Ecuaciones con coeficientes definidos por tramos (p. ej. P(x) = −2/x si 0 < x ≤ 2, 2 si x > 2).

Se resuelve cada tramo como problema de valores iniciales: el tramo que contiene el punto de la
condición usa esa condición y los vecinos usan la continuidad de y y de sus derivadas en la frontera.
"""
from __future__ import annotations

import sympy as sp

from .core.latex import latex
from .core.lector import Condicion, ErrorLectura, leer_condiciones, leer_ed, leer_expresion, x
from .core.paso import Paso, Resultado, Verificacion
from .primer_orden.base import NoAplica, Solucion
from .resolutor import resolver


def _num(txt: str) -> sp.Expr:
    t = txt.strip().lower()
    if t in {"oo", "inf", "infinito", "+oo", "∞"}:
        return sp.oo
    if t in {"-oo", "-inf", "-∞"}:
        return -sp.oo
    return leer_expresion(txt)


def _funcion(r: Resultado) -> sp.Expr:
    v = r.valor
    f = v.der if isinstance(v, Solucion) and v.explicita else (v if isinstance(v, sp.Expr) else None)
    if f is None:
        raise NoAplica("El tramo no quedó en forma explícita y(x); no puedo empalmar con el siguiente.")
    return f


def resolver_por_tramos(tramos: list[dict], condiciones: str) -> Resultado:
    if not tramos:
        raise NoAplica("Escribe al menos un tramo.")
    try:
        datos = sorted([(_num(t["desde"]), _num(t["hasta"]), leer_ed(t["ed"])) for t in tramos], key=lambda q: float(sp.N(q[0])) if q[0] != -sp.oo else -1e300)
        conds = leer_condiciones(condiciones)
    except ErrorLectura as exc:
        raise NoAplica(str(exc)) from exc
    n = datos[0][2].orden
    if any(d[2].orden != n for d in datos):
        raise NoAplica("Todos los tramos deben tener el mismo orden.")
    if len(conds) != n or sorted(c.orden for c in conds) != list(range(n)) or len({c.x0 for c in conds}) != 1:
        raise NoAplica(f"Hacen falta {n} condición(es) en un mismo punto (y, y', …, y^({n - 1})).")
    x0 = conds[0].x0
    k0 = next((k for k, (a, b, _) in enumerate(datos) if (a < x0 <= b) or (k == 0 and x0 == a)), None)
    if k0 is None:
        raise NoAplica(f"El punto x = {x0} de la condición no cae en ningún tramo.")
    res = Resultado("ecuación por tramos")
    sols: dict[int, tuple[Resultado, sp.Expr]] = {}

    def resolver_tramo(k: int, cs: list[Condicion], motivo: str):
        a, b, ed = datos[k]
        r = resolver(ed, None, cs)
        if r.metodo == "ninguno" or r.valor is None:
            raise NoAplica(f"El tramo {k + 1} no se resolvió con los métodos del temario.")
        sols[k] = (r, _funcion(r))
        res.pasos.append(Paso(f"Tramo {k + 1}: {latex(a)} < x ≤ {latex(b)}", motivo, latex(ed.lhs) + " = " + latex(ed.rhs), "y = " + latex(sols[k][1]),
                              "Condiciones: " + "; ".join(f"y{chr(39) * c.orden if c.orden else ''}({latex(c.x0)}) = {latex(c.valor)}" for c in cs)))
        for p in r.pasos:
            res.pasos.append(Paso(f"  Tramo {k + 1} · " + p.titulo, p.regla, p.antes_latex, p.despues_latex, p.explicacion, p.discrepancia))
        res.advertencias.extend(a_ for a_ in r.advertencias if a_ not in res.advertencias)

    resolver_tramo(k0, conds, "condición dada")
    for k in range(k0 + 1, len(datos)):                       # hacia la derecha: continuidad en la frontera izquierda del tramo
        frontera = datos[k][0]
        f = sols[k - 1][1]
        cs = [Condicion(j, frontera, sp.simplify(sp.limit(sp.diff(f, x, j), x, frontera, "-"))) for j in range(n)]
        resolver_tramo(k, cs, f"continuidad en x = {latex(frontera)}")
    for k in range(k0 - 1, -1, -1):                           # hacia la izquierda
        frontera = datos[k][1]
        f = sols[k + 1][1]
        cs = [Condicion(j, frontera, sp.simplify(sp.limit(sp.diff(f, x, j), x, frontera, "+"))) for j in range(n)]
        resolver_tramo(k, cs, f"continuidad en x = {latex(frontera)}")
    orden = sorted(sols)
    casos = [(sols[k][1], sp.And(datos[k][0] < x, x <= datos[k][1])) for k in orden]
    res.valor = sp.Piecewise(*casos)
    res.solucion = r"y = \begin{cases} " + r" \\ ".join(f"{latex(sols[k][1])} & {latex(datos[k][0])} < x \\le {latex(datos[k][1])}" for k in orden) + r" \end{cases}"
    ok = all(sols[k][0].verificacion and sols[k][0].verificacion.ok for k in orden)
    res.verificacion = Verificacion(ok, "cada tramo verificado por sustitución; y y sus derivadas se empalmaron por continuidad")
    res.pasos.append(Paso("Solución por tramos", "continuidad en las fronteras", "", res.solucion.replace("y = ", "y = ", 1)))
    return res
