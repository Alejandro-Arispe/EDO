"""La función de Vercel (api/index.py) debe exponer la misma app y servir la página estática."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


def test_api_index_expone_la_app_y_la_pagina():
    ruta = Path(__file__).resolve().parents[2] / "api" / "index.py"
    espec = importlib.util.spec_from_file_location("api_index_vercel", ruta)
    modulo = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(modulo)
    c = TestClient(modulo.app)
    assert c.get("/salud").json() == {"ok": True}
    assert "edo-solver" in c.get("/").text
    r = c.post("/resolver", json={"entrada": "y'=2y"}).json()
    assert r["verificacion"]["ok"]
