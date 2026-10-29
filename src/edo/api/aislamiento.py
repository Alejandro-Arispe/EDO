"""Ejecución de las peticiones pesadas en procesos aparte, con límite de tiempo y de memoria.

SymPy puede tardar muchísimo (o colgarse) con una ecuación rara, y un hilo no se puede matar. Para un
servidor público (Render) cada petición se resuelve en un proceso trabajador; si pasa del límite se mata el
trabajador y se responde 504, así el servidor sigue vivo.

Se activa con EDO_AISLAR=1 (render.yaml lo hace). En el equipo local (``python -m edo``) está apagado y las
peticiones se resuelven en el mismo proceso.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import queue
import sys
import threading

EN_TRABAJADOR = False


class TiempoAgotado(Exception):
    pass


class Ocupado(Exception):
    pass


def activo() -> bool:
    return os.environ.get("EDO_AISLAR", "").strip() == "1" and not EN_TRABAJADOR


def _limitar_memoria(megas: int) -> None:
    try:
        import resource
        limite = megas * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limite, limite))
    except Exception:       # Windows o sin permiso: sin límite de memoria
        pass


def _bucle(conn, modulo: str, megas: int) -> None:
    """Proceso trabajador: importa la app una sola vez y atiende peticiones hasta recibir None."""
    global EN_TRABAJADOR
    EN_TRABAJADOR = True
    if megas:
        _limitar_memoria(megas)
    import importlib
    app = importlib.import_module(modulo)
    conn.send(("listo",))
    while True:
        try:
            msg = conn.recv()
        except EOFError:
            return
        if msg is None:
            return
        nombre, clase, datos = msg
        try:
            res = getattr(app, nombre)(getattr(app, clase)(**datos))
            conn.send(app.empaquetar(res))
        except app.ErrorLectura as exc:
            conn.send(("err", "ErrorLectura", str(exc)))
        except MemoryError:
            conn.send(("err", "Memoria", "La ecuación necesitó demasiada memoria."))
        except Exception as exc:        # noqa: BLE001 - se informa al cliente sin tumbar el trabajador
            conn.send(("err", type(exc).__name__, str(exc)[:200]))


class _Trabajador:
    def __init__(self, modulo: str, megas: int):
        ctx = mp.get_context("spawn")
        self.conn, hijo = ctx.Pipe()
        self.proc = ctx.Process(target=_bucle, args=(hijo, modulo, megas), daemon=True)
        self.proc.start()
        hijo.close()
        self.listo = False

    def esperar_listo(self, timeout: float) -> bool:
        if self.listo:
            return True
        if self.conn.poll(timeout) and self.conn.recv() == ("listo",):
            self.listo = True
        return self.listo

    def vivo(self) -> bool:
        return self.proc.is_alive()

    def matar(self) -> None:
        try:
            self.proc.kill()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass


class Piscina:
    def __init__(self, modulo: str, n: int = 1, timeout: float = 80.0, espera: float = 30.0, megas: int = 900):
        self.modulo, self.timeout, self.espera, self.megas = modulo, timeout, espera, megas
        self.libres: "queue.Queue[_Trabajador | None]" = queue.Queue()
        for _ in range(n):
            self.libres.put(None)       # se crean bajo demanda (el primero tarda en importar SymPy)
        self._cerrojo = threading.Lock()

    def ejecutar(self, nombre: str, clase: str, datos: dict):
        try:
            t = self.libres.get(timeout=self.espera)
        except queue.Empty:
            raise Ocupado() from None
        devolver = None
        try:
            if t is None or not t.vivo():
                t = _Trabajador(self.modulo, self.megas)
            if not t.esperar_listo(max(self.timeout, 120.0)):
                t.matar()
                raise TiempoAgotado()
            t.conn.send((nombre, clase, datos))
            if not t.conn.poll(self.timeout):
                t.matar()
                raise TiempoAgotado()
            devolver = t
            return t.conn.recv()
        except (EOFError, BrokenPipeError, OSError):
            if t is not None:
                t.matar()
            devolver = None
            return ("err", "Trabajador", "El proceso de cálculo se cerró inesperadamente. Inténtalo de nuevo.")
        finally:
            self.libres.put(devolver)

    def calentar(self) -> None:
        """Crea el trabajador antes de la primera petición (importar SymPy tarda unos segundos)."""
        try:
            t = self.libres.get(timeout=1)
        except queue.Empty:
            return
        try:
            if t is None or not t.vivo():
                t = _Trabajador(self.modulo, self.megas)
            t.esperar_listo(max(self.timeout, 120.0))
        except Exception:
            t = None
        finally:
            self.libres.put(t)

    def cerrar(self) -> None:
        while True:
            try:
                t = self.libres.get_nowait()
            except queue.Empty:
                break
            if t is not None:
                try:
                    t.conn.send(None)
                except Exception:
                    pass
                t.matar()


_piscina: Piscina | None = None
_c = threading.Lock()


def piscina(modulo: str = "edo.api.app") -> Piscina:
    global _piscina
    with _c:
        if _piscina is None:
            _piscina = Piscina(modulo, int(os.environ.get("EDO_TRABAJADORES", "1")),
                               float(os.environ.get("EDO_TIMEOUT", "80")), megas=int(os.environ.get("EDO_MEMORIA_MB", "900")))
        return _piscina
