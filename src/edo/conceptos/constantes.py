"""Constantes con condiciones iniciales y tipos de solución (general, particular, singular, trivial)."""
from __future__ import annotations

import re

import sympy as sp

from ..core import discrepancias
from ..core.algebra import simplificar
from ..core.latex import latex
from ..core.lector import ED, Condicion, x, y, ys
from ..core.paso import Paso, Resultado, Verificacion
from ..core.verificador import derivadas_implicitas, es_cero, verificar_explicita, verificar_implicita

_RE_CTE = re.compile(r"^C\d*$")


def constantes_de(e: sp.Expr) -> list[sp.Symbol]:
    cs = [s for s in e.free_symbols if _RE_CTE.match(s.name)]
    return sorted(cs, key=lambda s: (len(s.name), s.name))


def _cond_txt(c: Condicion) -> str:
    if c.orden == 0:
        return f"y({latex(c.x0)}) = {latex(c.valor)}"
    marca = "'" * c.orden if c.orden <= 3 else f"^{{({c.orden})}}"
    return f"y{marca}({latex(c.x0)}) = {latex(c.valor)}"


def determinar_constantes(ed: ED | None, izq: sp.Expr, der: sp.Expr, condiciones: list[Condicion]) -> Resultado:
    """Halla las constantes de la solución general con las condiciones y escribe la particular."""
    res = Resultado("constantes con condiciones iniciales")
    explicita = izq == ys and ys not in der.free_symbols
    G = der if explicita else izq - der
    cs = constantes_de(G)
    res.constantes = [c.name for c in cs]
    if not cs:
        res.advertencias.append("La solución dada no tiene constantes arbitrarias.")
    if not condiciones:
        raise ValueError("Faltan las condiciones iniciales.")
    ordenes = sorted({c.orden for c in condiciones})
    # Paso 1: solución general y (si hace falta) sus derivadas
    if explicita:
        derivs = {k: sp.diff(G, x, k) for k in ordenes}
        partes = [("y" if k == 0 else ("y" + "'" * k if k <= 3 else f"y^{{({k})}}")) + " = " + latex(derivs[k]) for k in ordenes]
        res.pasos.append(Paso("Primer paso. Escribir la solución general y las derivadas necesarias", "solución general",
                              "", r" \quad ;\quad ".join(partes),
                              f"Hay {len(cs)} constante(s) arbitraria(s): ${', '.join(latex(c) for c in cs)}$."))
    else:
        res.pasos.append(Paso("Primer paso. Escribir la solución general", "solución general", "",
                              latex(izq) + " = " + latex(der)))
    # Paso 2: reemplazar
    ecs: list[sp.Expr] = []
    texto_ecs = []
    notas = []
    for c in condiciones:
        if c.orden == 0:
            notas.append(f"${_cond_txt(c)}$ significa $x={latex(c.x0)}$, $y={latex(c.valor)}$.")
            e = (G.subs(x, c.x0) - c.valor) if explicita else G.subs({x: c.x0, ys: c.valor})
            lado = (f"{latex(c.valor)} = {latex(G.subs(x, c.x0))}" if explicita
                    else latex(G.subs({x: c.x0, ys: c.valor})) + " = 0")
        else:
            notas.append(f"${_cond_txt(c)}$ significa que la derivada en $x={latex(c.x0)}$ vale ${latex(c.valor)}$.")
            if explicita:
                e = sp.diff(G, x, c.orden).subs(x, c.x0) - c.valor
                lado = f"{latex(c.valor)} = {latex(sp.diff(G, x, c.orden).subs(x, c.x0))}"
            else:
                y0 = next((k.valor for k in condiciones if k.orden == 0 and k.x0 == c.x0), None)
                if y0 is None:
                    raise ValueError("Con solución implícita, una condición sobre y' necesita también y(a).")
                ders = derivadas_implicitas(G, c.orden)
                e = ders[c.orden - 1].subs({x: c.x0, ys: y0}) - c.valor
                lado = f"{latex(c.valor)} = {latex(ders[c.orden - 1].subs({x: c.x0, ys: y0}))}"
        ecs.append(e)
        texto_ecs.append(lado)
    res.pasos.append(Paso("Segundo paso. Reemplazar las condiciones iniciales en la solución general", "condiciones iniciales",
                          ", ".join(_cond_txt(c) for c in condiciones), r" \quad ;\quad ".join(texto_ecs),
                          " ".join(notas)))
    # Paso 3: resolver
    sol = sp.solve(ecs, cs, dict=True) if cs else []
    if not sol:
        res.advertencias.append("No hay valores de las constantes que cumplan todas las condiciones.")
        res.pasos.append(Paso("Tercer paso. Determinar el valor de las constantes", "resolver el sistema", "",
                              "", "El sistema de ecuaciones no tiene solución: las condiciones son incompatibles con la familia dada."))
        res.verificacion = Verificacion(False, "no verificada", "sin solución para las constantes")
        return res
    if len(sol) > 1:
        res.advertencias.append(f"Hay {len(sol)} conjuntos de valores posibles para las constantes; se muestra el primero.")
    s0 = sol[0]
    libres = [c for c in cs if c not in s0]
    if libres:
        res.advertencias.append("Quedan constantes sin determinar: " + ", ".join(c.name for c in libres)
                                + " (hay menos condiciones que constantes).")
    valores = ", ".join(f"{latex(k)} = {latex(v)}" for k, v in s0.items())
    res.pasos.append(Paso("Tercer paso. Determinar el valor de las constantes", "resolver el sistema",
                          "", valores, "", discrepancia=discrepancias.nota("constantes", ed, condiciones) if ed else None))
    # Paso 4: solución particular
    Gp = G.subs(s0)
    if explicita:
        fp = (sp.expand(Gp) if Gp.is_polynomial(x) else simplificar(sp.expand(Gp))) if not Gp.has(sp.Integral) else Gp
        res.solucion = "y = " + latex(fp)
        res.valor = fp
        res.pasos.append(Paso("Cuarto paso. Escribir la solución particular", "solución particular", "",
                              "y = " + latex(fp), "Se reemplazan los valores de las constantes en la solución general."))
        v = verificar_explicita(ed, fp) if ed else Verificacion(True, "no se pidió verificar contra una ED")
        if all(c.orden == 0 for c in condiciones) or True:
            chk = [es_cero(sp.diff(fp, x, c.orden).subs(x, c.x0) - c.valor).ok for c in condiciones]
            if not all(chk):
                v = Verificacion(False, "no verificada", "la solución particular no cumple las condiciones")
    else:
        Gs = simplificar(sp.expand(Gp)) if not Gp.has(sp.Integral) else Gp
        res.solucion = latex(Gs) + " = 0"
        res.valor = Gs
        res.pasos.append(Paso("Cuarto paso. Escribir la solución particular", "solución particular", "",
                              latex(Gs) + " = 0"))
        v = verificar_implicita(ed, Gs, sp.Integer(0)) if ed else Verificacion(True, "no se pidió verificar contra una ED")
    if ed and v.ok:
        res.pasos.append(Paso("Comprobación", "sustitución en la ED original", "", "",
                              f"La solución particular cumple la ecuación diferencial y las condiciones ({v.como})."))
    res.verificacion = v
    return res


def clasificar_solucion(ed: ED, izq: sp.Expr, der: sp.Expr, general: tuple[sp.Expr, sp.Expr] | None = None) -> Resultado:
    """¿La función dada es solución general, particular, singular o trivial?"""
    res = Resultado("tipo de solución")
    explicita = izq == ys and ys not in der.free_symbols
    v = verificar_explicita(ed, der) if explicita else verificar_implicita(ed, izq, der)
    res.verificacion = v
    texto = ("y = " + latex(der)) if explicita else latex(izq) + " = " + latex(der)
    res.solucion = texto
    res.pasos.append(Paso("Verificar que es solución", "sustitución en la ED", "", texto,
                          "Se cumple la ecuación diferencial." if v.ok else "No cumple la ecuación diferencial."))
    if not v.ok:
        res.pasos.append(Paso("Conclusión", "", "", "", "No es solución, por lo tanto no tiene tipo."))
        return res
    G = der if explicita else izq - der
    cs = constantes_de(G)
    n = ed.orden
    if explicita and sp.simplify(der) == 0:
        tipo, por = "trivial", "Es la función constante $y=0$ (solución trivial)."
    elif len(cs) == n and n > 0:
        tipo = "general"
        por = f"Tiene {len(cs)} constante(s) arbitraria(s), igual al orden {n} de la ecuación."
    elif 0 < len(cs) < n:
        tipo = "familia con menos constantes que el orden"
        por = f"Tiene {len(cs)} constante(s) pero la ecuación es de orden {n}: no es la solución general."
    elif len(cs) > n:
        tipo, por = "no válida como general", f"Tiene más constantes ({len(cs)}) que el orden ({n}); no son independientes."
    else:
        if general is None:
            tipo = "particular o singular"
            por = ("No tiene constantes. Para decidir si es particular (sale de la solución general al dar valores a "
                   "las constantes) o singular (no sale de ella) hace falta la solución general.")
        else:
            gi, gd = general
            gG = gd if (gi == ys and ys not in gd.free_symbols) else None
            if gG is None or not explicita:
                tipo, por = "particular o singular", "Solo comparo contra una solución general explícita."
            else:
                gcs = constantes_de(gG)
                eqs = [gG.subs(x, sp.Rational(k, 3) + 1) - der.subs(x, sp.Rational(k, 3) + 1) for k in range(len(gcs) + 3)]
                try:
                    sols = sp.solve(eqs, gcs, dict=True)
                except Exception:
                    sols = []
                pertenece = any(es_cero(gG.subs(s) - der).ok for s in sols)
                if pertenece:
                    tipo, por = "particular", "Se obtiene de la solución general dando valores a las constantes."
                else:
                    tipo, por = "singular", "Cumple la ecuación pero no se obtiene de la solución general para ningún valor de las constantes."
    res.pasos.append(Paso("Tipo de solución", "definiciones: general, particular, singular, trivial", "", "",
                          f"Es solución {tipo}. {por}"))
    return res
