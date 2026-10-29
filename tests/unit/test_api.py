from fastapi.testclient import TestClient

from edo.api.app import app

c = TestClient(app)


def test_leer():
    r = c.post("/leer", json={"entrada": "(D^2-3D+2)y=e^x"})
    assert r.status_code == 200 and r.json()["orden"] == 2 and r.json()["forma"] == "operador"


def test_error_lectura_es_422_en_español():
    r = c.post("/leer", json={"entrada": "y'=e^"})
    assert r.status_code == 422 and "exponente" in r.json()["error"]


def test_verificar():
    def v(ed, resp):
        return c.post("/verificar", json={"ed": ed, "respuesta": resp}).json()["verificacion"]["ok"]
    assert v("y'=3-2x", "y=3x-x^2")
    assert v("y'=3-2x", "y=3x-x^2+C")
    assert not v("y'=3-2x", "y=3x+x^2")
    assert v("(2xy+3)dy-y^2 dx=0", "x/y^2+1/y^3=C")


def test_resolver_aun_sin_solvers():
    assert c.post("/resolver", json={"entrada": "y'=x"}).status_code == 501


def test_pagina_estatica():
    assert "edo-solver" in c.get("/").text
