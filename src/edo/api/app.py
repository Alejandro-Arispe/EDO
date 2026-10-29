"""API local. Sin internet ni base de datos."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..core.lector import ED, ErrorLectura, leer_condiciones, leer_ed, leer_relacion, ys
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


@app.post("/clasificar")
def clasificar(p: Entrada):
    ed = leer_ed(p.entrada, latex=p.latex)
    # El clasificador de métodos llega con F2 en adelante.
    return {"lectura": ed.to_dict(), "metodos": [],
            "mensaje": "Todavía no hay solvers instalados (se agregan desde la fase F2)."}


@app.post("/resolver")
def resolver(p: PedidoResolver):
    ed = leer_ed(p.entrada, latex=p.latex)
    conds = leer_condiciones(p.condiciones) if p.condiciones else []
    return JSONResponse(status_code=501, content={
        "error": "Todavía no hay solvers instalados (se agregan desde la fase F2).",
        "lectura": ed.to_dict(), "condiciones": [c.to_dict() for c in conds]})


def _verificar(ed: ED, respuesta: str, latex: bool):
    izq, der = leer_relacion(respuesta, latex=latex)
    if izq == ys and ys not in der.free_symbols:
        return verificar_explicita(ed, der)
    return verificar_implicita(ed, izq, der)


@app.post("/verificar")
def verificar(p: PedidoVerificar):
    ed = leer_ed(p.ed)
    v = _verificar(ed, p.respuesta, p.latex)
    return {"lectura": ed.to_dict(), "verificacion": v.to_dict()}


if WEB.is_dir():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
