"""API local. Sin internet ni base de datos."""
from __future__ import annotations

import functools
import json
import os
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import aislamiento
from ..calculo.derivadas import derivar
from ..conceptos.clasificacion import clasificar as clasificar_ed
from ..conceptos.constantes import clasificar_solucion, determinar_constantes
from ..conceptos.desde_raices import desde_raices, leer_raices
from ..conceptos.verificacion import verificar_solucion
from ..conceptos.wronskiano import analizar_dependencia
from .. import ia, problemas, tramos as tramos_mod
from ..grafica import series as series_grafica
from ..core.geogebra import comandos as comandos_geogebra
from ..core.lector_general import leer_general
from ..primer_orden.base import NoAplica
from ..resolutor import clasificar_metodos, resolver as resolver_primer_orden
from ..calculo.integrales import integrar
from ..calculo.resultado import ErrorCalculo
from ..core.lector import ED, ErrorLectura, leer_condiciones, leer_ed, leer_expresion, leer_relacion, x, ys
from ..core.verificador import verificar_explicita, verificar_implicita

def _carpeta_web() -> Path:
    """web/ junto al código (instalación editable) o, si no, en el directorio de trabajo; EDO_WEB la fuerza."""
    candidatas = [Path(os.environ["EDO_WEB"])] if os.environ.get("EDO_WEB") else []
    candidatas += [Path(__file__).resolve().parents[3] / "web", Path.cwd() / "web"]
    return next((c for c in candidatas if (c / "index.html").is_file()), candidatas[-1])


WEB = _carpeta_web()

app = FastAPI(title="edo-solver")


def empaquetar(res):
    """Resultado de un endpoint -> mensaje simple que viaja por la tubería del trabajador."""
    if isinstance(res, JSONResponse):
        return ("resp", res.status_code, json.loads(res.body))
    return ("ok", jsonable_encoder(res))


def aislado(fn):
    """Con EDO_AISLAR=1 el endpoint se resuelve en un proceso trabajador con límite de tiempo y memoria."""
    @functools.wraps(fn)
    def envoltura(p):
        if not aislamiento.activo():
            return fn(p)
        try:
            msg = aislamiento.piscina().ejecutar(fn.__name__, type(p).__name__, p.model_dump())
        except aislamiento.TiempoAgotado:
            return JSONResponse(status_code=504, content={"error": "La ecuación tardó demasiado en resolverse (límite de tiempo). "
                                                                     "Prueba con una forma más simple o resuélvela en tu equipo."})
        except aislamiento.Ocupado:
            return JSONResponse(status_code=503, content={"error": "El servidor está ocupado resolviendo otras ecuaciones. Inténtalo en unos segundos."})
        if msg[0] == "ok":
            return msg[1]
        if msg[0] == "resp":
            return JSONResponse(status_code=msg[1], content=msg[2])
        if msg[1] == "ErrorLectura":
            raise ErrorLectura(msg[2])
        raise HTTPException(status_code=500, detail=f"Error interno al resolver ({msg[1]}).")
    return envoltura


@app.on_event("startup")
def _calentar_trabajador():
    if aislamiento.activo():
        threading.Thread(target=aislamiento.piscina().calentar, daemon=True).start()


@app.get("/salud")
def salud():
    return {"ok": True}


class Entrada(BaseModel):
    entrada: str
    latex: bool = False  # la entrada viene de MathLive (LaTeX)


class PedidoResolver(Entrada):
    metodo: str | None = None
    condiciones: str | None = None


class PedidoVerificar(BaseModel):
    ed: str
    respuesta: str
    latex: bool = False


@app.exception_handler(ErrorLectura)
async def _error_lectura(_, exc: ErrorLectura):
    return JSONResponse(status_code=422, content={"error": str(exc)})


@app.post("/leer")
@aislado
def leer(p: Entrada):
    return leer_ed(p.entrada, latex=p.latex).to_dict()


def _leer_cualquiera(entrada: str, latex: bool = False):
    """ED en y(x) si se puede; si no tiene derivadas de y, la lectura general (otras variables, parciales)."""
    try:
        ed = leer_ed(entrada, latex=latex)
        if ed.orden > 0:
            return ed
    except ErrorLectura:
        pass
    return leer_general(entrada, latex=latex)


def _lectura(ed) -> dict:
    if isinstance(ed, ED):
        return ed.to_dict()
    from ..core.latex import latex as ltx
    return {"original": ed.original, "forma": "general", "orden": ed.orden, "tipo": ed.tipo,
            "latex": f"{ltx(ed.lhs)} = {ltx(ed.rhs)}", "notas": []}


@app.post("/clasificar")
@aislado
def clasificar(p: Entrada):
    ed = _leer_cualquiera(p.entrada, p.latex)
    c = clasificar_ed(ed)
    metodos = clasificar_metodos(ed) if isinstance(ed, ED) else []
    return {"lectura": _lectura(ed), "clasificacion": c.to_dict(), "pasos": [s.to_dict() for s in c.pasos],
            "metodos": metodos}


@app.post("/resolver")
@aislado
def resolver(p: PedidoResolver):
    ed = leer_ed(p.entrada, latex=p.latex)
    conds = leer_condiciones(p.condiciones) if p.condiciones and p.condiciones.strip() else []
    try:
        r = resolver_primer_orden(ed, p.metodo or None, conds)
    except NoAplica as exc:
        return JSONResponse(status_code=422, content={"error": str(exc), "lectura": ed.to_dict()})
    d = r.to_dict()
    d["lectura"] = ed.to_dict()
    d["condiciones"] = [c.to_dict() for c in conds]
    try:
        d["geogebra"] = comandos_geogebra(r.valor, r.extra) if r.valor is not None else []
    except Exception:
        d["geogebra"] = []
    return d


@app.post("/verificar")
@aislado
def verificar(p: PedidoVerificar):
    ed = leer_ed(p.ed)
    izq, der = leer_relacion(p.respuesta, latex=p.latex)
    r = verificar_solucion(ed, izq, der)
    out = {"lectura": ed.to_dict(), "verificacion": r.verificacion.to_dict(), "pasos": [s.to_dict() for s in r.pasos],
           "solucion": r.solucion}
    if r.verificacion.ok:
        try:
            out["tipo"] = clasificar_solucion(ed, izq, der).pasos[-1].explicacion
        except Exception:
            pass
    return out


class PedidoConstantes(BaseModel):
    ed: str | None = None
    respuesta: str
    condiciones: str


@app.post("/conceptos/constantes")
@aislado
def conceptos_constantes(p: PedidoConstantes):
    ed = leer_ed(p.ed) if p.ed and p.ed.strip() else None
    izq, der = leer_relacion(p.respuesta)
    try:
        r = determinar_constantes(ed, izq, der, leer_condiciones(p.condiciones))
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return r.to_dict()


class PedidoTipo(BaseModel):
    ed: str
    respuesta: str
    general: str | None = None


@app.post("/conceptos/tipo_solucion")
@aislado
def conceptos_tipo(p: PedidoTipo):
    izq, der = leer_relacion(p.respuesta)
    gen = leer_relacion(p.general) if p.general and p.general.strip() else None
    return clasificar_solucion(leer_ed(p.ed), izq, der, gen).to_dict()


class PedidoLista(BaseModel):
    entrada: str
    mismo_ed: bool = False


def _partir_lista(s: str) -> list[str]:
    sep = ";" if ";" in s else ","
    trozos, nivel, actual = [], 0, ""
    for ch in s:
        nivel += (ch in "([{") - (ch in ")]}")
        if ch == sep and nivel == 0:
            trozos.append(actual)
            actual = ""
        else:
            actual += ch
    trozos.append(actual)
    return [t.strip() for t in trozos if t.strip()]


@app.post("/conceptos/dependencia")
@aislado
def conceptos_dependencia(p: PedidoLista):
    funcs = [leer_expresion(t) for t in _partir_lista(p.entrada)]
    try:
        return analizar_dependencia(funcs, mismo_ed=p.mismo_ed).to_dict()
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})


@app.post("/conceptos/raices")
@aislado
def conceptos_raices(p: Entrada):
    return desde_raices(leer_raices(p.entrada)).to_dict()


class PedidoCalculo(Entrada):
    orden: int = 1


_NO_SOPORTADO = ("Escribe solo la función (por ejemplo x^2 sen x), sin ∫, sin dx y sin «Integral(...)»: "
                 "las integrales definidas, las integrales dobles y las derivadas parciales todavía no están disponibles.")


def _revisar_calculo(entrada: str):
    import re
    if re.search(r"(?i)integral|∫|\\int|(?<![A-Za-z])d[xy](?![A-Za-z])|∂|partial", entrada):
        return JSONResponse(status_code=422, content={"error": _NO_SOPORTADO})
    return None


@app.post("/calculo/derivar")
@aislado
def calculo_derivar(p: PedidoCalculo):
    if (mal := _revisar_calculo(p.entrada)) is not None:
        return mal
    try:
        r = derivar(leer_expresion(p.entrada, latex=p.latex), x, max(1, min(p.orden, 6)))
    except ErrorCalculo as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return r.to_dict()


@app.post("/calculo/integrar")
@aislado
def calculo_integrar(p: Entrada):
    if (mal := _revisar_calculo(p.entrada)) is not None:
        return mal
    return integrar(leer_expresion(p.entrada, latex=p.latex), x).to_dict()


# ------------------------------------------------------------- ecuaciones por tramos
class Tramo(BaseModel):
    ed: str
    desde: str
    hasta: str


class PedidoTramos(BaseModel):
    tramos: list[Tramo]
    condiciones: str


@app.post("/tramos")
@aislado
def tramos(p: PedidoTramos):
    try:
        r = tramos_mod.resolver_por_tramos([t.model_dump() for t in p.tramos], p.condiciones)
    except NoAplica as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    d = r.to_dict()
    try:
        d["geogebra"] = []
    except Exception:
        pass
    return d


# ---------------------------------------------------------------- problemas escritos
@app.get("/problema/plantillas")
def problema_plantillas():
    return [{"id": pl.id, "titulo": pl.titulo, "descripcion": pl.descripcion,
             "parametros": [{"nombre": n, "etiqueta": e, "ejemplo": ej} for n, e, ej in pl.parametros]}
            for pl in problemas.PLANTILLAS.values()]


class PedidoPlantilla(BaseModel):
    id: str
    parametros: dict[str, str] = {}


@app.post("/problema/plantilla")
@aislado
def problema_plantilla(p: PedidoPlantilla):
    try:
        r = problemas.resolver_plantilla(p.id, p.parametros)
    except NoAplica as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return r.to_dict()


@app.get("/problema/ia/estado")
def problema_ia_estado():
    return {"disponible": ia.disponible(),
            "aviso": "El enunciado se envía a la API de Anthropic solo si lo confirmas. Sin la variable ANTHROPIC_API_KEY esta función está apagada."}


class PedidoIA(BaseModel):
    enunciado: str
    confirmo_envio: bool = False


@app.post("/problema/ia/proponer")
@aislado
def problema_ia_proponer(p: PedidoIA):
    if not p.confirmo_envio:
        return JSONResponse(status_code=400, content={"error": "Debes confirmar el envío del enunciado a la API antes de usar la IA."})
    try:
        return ia.proponer(p.enunciado)
    except ia.ErrorIA as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})


# ------------------------------------------------------------------------ gráfica
class PedidoGrafica(PedidoResolver):
    xmin: float = -5.0
    xmax: float = 5.0
    ymin: float = -5.0
    ymax: float = 5.0
    familia: str | None = None


@app.post("/grafica")
@aislado
def grafica(p: PedidoGrafica):
    ed = leer_ed(p.entrada, latex=p.latex)
    conds = leer_condiciones(p.condiciones) if p.condiciones and p.condiciones.strip() else []
    if not (p.xmin < p.xmax and p.ymin < p.ymax):
        return JSONResponse(status_code=422, content={"error": "El rango debe cumplir mín < máx."})
    try:
        r = resolver_primer_orden(ed, p.metodo or None, conds)
    except NoAplica as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    if r.valor is None:
        return JSONResponse(status_code=422, content={"error": "No hay solución que graficar."})
    fam = None
    if p.familia and p.familia.strip():
        try:
            fam = [float(v) for v in p.familia.replace(";", ",").split(",") if v.strip()][:12]
        except ValueError:
            return JSONResponse(status_code=422, content={"error": "La familia debe ser una lista de números, por ejemplo -2, -1, 0, 1, 2."})
    return {"series": series_grafica(r, p.xmin, p.xmax, p.ymin, p.ymax, fam), "solucion": r.solucion,
            "rango": {"xmin": p.xmin, "xmax": p.xmax, "ymin": p.ymin, "ymax": p.ymax}}


if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
