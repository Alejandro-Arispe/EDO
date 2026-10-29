"""python -m edo: arranca el servidor local y abre el navegador.

En un servidor (Render) se arranca con ``uvicorn edo.api.app:app --host 0.0.0.0 --port $PORT``; si se usa
``python -m edo`` con la variable PORT definida, escucha en 0.0.0.0 y no abre el navegador.
"""
import os
import threading
import webbrowser

import uvicorn


def main() -> None:
    puerto = int(os.environ.get("PORT", "8000"))
    en_servidor = "PORT" in os.environ
    if not en_servidor:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{puerto}")).start()
    uvicorn.run("edo.api.app:app", host="0.0.0.0" if en_servidor else "127.0.0.1", port=puerto, log_level="warning")


if __name__ == "__main__":
    main()
