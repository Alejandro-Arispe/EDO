"""API local. Sin internet ni base de datos."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..calculo.derivadas import derivar
from ..conceptos.clasificacion import clasificar as clasificar_ed
from ..conceptos.constantes import clasificar_solucion, determinar_constantes
from ..conceptos.desde_raices import desde_raices, leer_raices
from ..conceptos.verificacion import verificar_solucion
from ..conceptos.wronskiano import analizar_dependencia
from ..core.lector_general import leer_general
from ..calculo.integrales import integrar
from ..calculo.resultado import ErrorCalculo
from ..core.lector import ED, ErrorLectura, leer_condiciones, leer_ed, leer_expresion, leer_relacion, x, ys
from ..core.verificador import verificar_explicita, verificar_implicita

WEB = Path(__file__).resolve().parents[3] / "web"

app = FastAPI(title="edo-solver")


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
def clasificar(p: Entrada):
    ed = _leer_cualquiera(p.entrada, p.latex)
    c = clasificar_ed(ed)
    # El clasificador de métodos de resolución llega con F3 en adelante.
    return {"lectura": _lectura(ed), "clasificacion": c.to_dict(), "pasos": [s.to_dict() for s in c.pasos],
            "metodos": []}


@app.post("/resolver")
def resolver(p: PedidoResolver):
    ed = leer_ed(p.entrada, latex=p.latex)
    conds = leer_condiciones(p.condiciones) if p.condiciones else []
    return JSONResponse(status_code=501, content={
        "error": "Todavía no hay solvers instalados (se agregan desde la fase F3).",
        "lectura": ed.to_dict(), "condiciones": [c.to_dict() for c in conds]})


@app.post("/verificar")
def verificar(p: PedidoVerificar):
    ed = leer_ed(p.ed)
    izq, der = leer_relacion(p.respuesta, latex=p.latex)
    r = verificar_solucion(ed, izq, der)
    return {"lectura": ed.to_dict(), "verificacion": r.verificacion.to_dict(), "pasos": [s.to_dict() for s in r.pasos],
            "solucion": r.solucion}


class PedidoConstantes(BaseModel):
    ed: str | None = None
    respuesta: str
    condiciones: str


@app.post("/conceptos/constantes")
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
def conceptos_dependencia(p: PedidoLista):
    funcs = [leer_expresion(t) for t in _partir_lista(p.entrada)]
    try:
        return analizar_dependencia(funcs, mismo_ed=p.mismo_ed).to_dict()
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})


@app.post("/conceptos/raices")
def conceptos_raices(p: Entrada):
    return desde_raices(leer_raices(p.entrada)).to_dict()


class PedidoCalculo(Entrada):
    orden: int = 1


@app.post("/calculo/derivar")
def calculo_derivar(p: PedidoCalculo):
    try:
        r = derivar(leer_expresion(p.entrada, latex=p.latex), x, max(1, min(p.orden, 6)))
    except ErrorCalculo as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})
    return r.to_dict()


@app.post("/calculo/integrar")
def calculo_integrar(p: Entrada):
    return integrar(leer_expresion(p.entrada, latex=p.latex), x).to_dict()


if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
