import json

import pytest
import sympy as sp
from fastapi.testclient import TestClient

from edo import ia, problemas
from edo.api.app import app
from edo.core.lector import leer_ed
from edo.grafica import series
from edo.primer_orden.base import NoAplica
from edo.resolutor import resolver

c = TestClient(app)


# ----------------------------------------------------------------- plantillas
def test_bacterias_triplicar_III_evaluacion():
    r = problemas.resolver_plantilla("crecimiento", {"P0": "P0", "P1": "3/2*P0", "t1": "1", "objetivo": "3*P0"})
    assert r.verificacion.ok
    assert abs(float(r.respuestas[0]["aprox"]) - 2.71) < 0.01      # III Evaluación: 2.71 horas
    assert any(p.titulo.startswith("Resolver la ED") for p in r.pasos)


def test_enfriamiento_newton():
    r = problemas.resolver_plantilla("enfriamiento", {"Tm": "20", "T0": "100", "T1": "60", "t1": "10", "t2": "20", "objetivo": "30"})
    assert [a["aprox"] for a in r.respuestas] == ["40", "30"]


def test_circuito_mezcla_logistico_caida_resorte():
    r = problemas.resolver_plantilla("circuito_rl", {"L": "1", "R": "2", "E": "10", "i0": "0", "t2": "1"})
    assert r.respuestas[-1]["aprox"] == "5"
    r = problemas.resolver_plantilla("mezcla", {"V0": "100", "qe": "5", "ce": "2", "qs": "5", "A0": "0", "t2": "10"})
    assert abs(float(r.respuestas[0]["aprox"]) - 200 * (1 - float(sp.exp(-sp.Rational(1, 2))))) < 1e-3
    r = problemas.resolver_plantilla("logistico", {"a": "1", "b": "1/100", "P0": "10"})
    assert r.respuestas[-1]["aprox"] == "100"
    r = problemas.resolver_plantilla("caida", {"m": "2", "g": "9.8", "k": "4", "v0": "0"})
    assert r.respuestas[-1]["aprox"] == "4.9"
    r = problemas.resolver_plantilla("resorte", {"m": "1", "c": "0", "k": "4", "F": "0", "x0": "1", "v0": "0", "t2": "1"})
    assert abs(float(r.respuestas[0]["aprox"]) - float(sp.cos(2))) < 1e-4


def test_plantilla_errores_claros():
    with pytest.raises(NoAplica):
        problemas.resolver_plantilla("no_existe", {})
    with pytest.raises(NoAplica):
        problemas.resolver_plantilla("enfriamiento", {"Tm": "20"})


def test_api_plantillas():
    lista = c.get("/problema/plantillas").json()
    assert {"crecimiento", "enfriamiento", "resorte"} <= {p["id"] for p in lista}
    r = c.post("/problema/plantilla", json={"id": "enfriamiento", "parametros": {
        "Tm": "20", "T0": "100", "T1": "60", "t1": "10", "t2": "20"}}).json()
    assert r["respuestas"][0]["aprox"] == "40"
    assert c.post("/problema/plantilla", json={"id": "x", "parametros": {}}).status_code == 422


def test_nombres_con_subindice_son_un_solo_simbolo():
    from edo.core.lector import leer_expresion
    assert leer_expresion("3/2*P0") == sp.Rational(3, 2) * sp.Symbol("P0")


# ------------------------------------------------------------------------- IA
class _Resp:
    def __init__(self, texto):
        self._t = texto

    def read(self):
        return json.dumps({"content": [{"type": "text", "text": self._t}]}).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_ia_apagada_sin_clave(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert c.get("/problema/ia/estado").json()["disponible"] is False
    r = c.post("/problema/ia/proponer", json={"enunciado": "hola", "confirmo_envio": True})
    assert r.status_code == 503 and "ANTHROPIC_API_KEY" in r.json()["error"]


def test_ia_exige_confirmacion(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    llamadas = []
    monkeypatch.setattr(ia.urllib.request, "urlopen", lambda *a, **k: llamadas.append(1))
    r = c.post("/problema/ia/proponer", json={"enunciado": "algo", "confirmo_envio": False})
    assert r.status_code == 400 and not llamadas


def test_ia_propuesta_validada_y_no_resuelve(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    visto = {}

    def falso(req, timeout=0):
        visto["cuerpo"] = json.loads(req.data)
        visto["clave"] = req.headers.get("X-api-key")
        return _Resp('```json\n{"ed": "y\' = k*y", "condiciones": "y(0)=100", "interpretacion": "crece exponencial", '
                     '"pregunta": "tiempo", "supuestos": ["k constante"]}\n```')
    monkeypatch.setattr(ia.urllib.request, "urlopen", falso)
    r = c.post("/problema/ia/proponer", json={"enunciado": "Una población crece proporcional a su tamaño", "confirmo_envio": True}).json()
    assert r["valida"] and r["ed"] == "y' = k*y" and r["condiciones"] == "y(0)=100"
    assert visto["clave"] == "clave-de-prueba" and visto["cuerpo"]["messages"][0]["content"].startswith("Una población")
    assert "solucion" not in r and "pasos" not in r            # solo propone: nunca resuelve


def test_ia_propuesta_ilegible_se_marca(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(ia.urllib.request, "urlopen", lambda req, timeout=0: _Resp('{"ed": "y\'\' +* 3", "condiciones": ""}'))
    r = ia.proponer("x")
    assert not r["valida"] and "corrígela" in r["error"].lower()


def test_ia_sin_internet(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")

    def falla(*a, **k):
        raise ia.urllib.error.URLError("sin red")
    monkeypatch.setattr(ia.urllib.request, "urlopen", falla)
    with pytest.raises(ia.ErrorIA) as e:
        ia.proponer("algo")
    assert "sin internet" in str(e.value)


# ------------------------------------------------------------------- gráficas
def test_grafica_explicita_familia():
    s = series(resolver(leer_ed("y'=3-2x")), -3, 3, -5, 5)
    assert len(s) == 5 and all(len(x_["segmentos"]) >= 1 for x_ in s)
    seg = s[2]["segmentos"][0]
    pt = seg[len(seg) // 2]
    assert abs(pt[1] - (3 * pt[0] - pt[0] ** 2)) < 1e-6          # C = 0


def test_grafica_implicita_y_parametrica_y_singular():
    s = series(resolver(leer_ed("(2xy+3)dy - y^2 dx = 0")), -3, 3, -3, 3, [1])
    assert s and s[0]["segmentos"]
    s = series(resolver(leer_ed("y = x y' + y'^2")), -4, 4, -6, 2, [-1, 0, 1])
    assert any(o["singular"] for o in s) and len(s) == 4
    s = series(resolver(leer_ed("y = 2x y' + y'^2 + 1")), -4, 4, -4, 4, [1])
    assert any(o["segmentos"] for o in s)


def test_api_grafica():
    r = c.post("/grafica", json={"entrada": "y'=2y", "familia": "-1, 1"}).json()
    assert len(r["series"]) == 2 and r["series"][0]["segmentos"]
    assert c.post("/grafica", json={"entrada": "y'=2y", "xmin": 3, "xmax": 1}).status_code == 422
    assert c.post("/grafica", json={"entrada": "y'=2y", "familia": "a,b"}).status_code == 422


def test_el_javascript_de_la_web_tiene_sintaxis_valida():
    """Un error de sintaxis en app.js deja la web muerta (pasó en F7); se revisa con node si está instalado."""
    import shutil
    import subprocess
    from pathlib import Path
    node = shutil.which("node")
    if node is None:
        pytest.skip("node no está instalado")
    js = Path(__file__).resolve().parents[2] / "web" / "app.js"
    r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
