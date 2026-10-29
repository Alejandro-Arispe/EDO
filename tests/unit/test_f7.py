import sympy as sp
from fastapi.testclient import TestClient

from edo.api.app import app
from edo.core.geogebra import comandos, expr
from edo.core.lector import leer_ed, x, ys
from edo.primer_orden.base import Solucion
from edo.resolutor import resolver

c = TestClient(app)


def test_expr_geogebra():
    assert set(expr(sp.log(x) + sp.sqrt(x) + sp.exp(2 * x) + sp.E).split(" + ")) == {"ln(x)", "sqrt(x)", "exp(2*x)", "e"}
    assert expr(x ** 2 / 2) == "x^2/2"
    assert set(expr(sp.Symbol("C1") * x + sp.Symbol("C")).split(" + ")) == {"c_1*x", "c"}


def test_comandos_explicita_implicita_parametrica():
    r = resolver(leer_ed("y'=3-2x"))
    cmd = comandos(r.valor, r.extra)
    assert cmd[0].startswith("c = Slider") and cmd[-1] == "f_1(x) = c - x^2 + 3*x"
    r = resolver(leer_ed("(1+e^(x/y))dx+e^(x/y)(1-x/y)dy=0"))
    assert comandos(r.valor)[-1] == "x + y*exp(x/y) = c"
    r = resolver(leer_ed("y=2xy'+y'^2+1"))
    cmd = comandos(r.valor, r.extra)
    assert any(l.startswith("Curve(") for l in cmd) and "f_1(x) = 1" in cmd
    r = resolver(leer_ed("y''+4y=3x^3"))
    assert [l for l in comandos(r.valor) if "Slider" in l] == ["c_1 = Slider(-5, 5, 0.1)", "c_2 = Slider(-5, 5, 0.1)"]


def test_api_resolver_incluye_geogebra_y_verificar_tipo():
    r = c.post("/resolver", json={"entrada": "y'=2y"}).json()
    assert r["geogebra"] and "Slider" in r["geogebra"][0]
    v = c.post("/verificar", json={"ed": "y'=2y", "respuesta": "y=C e^(2x)"}).json()
    assert v["verificacion"]["ok"] and "general" in v["tipo"]
    v = c.post("/verificar", json={"ed": "y'=2y", "respuesta": "y=e^(3x)"}).json()
    assert not v["verificacion"]["ok"] and "tipo" not in v
    v = c.post("/verificar", json={"ed": "y''+y=0", "respuesta": "y=C1 cos x + C2 sen x"}).json()
    assert v["verificacion"]["ok"] and "general" in v["tipo"]


def test_la_pagina_trae_historial_pdf_y_geogebra():
    html = c.get("/").text
    for clave in ("tab-historial", "btn-pdf", "btn-gg", "salida-revisar"):
        assert clave in html
    assert "@media print" in c.get("/style.css").text


def test_la_pagina_trae_el_teclado_y_sus_teclas_se_leen_bien():
    """Cada tecla del teclado debe producir algo que el lector entienda dentro de una ecuación."""
    import re
    from pathlib import Path
    from edo.core.lector import leer_expresion
    html = c.get("/").text
    assert 'id="teclado"' in html and 'id="btn-teclado"' in html
    js = (Path(__file__).resolve().parents[2] / "web" / "app.js").read_text(encoding="utf-8")
    snippets = re.findall(r'\["[^"]+", "([^"]*)", "[^"]*"\]', js[js.index("const TECLAS"):js.index("let ultimoCampo")])
    assert len(snippets) >= 40
    for s in snippets:
        if s.strip() in {"=", "*", "?", "y'", "y''", "y'''", "dx", "dy", "D", "C1", "dy/dx", "d^2y/dx^2", "D^2"} or s.startswith(("y^", "y(", "y'(", "(D-")):
            continue                       # fragmentos de ED: se prueban dentro de una ecuación
        e = s.replace("|", "x")
        if e.startswith("^"):
            e = "x" + e
        if e == "(x)/()":
            e = "(x)/(2)"
        if e.startswith("(x)^(1/n)"):
            e = "(x)^(1/3)"
        if e.startswith("x^(x/)"):
            e = "x^(1/2)"
        assert leer_expresion(e) is not None, s
