"""Clasificador de métodos de primer orden y despachador."""
from __future__ import annotations

import sympy as sp

from ..core import discrepancias
from ..core.lector import ED, x, y, ys
from ..core.paso import Paso, Resultado, Verificacion
from ..core.latex import latex
from . import exacta, grado_superior, lineales, separable
from .base import NoAplica, Solucion, forma, p

# id -> (título, función aplica(ed) -> motivo|None, función resolver(ed, condiciones))
METODOS = {
    "separable": ("Variables separables", separable.aplica_separable, separable.resolver_separable),
    "lineal_y": ("Lineal en y", lambda e: lineales.aplica_lineal(e, False), lambda e, c: lineales.resolver_lineal(e, c, False)),
    "lineal_x": ("Lineal en x", lambda e: lineales.aplica_lineal(e, True), lambda e, c: lineales.resolver_lineal(e, c, True)),
    "bernoulli_y": ("Bernoulli en y", lambda e: lineales.aplica_bernoulli(e, False), lambda e, c: lineales.resolver_bernoulli(e, c, False)),
    "bernoulli_x": ("Bernoulli en x", lambda e: lineales.aplica_bernoulli(e, True), lambda e, c: lineales.resolver_bernoulli(e, c, True)),
    "exacta": ("Exacta", exacta.aplica_exacta, exacta.resolver_exacta),
    "homogenea": ("Homogénea (se elige y = t x o x = t y)", lineales.aplica_homogenea, lambda e, c: lineales.resolver_homogenea(e, c)),
    "homogenea_yx": ("Homogénea con y = t x", lineales.aplica_homogenea, lambda e, c: lineales.resolver_homogenea(e, c, "yx")),
    "homogenea_xy": ("Homogénea con x = t y", lineales.aplica_homogenea, lambda e, c: lineales.resolver_homogenea(e, c, "xy")),
    "reducible_lineal": ("Reducible a separable: y' = f(ax+by+c)", separable.aplica_reducible_lineal, separable.resolver_reducible_lineal),
    "reducible_xy": ("Reducible a separable: función de xy", separable.aplica_reducible_xy, separable.resolver_reducible_xy),
    "clairaut": ("Clairaut", lambda e: grado_superior.aplica_grado_superior(e, "clairaut"), grado_superior.resolver_clairaut),
    "lagrange": ("Lagrange", lambda e: grado_superior.aplica_grado_superior(e, "lagrange"), grado_superior.resolver_lagrange),
    "y_f_p": ("y = f(y')", lambda e: grado_superior.aplica_grado_superior(e, "y_p"), grado_superior.resolver_y_f_p),
    "x_f_p": ("x = f(y')", lambda e: grado_superior.aplica_grado_superior(e, "x_p"), grado_superior.resolver_x_f_p),
}
PREFERENCIA = ["separable", "lineal_y", "lineal_x", "bernoulli_y", "bernoulli_x", "exacta", "homogenea",
               "reducible_lineal", "reducible_xy", "clairaut", "lagrange", "y_f_p", "x_f_p"]
_OCULTOS = {"homogenea_yx", "homogenea_xy"}  # solo se usan si el usuario los fuerza


def _factores(ed: ED):
    """Raíces de F(x,y,p)=0 respecto de p (ED de grado superior que se factoriza), o None."""
    try:
        F = forma(ed).F
    except NoAplica:
        return None
    if not F.has(p) or not F.is_polynomial(p) or sp.degree(F, p) < 2:
        return None
    try:
        raices = sp.solve(F, p)
    except Exception:
        return None
    if len(raices) < 2 or any(r.has(p) or r.has(sp.RootOf, sp.CRootOf) for r in raices):
        return None
    return raices


def _param_libre(ed: ED):
    if ed.forma != "diferencial":
        return None
    libres = (ed.M.free_symbols | ed.N.free_symbols) - {x, ys, sp.Symbol("QQ")}
    return sorted(libres, key=lambda s: s.name)[0] if len(libres) == 1 else None


def clasificar_metodos(ed: ED) -> list[dict]:
    """Todos los métodos aplicables, por orden de preferencia, con el motivo."""
    if ed.orden != 1:
        return []
    out = []
    for m in PREFERENCIA:
        titulo, aplica, _ = METODOS[m]
        try:
            motivo = aplica(ed)
        except Exception:
            motivo = None
        if motivo:
            out.append({"metodo": m, "titulo": titulo, "motivo": motivo})
    if _factores(ed) is not None:
        out.append({"metodo": "factorizable", "titulo": "Grado superior que se factoriza en y'",
                    "motivo": "F(x,y,y') = 0 se resuelve para y' y da varias ecuaciones de primer grado"})
    return out


def _resolver_factorizable(ed: ED, condiciones=None) -> Resultado:
    raices = _factores(ed)
    if raices is None:
        raise NoAplica("La ecuación no se factoriza en ecuaciones de primer grado en y'.")
    res = Resultado("grado superior: factorización en y'")
    res.pasos.append(Paso("Sustitución y' = p y resolver para p", "F(x, y, p) = 0", latex(ed.lhs) + " = " + latex(ed.rhs),
                          r"\ ;\quad ".join("p = " + latex(r) for r in raices),
                          "Se resuelve la ecuación en $p=y'$; cada raíz da una ecuación diferencial de primer orden."))
    ok_todas, partes, sols = True, [], []
    for r in raices:
        sub = ED(f"y' = {r}", "derivada", sp.Derivative(y(x), x), r.subs(ys, y(x)), 1)
        try:
            rr = resolver(sub, None, condiciones)
        except NoAplica:
            rr = None
        if rr is None or rr.valor is None:
            ok_todas = False
            res.advertencias.append(f"No pude resolver y' = {latex(r)} con los métodos del temario.")
            continue
        res.pasos.append(Paso(f"Resolver y' = {latex(r)} ({rr.metodo})", "", "y' = " + latex(r), rr.solucion))
        res.advertencias += [a for a in rr.advertencias if a not in res.advertencias]
        sols.append(rr)
        partes.append(rr.solucion)
        res.adicionales += rr.adicionales
        res.extra += rr.extra
    if not sols:
        raise NoAplica("Ningún factor se resolvió.")
    res.solucion = r"\ ;\quad ".join(partes)
    res.valor = [s.valor for s in sols]
    res.constantes = ["C"]
    res.verificacion = Verificacion(ok_todas and all(s.verificacion and s.verificacion.ok for s in sols),
                                    "cada factor verificado por sustitución")
    return res


def resolver(ed: ED, metodo: str | None = None, condiciones=None) -> Resultado:
    """Resuelve una ED de primer orden. Si ``metodo`` es None usa el preferido."""
    if ed.orden != 1:
        raise NoAplica("Solo resuelvo ecuaciones de primer orden aquí (las de orden superior llegan en F5 y F6).")
    cand = clasificar_metodos(ed)
    ids = [c["metodo"] for c in cand]
    elegido = metodo or (ids[0] if ids else None)
    qq = sp.Symbol("QQ")
    if ed.forma == "diferencial" and (ed.M.has(qq) or ed.N.has(qq)):
        elegido = "exacta"
    k = _param_libre(ed) if (metodo in (None, "exacta") and elegido in (None, "exacta") and "exacta" not in ids) else None
    if elegido is None and k is None:
        return _ninguno(ed)
    try:
        if k is not None:
            r = exacta.hallar_k(ed, k, condiciones)
        elif elegido == "factorizable":
            r = _resolver_factorizable(ed, condiciones)
        elif elegido in METODOS:
            r = METODOS[elegido][2](ed, condiciones)
        else:
            raise NoAplica(f"Método desconocido: {elegido}.")
    except NoAplica as exc:
        if metodo:
            raise
        return _ninguno(ed, str(exc))
    nota = discrepancias.nota("solucion", ed, condiciones)
    if nota and r.pasos:
        ultimo = next((s for s in reversed(r.pasos) if "solución" in s.titulo.lower()), r.pasos[-1])
        ultimo.discrepancia = nota
    r.otros_metodos_aplicables = [c for c in cand if c["metodo"] != elegido]
    r.advertencias = list(dict.fromkeys(r.advertencias))
    return r


def _ninguno(ed: ED, motivo: str = "") -> Resultado:
    """Ningún método aplica: no se inventan pasos (regla 5)."""
    intentos = []
    for m in PREFERENCIA:
        try:
            METODOS[m][2](ed, None)
        except NoAplica as exc:
            intentos.append(f"{METODOS[m][0]}: {exc}")
        except Exception as exc:
            intentos.append(f"{METODOS[m][0]}: error ({type(exc).__name__})")
    res = Resultado("ninguno")
    res.advertencias.append("No aplica con los métodos del temario (separable, reducibles a separable, homogénea, lineal, "
                            "Bernoulli, exacta, Clairaut, Lagrange, y = f(y'), x = f(y')).")
    res.advertencias += ["Se intentó — " + i for i in intentos]
    if motivo:
        res.advertencias.append(motivo)
    return res
