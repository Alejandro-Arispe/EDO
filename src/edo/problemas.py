"""Problemas escritos con plantillas: modelos clásicos que se arman, se resuelven con los
métodos del temario y se contestan (sin internet y sin IA).

Dentro del programa la variable independiente es x (aquí representa el tiempo t) y la
incógnita es y; la presentación aclara el significado de cada letra.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from .core.latex import latex
from .core.lector import ED, ErrorLectura, leer_condiciones, leer_ed, leer_expresion, x, y
from .core.paso import Paso, Resultado, Verificacion
from .primer_orden.base import NoAplica, Solucion
from .resolutor import resolver


@dataclass
class Plantilla:
    id: str
    titulo: str
    descripcion: str
    parametros: list[tuple[str, str, str]]   # (nombre, etiqueta, ejemplo)
    construir: object                        # p: dict[str, str] -> Modelo


@dataclass
class Modelo:
    ed: str                                  # en x, y
    explicacion: str                         # qué significan las letras
    datos: list[str]                         # condiciones como texto: "y(0)=P0"
    incognitas: list[str] = field(default_factory=list)   # parámetros por hallar con los datos
    preguntas: list[tuple[str, str, str]] = field(default_factory=list)  # (tipo, etiqueta, argumento)


def _crecimiento(p):
    k_conocida = p.get("k", "").strip()
    datos = [f"y(0)={p['P0']}"]
    inc = []
    if k_conocida:
        ed = f"y' = ({k_conocida}) y"
    else:
        ed = "y' = k y"
        datos.append(f"y({p['t1']})={p['P1']}")
        inc = ["k"]
    pregs = []
    if p.get("objetivo", "").strip():
        pregs.append(("tiempo", f"Tiempo para llegar a {p['objetivo']}", p["objetivo"]))
    if p.get("t2", "").strip():
        pregs.append(("valor", f"Valor en t = {p['t2']}", p["t2"]))
    return Modelo(ed, "y(x) es la cantidad en el tiempo x = t; la rapidez de cambio es proporcional a la cantidad (y' = k y).",
                  datos, inc, pregs)


def _enfriamiento(p):
    ed = "y' = k (y - Tm)".replace("Tm", f"({p['Tm']})")
    datos = [f"y(0)={p['T0']}", f"y({p['t1']})={p['T1']}"]
    pregs = []
    if p.get("t2", "").strip():
        pregs.append(("valor", f"Temperatura en t = {p['t2']}", p["t2"]))
    if p.get("objetivo", "").strip():
        pregs.append(("tiempo", f"Tiempo para llegar a {p['objetivo']}", p["objetivo"]))
    return Modelo(ed, "Ley de Newton: y(x) es la temperatura del cuerpo en el tiempo x = t y la del medio es Tm = " + p["Tm"] +
                  "; y' = k (y − Tm).", datos, ["k"], pregs)


def _circuito_rl(p):
    ed = f"({p['L']}) y' + ({p['R']}) y = {p['E']}"
    pregs = [("limite", "Corriente estacionaria (t → ∞)", "")]
    if p.get("t2", "").strip():
        pregs.insert(0, ("valor", f"Corriente en t = {p['t2']}", p["t2"]))
    return Modelo(ed, "Circuito RL en serie: y(x) es la corriente i(t), L y' + R y = E.", [f"y(0)={p['i0']}"], [], pregs)


def _mezcla(p):
    ed = f"y' = ({p['qe']})*({p['ce']}) - ({p['qs']})*y/(({p['V0']}) + (({p['qe']}) - ({p['qs']}))*x)"
    pregs = []
    if p.get("t2", "").strip():
        pregs.append(("valor", f"Cantidad de sal en t = {p['t2']}", p["t2"]))
    if p.get("objetivo", "").strip():
        pregs.append(("tiempo", f"Tiempo para llegar a {p['objetivo']}", p["objetivo"]))
    return Modelo(ed, "Mezclas: y(x) es la cantidad de sustancia en el tanque; entra con caudal qe y concentración ce, sale con caudal qs; "
                  "V(t) = V0 + (qe − qs)t.", [f"y(0)={p['A0']}"], [], pregs)


def _logistico(p):
    ed = f"y' = y (({p['a']}) - ({p['b']}) y)"
    pregs = [("limite", "Población límite (t → ∞)", "")]
    if p.get("t2", "").strip():
        pregs.insert(0, ("valor", f"Población en t = {p['t2']}", p["t2"]))
    return Modelo(ed, "Crecimiento logístico: y(x) es la población, y' = y (a − b y).", [f"y(0)={p['P0']}"], [], pregs)


def _caida(p):
    ed = f"({p['m']}) y' = ({p['m']})*({p['g']}) - ({p['k']}) y"
    pregs = [("limite", "Velocidad límite (t → ∞)", "")]
    if p.get("t2", "").strip():
        pregs.insert(0, ("valor", f"Velocidad en t = {p['t2']}", p["t2"]))
    return Modelo(ed, "Caída con resistencia del aire proporcional a la velocidad: y(x) es la velocidad v(t), m v' = m g − k v.",
                  [f"y(0)={p['v0']}"], [], pregs)


def _resorte(p):
    ed = f"({p['m']}) y'' + ({p['c']}) y' + ({p['k']}) y = {p.get('F', '0') or '0'}"
    pregs = []
    if p.get("t2", "").strip():
        pregs.append(("valor", f"Posición en t = {p['t2']}", p["t2"]))
    return Modelo(ed, "Masa-resorte: y(x) es la posición x(t); m y'' + c y' + k y = F(t).",
                  [f"y(0)={p['x0']}", f"y'(0)={p['v0']}"], [], pregs)


PLANTILLAS: dict[str, Plantilla] = {t.id: t for t in [
    Plantilla("crecimiento", "Crecimiento o decaimiento exponencial (población, bacterias, desintegración)",
              "y' = k y. Con dos datos se halla k; con k conocida basta y(0). Deja vacío lo que no pidas.",
              [("P0", "Cantidad inicial y(0)", "P0"), ("P1", "Cantidad en t1", "3/2*P0"), ("t1", "Tiempo t1", "1"),
               ("k", "Constante k (opcional, si ya la conoces)", ""), ("objetivo", "Cantidad objetivo (opcional)", "3*P0"),
               ("t2", "Tiempo donde preguntar la cantidad (opcional)", "")], _crecimiento),
    Plantilla("enfriamiento", "Ley de enfriamiento de Newton",
              "y' = k (y − Tm). Datos: T(0) y T(t1).",
              [("Tm", "Temperatura del medio", "20"), ("T0", "Temperatura inicial", "100"), ("T1", "Temperatura en t1", "60"),
               ("t1", "Tiempo t1", "10"), ("t2", "Tiempo donde preguntar T (opcional)", "20"),
               ("objetivo", "Temperatura objetivo (opcional)", "30")], _enfriamiento),
    Plantilla("circuito_rl", "Circuito RL en serie",
              "L i' + R i = E con i(0) dado.",
              [("L", "Inductancia L", "1"), ("R", "Resistencia R", "2"), ("E", "Fuerza electromotriz E", "10"),
               ("i0", "Corriente inicial", "0"), ("t2", "Tiempo donde preguntar i (opcional)", "1")], _circuito_rl),
    Plantilla("mezcla", "Mezclas (tanque)",
              "y' = qe·ce − qs·y / V(t) con V(t) = V0 + (qe − qs) t.",
              [("V0", "Volumen inicial V0", "100"), ("qe", "Caudal de entrada qe", "5"), ("ce", "Concentración de entrada ce", "2"),
               ("qs", "Caudal de salida qs", "5"), ("A0", "Cantidad inicial y(0)", "0"),
               ("t2", "Tiempo donde preguntar (opcional)", "10"), ("objetivo", "Cantidad objetivo (opcional)", "")], _mezcla),
    Plantilla("logistico", "Crecimiento logístico", "y' = y (a − b y), ecuación de Bernoulli.",
              [("a", "a", "1"), ("b", "b", "1/100"), ("P0", "Población inicial", "10"),
               ("t2", "Tiempo donde preguntar (opcional)", "5")], _logistico),
    Plantilla("caida", "Caída con resistencia del aire", "m v' = m g − k v.",
              [("m", "Masa m", "2"), ("g", "Gravedad g", "9.8"), ("k", "Coeficiente k", "4"), ("v0", "Velocidad inicial", "0"),
               ("t2", "Tiempo donde preguntar (opcional)", "1")], _caida),
    Plantilla("resorte", "Masa-resorte (orden 2)", "m x'' + c x' + k x = F(t) con posición y velocidad iniciales.",
              [("m", "Masa m", "1"), ("c", "Amortiguamiento c", "0"), ("k", "Constante k", "4"), ("F", "Fuerza F(t) (opcional)", "0"),
               ("x0", "Posición inicial", "1"), ("v0", "Velocidad inicial", "0"), ("t2", "Tiempo donde preguntar (opcional)", "1")], _resorte),
]}


def _positivos(e: sp.Expr, simbolos) -> tuple[sp.Expr, dict]:
    rep = {s: sp.Symbol(s.name, positive=True) for s in simbolos}
    return e.subs(rep), rep


def _aprox(v) -> str:
    try:
        return f"{float(sp.N(v)):.6g}"
    except (TypeError, ValueError):
        return ""


def resolver_plantilla(pid: str, params: dict[str, str]) -> Resultado:
    if pid not in PLANTILLAS:
        raise NoAplica(f"Plantilla desconocida: {pid}.")
    pl = PLANTILLAS[pid]
    faltan = [n for n, e, ej in pl.parametros if not params.get(n, "").strip() and not _opcional(pid, n)]
    if faltan:
        raise NoAplica("Faltan datos: " + ", ".join(faltan) + ".")
    m = pl.construir(params)
    res = Resultado(f"problema: {pl.titulo}")
    try:
        ed = leer_ed(m.ed)
    except ErrorLectura as exc:
        raise NoAplica(f"No pude leer el modelo «{m.ed}»: {exc}") from exc
    res.pasos.append(Paso("Plantear el modelo", pl.titulo, "", latex(ed.lhs) + " = " + latex(ed.rhs),
                          m.explicacion + " Datos: " + "; ".join(f"${latex(c.valor)}$ en $x={latex(c.x0)}$" if c.orden == 0 else
                                                                  f"$y'$ en $x={latex(c.x0)}$ vale ${latex(c.valor)}$"
                                                                  for c in leer_condiciones(", ".join(m.datos)))))
    sub = resolver(ed, None, None)
    if sub.metodo == "ninguno" or sub.valor is None:
        raise NoAplica("El modelo no se resolvió con los métodos del temario.")
    for pa in sub.pasos:
        res.pasos.append(Paso("Resolver la ED: " + pa.titulo, pa.regla, pa.antes_latex, pa.despues_latex, pa.explicacion, pa.discrepancia))
    res.advertencias += sub.advertencias
    v = sub.valor
    f = v.der if isinstance(v, Solucion) and v.explicita else (v if isinstance(v, sp.Expr) else None)
    if f is None:
        raise NoAplica("La solución del modelo no quedó en forma explícita y(x); no puedo contestar con ella.")
    # datos -> constantes e incógnitas
    desconocidas = [s for s in f.free_symbols if s != x and s.name.startswith("C")] + [sp.Symbol(n) for n in m.incognitas]
    ecs = []
    for c in leer_condiciones(", ".join(m.datos)):
        ecs.append(sp.diff(f, x, c.orden).subs(x, c.x0) - c.valor)
    todos = set().union(*[e.free_symbols for e in ecs]) - {x}
    todos |= set(desconocidas)
    rep = {s: (sp.Symbol(s.name, real=True) if s in desconocidas else sp.Symbol(s.name, positive=True)) for s in todos}
    ecs_p = [e.subs(rep) for e in ecs]
    desc_p = [rep.get(s, s) for s in desconocidas]
    simbolos_param = todos
    try:
        sol = sp.solve(ecs_p, desc_p, dict=True)
    except Exception:
        sol = []
    if not sol:
        sol = _eliminar(ecs_p, desc_p)
    if not sol:
        raise NoAplica("Los datos no permiten determinar las constantes (revisa los valores).")
    sol = sol[0]
    sol = {k: sp.simplify(v) for k, v in sol.items()}
    res.pasos.append(Paso("Usar los datos para hallar las constantes", "reemplazar los datos en la solución general", "",
                          r"\ ;\quad ".join(f"{latex(k)} = {latex(vv)}" for k, vv in sol.items()),
                          "Los valores iniciales dan las constantes; el dato extra da la constante del modelo."))
    fp = f.subs({s: rep.get(s, sp.Symbol(s.name, positive=True)) for s in f.free_symbols - {x}}).subs(sol)
    res.pasos.append(Paso("Solución del problema", "solución particular", "", "y = " + latex(sp.simplify(fp))))
    res.valor = sp.simplify(fp)
    # preguntas
    t = sp.Symbol("t_", positive=True)
    for tipo, etiqueta, arg in m.preguntas:
        try:
            if tipo == "valor":
                a, _ = _positivos(leer_expresion(arg), set())
                val = sp.simplify(fp.subs(x, a))
            elif tipo == "limite":
                val = sp.simplify(sp.limit(fp, x, sp.oo))
            else:  # tiempo
                objetivo = leer_expresion(arg)
                objetivo, _ = _positivos(objetivo, objetivo.free_symbols)
                raices = [r for r in sp.solve(sp.Eq(fp.subs(x, t), objetivo), t) if r.is_real is not False]
                val = sp.simplify(raices[0]) if raices else None
        except Exception:
            val = None
        if val is None:
            res.advertencias.append(f"No pude calcular: {etiqueta}.")
            continue
        res.respuestas.append({"etiqueta": etiqueta, "latex": latex(val), "aprox": _aprox(val)})
        res.pasos.append(Paso("Responder: " + etiqueta, "", "", latex(val) + (r" \approx " + _aprox(val) if _aprox(val) and not val.is_Integer else "")))
    res.solucion = "y = " + latex(sp.simplify(fp))
    res.verificacion = Verificacion(bool(sub.verificacion and sub.verificacion.ok), "la solución general se verificó en la ED del modelo")
    return res


def _eliminar(ecs, incognitas):
    """Resuelve ecuación por ecuación (una incógnita a la vez) cuando sp.solve no puede con el sistema."""
    ecs, hallado, pendientes = list(ecs), {}, list(incognitas)
    for _ in range(len(incognitas) + 1):
        for e in ecs:
            libres = [u for u in pendientes if e.has(u)]
            if len(libres) != 1:
                continue
            try:
                raices = sp.solve(e, libres[0])
            except Exception:
                continue
            if raices:
                v = sp.simplify(raices[0])
                hallado[libres[0]] = v
                pendientes.remove(libres[0])
                ecs = [sp.simplify(q.subs(libres[0], v)) for q in ecs]
                break
    if pendientes:
        return []
    for u in list(hallado):  # sustituir hacia atrás
        hallado[u] = sp.simplify(hallado[u].subs(hallado))
    return [hallado]


def _opcional(pid: str, nombre: str) -> bool:
    return nombre in {"k", "objetivo", "t2", "F"} or (pid == "crecimiento" and nombre in {"P1", "t1"})
