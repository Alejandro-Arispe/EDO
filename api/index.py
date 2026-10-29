"""Punto de entrada para Vercel (función Python): expone la app FastAPI de edo-solver.

Vercel instala las dependencias de requirements.txt; el código del proyecto vive en src/, así que se añade
al path antes de importarlo. Las páginas estáticas (web/) las sirve la propia app.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "src"))
os.environ.setdefault("EDO_WEB", os.path.join(RAIZ, "web"))

from edo.api.app import app  # noqa: E402,F401  (Vercel busca la variable «app»)
