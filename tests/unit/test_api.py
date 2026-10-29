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


def test_resolver_sin_derivadas_es_422():
    r = c.post("/resolver", json={"entrada": "y = x^2"})
    assert r.status_code == 422 and "no es una ecuación diferencial" in r.json()["error"]


def test_pagina_estatica():
    assert "edo-solver" in c.get("/").text


def test_calculo_derivar_e_integrar():
    r = c.post("/calculo/derivar", json={"entrada": "x^2 sen x"}).json()
    assert r["verificacion"]["ok"] and r["pasos"]
    r = c.post("/calculo/integrar", json={"entrada": "x e^x"}).json()
    assert r["verificacion"]["ok"] and r["resultado_latex"].endswith("+ C")
    r = c.post("/calculo/integrar", json={"entrada": "e^(x^2)"}).json()
    assert r["elemental"] is False and r["advertencias"]


def test_resolver_primer_orden_y_forzar_metodo():
    r = c.post("/resolver", json={"entrada": "(2xy+3)dy - y^2 dx = 0"}).json()
    assert r["metodo"] == "lineal en x" and r["verificacion"]["ok"]
    r = c.post("/resolver", json={"entrada": "y'=3-2x", "condiciones": "y(1)=2"}).json()
    assert r["solucion"] == "y = - x^{2} + 3 x"
    r = c.post("/resolver", json={"entrada": "(1+e^(x/y))dx + e^(x/y)(1-x/y)dy = 0", "metodo": "homogenea_xy",
                                  "condiciones": "y(1)=1"}).json()
    assert r["verificacion"]["ok"] and any(p["discrepancia"] and "A5" in p["discrepancia"] for p in r["pasos"])
    mal = c.post("/resolver", json={"entrada": "y'=3-2x", "metodo": "exacta2"})
    assert mal.status_code == 422
    nada = c.post("/resolver", json={"entrada": "y'=x^2+y^2"}).json()
    assert nada["metodo"] == "ninguno" and not nada["pasos"]
    k = c.post("/clasificar", json={"entrada": "y' = y/x"}).json()
    assert k["metodos"] and k["metodos"][0]["metodo"] == "separable"
