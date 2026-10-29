"""Traducción OPCIONAL de un problema escrito a ED usando la API de Anthropic.

Reglas:
  * Está apagada si no hay la variable de entorno ANTHROPIC_API_KEY (el programa sigue siendo
    100 % local sin ella).
  * Solo envía el texto del enunciado, y solo cuando el usuario lo confirma en la interfaz.
  * Nunca resuelve nada: devuelve una PROPUESTA (ED y condiciones) que el usuario revisa,
    edita y confirma antes de que los métodos del programa la resuelvan.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from .core.lector import ErrorLectura, leer_condiciones, leer_ed

URL = "https://api.anthropic.com/v1/messages"
MODELO_POR_DEFECTO = "claude-sonnet-5-5"

SISTEMA = """Eres un asistente que traduce problemas de ecuaciones diferenciales escritos en español a la notación de entrada de un programa.
Responde SOLO con un objeto JSON (sin texto antes ni después, sin bloques de código) con estas claves:
  "ed": la ecuación diferencial usando x como variable independiente (el tiempo se llama x) e y como función incógnita.
        Ejemplos válidos: "y' = k*y", "2*y'' + 2*y' + y = 4*sqrt(x)", "(x+y)dx - (x-y)dy = 0".
        Funciones: sen, cos, tg, ln, sqrt, e^( ). Usa solo letras simples para constantes del modelo (k, m, g, ...).
  "condiciones": las condiciones iniciales o datos como texto, por ejemplo "y(0)=100, y(2)=300" (cadena vacía si no hay).
  "interpretacion": una explicación breve en español de cómo armaste el modelo y qué significan x e y.
  "pregunta": qué pide el problema (en español).
  "supuestos": lista de supuestos o datos que faltan y que el usuario debe confirmar.
Si el enunciado no se puede modelar con una ecuación diferencial ordinaria, responde {"ed": "", "condiciones": "", "interpretacion": "motivo", "pregunta": "", "supuestos": []}."""


class ErrorIA(RuntimeError):
    """Error al usar la API (mensaje en español)."""


def disponible() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _extraer_json(texto: str) -> dict:
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    i, j = texto.find("{"), texto.rfind("}")
    if i < 0 or j < i:
        raise ErrorIA("La respuesta de la IA no tuvo el formato esperado (JSON).")
    try:
        return json.loads(texto[i:j + 1])
    except json.JSONDecodeError as exc:
        raise ErrorIA(f"La respuesta de la IA no es un JSON válido: {exc}") from exc


def proponer(enunciado: str, timeout: float = 45.0) -> dict:
    """Pide a la IA una propuesta de ED. Devuelve el diccionario validado (la ED se lee con el lector del programa)."""
    if not disponible():
        raise ErrorIA("La función de IA está apagada: define la variable de entorno ANTHROPIC_API_KEY para activarla.")
    enunciado = enunciado.strip()
    if not enunciado:
        raise ErrorIA("Escribe el enunciado del problema.")
    if len(enunciado) > 4000:
        raise ErrorIA("El enunciado es demasiado largo (máximo 4000 caracteres).")
    cuerpo = json.dumps({
        "model": os.environ.get("EDO_MODELO", MODELO_POR_DEFECTO),
        "max_tokens": 800,
        "system": SISTEMA,
        "messages": [{"role": "user", "content": enunciado}],
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=cuerpo, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": os.environ["ANTHROPIC_API_KEY"].strip(),
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            datos = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ErrorIA(f"La API respondió con error {exc.code}. Revisa tu clave y tu saldo.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ErrorIA("No pude conectar con la API (¿sin internet?). El resto del programa sigue funcionando sin conexión.") from exc
    try:
        texto = "".join(b.get("text", "") for b in datos["content"] if b.get("type") == "text")
    except (KeyError, TypeError) as exc:
        raise ErrorIA("La respuesta de la API no tiene el formato esperado.") from exc
    p = _extraer_json(texto)
    out = {k: p.get(k, "" if k != "supuestos" else []) for k in ("ed", "condiciones", "interpretacion", "pregunta", "supuestos")}
    out["valida"], out["error"] = True, ""
    if not str(out["ed"]).strip():
        out["valida"], out["error"] = False, "La IA no pudo modelar el problema con una ecuación diferencial."
        return out
    try:
        leer_ed(str(out["ed"]))
        if str(out["condiciones"]).strip():
            leer_condiciones(str(out["condiciones"]))
    except ErrorLectura as exc:
        out["valida"], out["error"] = False, f"El programa no pudo leer la propuesta: {exc}. Corrígela a mano antes de resolver."
    return out
