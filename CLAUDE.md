# edo-solver

Herramienta web local en Python que resuelve EDO y muestra el procedimiento paso a paso, en español, con el método y la notación del M.Sc. Ing. Eudal Avendaño Gonzales (UAGRM, FICCT). Es una herramienta de estudio: cada paso debe entenderse y cada resultado debe ser correcto.

## Alcance (5 temas)
1. Conceptos: clasificar, verificar soluciones (explícitas/implícitas), tipos de solución, constantes con condiciones iniciales, dependencia lineal/Wronskiano, ED desde raíces características.
2. 1er orden: separable, reducible a separable, homogénea (y=tx, x=ty), lineal en y o x, Bernoulli, exacta (incl. hallar M o N), valores iniciales; grado superior: y=f(y'), x=f(y'), Clairaut, Lagrange (paramétrica y singular).
3. Método abreviado (operador D): homogénea de coef. constantes; no homogénea Casos I, II, III, polinomios, resonancia, sumas; coeficientes indeterminados con modificación.
4. Variación de parámetros: orden 2, 3 y n; L'_i, Cramer, Wronskiano; coeficiente principal ≠ 1.
5. Coeficiente variable: Euler (x=e^t) y Cauchy-Legendre (ax+b=e^t), homogénea y no homogénea.

Fuera de alcance: Laplace, series, sistemas, EDP, métodos numéricos.

## Reglas inamovibles
1. La matemática correcta manda sobre el texto del docente. Si el texto la contradice (docs/DISCREPANCIAS.md), se resuelve lo correcto y el paso afectado lleva la nota "Discrepancia con el texto del docente".
2. Todo resultado se verifica por sustitución en la ED original: simbólico y, si no simplifica, numérico en 5 puntos aleatorios. Si falla, no se presenta como correcto. Una prueba falla si un solver devuelve algo no verificado.
3. SymPy es el motor, pero `dsolve` NO se usa para producir pasos; solo en pruebas, como contraste. Cada método se programa a mano y emite sus pasos. Integrales: `manualintegrate`/`integral_steps` traducidos al español; derivadas: derivador propio por reglas (suma, producto, cociente, cadena, tabla).
4. Pasos en español con los nombres del docente: ecuación característica, operador D, método abreviado, y_h (solución homogénea), y_p (solución particular; el docente a veces la llama y_c, anótalo).
5. Nunca inventar un paso. Si ningún método aplica: "no aplica con los métodos del temario" y qué se intentó.
6. Integrales no elementales: dejarlas indicadas con aviso; no fallar ni devolver basura.
7. Reportar soluciones perdidas al dividir (y=0, p=0, singulares).
8. y(a)=b significa x=a, y=b; y'(a)=c significa derivada en x=a igual a c.
9. Entrada flexible: `y'+2y=x e^x`, `dy/dx`, forma diferencial `(x+y)dx-(x-y)dy=0`, notación D `(D^2-3D+2)y=e^x`, funciones en español (sen, cos, tg, ctg, sec, csc, arcsen, arctg, ln, sqrt, e^).
10. Sin internet ni base de datos en tiempo de ejecución. Si no se puede instalar una dependencia, avisar cuál y por qué; no reemplazarla en silencio.

## Tecnología
Python 3.11+, SymPy, FastAPI + uvicorn, pytest + hypothesis, HTML/JS estático con MathLive (entrada) y KaTeX (salida), sin build. Arranque: `python -m edo` abre http://localhost:8000. Dependencias en pyproject.toml.

## Arquitectura
Flujo: entrada → lector → clasificador → solver → verificador → render.
`src/edo/{core, calculo, conceptos, primer_orden, orden_superior, api}`, `web/`, `tests/{unit,golden}`, `docs/{fuentes,DISCREPANCIAS.md}`.
- Paso = {titulo, regla, antes_latex, despues_latex, explicacion, discrepancia?}
- Resultado = {metodo, pasos, solucion, constantes, verificacion{ok, como}, advertencias, otros_metodos_aplicables}
- El clasificador devuelve todos los métodos aplicables con motivo, por preferencia; la interfaz permite forzar uno.
- API: POST /resolver {entrada, metodo?, condiciones?}, POST /clasificar, POST /verificar {ed, respuesta}.

## Fases (una a la vez; al cerrar: pruebas en verde, commit, resumen corto, esperar "sigue")
F0 base · F1 derivadas/integrales con pasos · F2 Tema 1 · F3 Tema 2 (+grado superior) · F4 Tema 3 · F5 Tema 4 · F6 Tema 5 · F7 pulido (selector de método, revisar mi respuesta, historial, PDF, copiar a GeoGebra) · F8 opcional (problemas escritos con IA, gráficas).
Orden real: las homogéneas de coef. constantes (F4) se usan en F5 y F6.

## Pruebas
`tests/golden/*.yaml`: ED, condiciones, método esperado, solución esperada y referencia. Fuentes: ejemplos del texto (respuesta corregida donde haya error), Evaluaciones I–III, prácticos del Zill (impares). Cada punto de los Anexos A y B de docs/DISCREPANCIAS.md es una prueba. Más pruebas con hypothesis (elegir raíces, armar ED, resolver, comparar).

## Fuentes (docs/fuentes)
- `texto_ecua.pdf` (59 págs, escaneo sin texto): leer como imagen. Nº de página del PDF = nº impreso − 3 (−2 en las impresas 3–5 y 60–61); confirmar siempre con el pie de página. Eval. I–III pp. 3–8, Tema 1 8–21, Tema 2 22–33, Tema 3 grado superior 34–40, Tema 4 40–61 (nº impreso), Prácticos 1–11.
- `zill_wright_8ed.pdf` (643 págs; capa de texto dañada, leer como imagen). Págs. PDF: 1.1→20, 1.3→37, 2.2→60, 2.3→69, 2.4→77, 2.5→82, 4.3→143, 4.4→153, 4.5→160, 4.6→166, 4.7→172; respuestas impares desde 599.
- Prácticos 4 y 5 (Edwards-Penney) no disponibles: usar Zill 2.2 y 2.3.
- Render de páginas en este equipo: no hay poppler; usar PyMuPDF (`pymupdf`) para convertir a PNG y leer con Read. Solo herramienta de desarrollo, no dependencia de runtime.
