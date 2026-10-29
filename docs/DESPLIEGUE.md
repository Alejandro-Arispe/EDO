# Subir edo-solver a Render

1. **GitHub:** crea un repositorio (puede ser privado) y sube el proyecto:
   ```bash
   git remote add origin https://github.com/TU_USUARIO/edo-solver.git
   git branch -M main
   git push -u origin main
   ```
   Los PDF de `docs/fuentes/` están en `.gitignore` (son libros con derechos de autor): no se suben.
2. **Render:** *New + → Blueprint* → elige el repositorio. Render lee `render.yaml` y crea el servicio web.
   (O *New + → Web Service* con: Build `pip install -e .`, Start `uvicorn edo.api.app:app --host 0.0.0.0 --port $PORT`,
   variables `PYTHON_VERSION=3.12.7`, `EDO_AISLAR=1`.)
3. **Probar:** abre la URL `https://edo-solver-XXXX.onrender.com`; `/salud` debe responder `{"ok": true}`.

## Qué hace el modo servidor (`EDO_AISLAR=1`)
* Cada ecuación se resuelve en un proceso aparte; si pasa de `EDO_TIMEOUT` segundos se mata y se responde 504.
* Si hay más peticiones simultáneas que `EDO_TRABAJADORES`, las que esperan más de 30 s reciben 503.
* La entrada se valida antes de usar `eval` de SymPy (solo matemática: sin atributos, corchetes, comillas, nombres largos).

## Límites del plan gratuito
* 512 MB de RAM y CPU compartida: SymPy es pesado; las ecuaciones difíciles pueden agotar el tiempo.
* El servicio se duerme tras 15 minutos sin visitas: la primera petición tarda ~1 minuto en despertar.
* Si lo vas a usar en clase con varias personas a la vez, usa un plan de pago (Starter) y sube `EDO_TRABAJADORES` a 2.

## Seguridad
* No hay inicio de sesión ni base de datos: cualquiera con el enlace puede usarlo. Si prefieres que sea solo tuyo,
  usa un repositorio privado y no compartas la URL, o pon la app detrás de una contraseña.
* No definas `ANTHROPIC_API_KEY` en Render (la función de IA gastaría tu saldo).
* El historial se guarda en el navegador de cada persona, no en el servidor.

---

# Subir edo-solver a Vercel (alternativa a Render)

Render y Vercel **no** piden lo mismo. Render ejecuta un servidor que queda encendido (como en tu PC); Vercel ejecuta
la app como una **función** que se crea por petición. Por eso el proyecto trae archivos para ambos:

| Archivo | Para qué |
|---|---|
| `render.yaml`, `EDO_AISLAR` | solo Render (servidor con procesos de cálculo aislados) |
| `api/index.py`, `vercel.json`, `requirements.txt`, `.vercelignore` | solo Vercel |
| `.python-version` (`3.12`) | versión de Python (Vercel); Render la toma de `PYTHON_VERSION` en `render.yaml` |

Pasos:
1. Sube el proyecto a GitHub (ver arriba).
2. En vercel.com: *Add New… → Project* → importa el repositorio. Framework: **Other**. No pongas comando de build.
3. Deploy. Abre la URL; `/salud` debe responder `{"ok": true}`.
4. **No definas `EDO_AISLAR`** en Vercel: cada petición ya es una función aislada y la plataforma corta por tiempo
   (`maxDuration` en `vercel.json`, 120 s; el plan Hobby permite hasta 300 s).

Notas:
* Límite de paquete de Python: 500 MB sin comprimir; SymPy + FastAPI caben de sobra.
* Cada función "en frío" tarda unos segundos en importar SymPy; las siguientes peticiones son más rápidas.
* El plan Hobby es para uso personal/no comercial.
* Memoria y duración dependen del plan; si una ecuación se corta por tiempo, la respuesta es un error claro, no un cuelgue.
