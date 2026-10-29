"""python -m edo: arranca el servidor local y abre el navegador."""
import threading
import webbrowser

import uvicorn

PUERTO = 8000


def main() -> None:
    threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{PUERTO}")).start()
    uvicorn.run("edo.api.app:app", host="127.0.0.1", port=PUERTO, log_level="warning")


if __name__ == "__main__":
    main()
