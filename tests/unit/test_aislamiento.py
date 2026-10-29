"""El modo de servidor (EDO_AISLAR=1) resuelve cada petición en un proceso aparte con límite de tiempo."""
import time

import pytest
from fastapi.testclient import TestClient

from edo.api import aislamiento
from edo.api.app import app


@pytest.fixture()
def servidor_aislado(monkeypatch):
    monkeypatch.setenv("EDO_AISLAR", "1")
    monkeypatch.setenv("EDO_TIMEOUT", "20")
    monkeypatch.setattr(aislamiento, "_piscina", None)
    yield TestClient(app)
    p = aislamiento._piscina
    if p is not None:
        p.cerrar()
    monkeypatch.setattr(aislamiento, "_piscina", None)


def test_resuelve_en_un_trabajador_y_mata_lo_que_se_cuelga(servidor_aislado):
    c = servidor_aislado
    assert c.get("/salud").json() == {"ok": True}
    r = c.post("/resolver", json={"entrada": "y'+2y=x e^x"})
    assert r.status_code == 200 and r.json()["verificacion"]["ok"]
    # error de lectura: llega como 422 con el mensaje en español
    r = c.post("/resolver", json={"entrada": "y'=e^"})
    assert r.status_code == 422 and "exponente" in r.json()["error"]
    # 404/422 propios del endpoint también viajan bien
    assert c.post("/resolver", json={"entrada": "y'=3-2x", "metodo": "exacta2"}).status_code == 422
    # una potencia gigante cuelga a SymPy: se corta por tiempo y el servidor sigue vivo
    t0 = time.time()
    r = c.post("/resolver", json={"entrada": "y' = x^(9^9^9)"})
    assert r.status_code == 504 and "demasiado" in r.json()["error"]
    assert time.time() - t0 < 60
    r = c.post("/resolver", json={"entrada": "y'=3-2x", "condiciones": "y(1)=2"})
    assert r.status_code == 200 and r.json()["solucion"] == "y = - x^{2} + 3 x"
