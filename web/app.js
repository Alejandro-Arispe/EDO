const $ = (id) => document.getElementById(id);
let usarML = false;

function mate(el, latex, display = true) {
  try { katex.render(latex, el, { displayMode: display, throwOnError: false }); }
  catch (e) { el.textContent = latex; }
}
function texto(el, s) {
  el.textContent = s;
  renderMathInElement(el, { delimiters: [{ left: "$", right: "$", display: false }], throwOnError: false });
}
async function api(ruta, cuerpo) {
  const r = await fetch(ruta, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(d.error || d.detail || r.statusText); e.datos = d; throw e; }
  return d;
}
function entradaED() {
  if (usarML) return { entrada: $("ml").getValue("latex"), latex: true };
  return { entrada: $("entrada").value, latex: false };
}
function crear(tag, clase, padre) { const e = document.createElement(tag); if (clase) e.className = clase; if (padre) padre.appendChild(e); return e; }

function pintarPasos(pasos, destino) {
  pasos.forEach((p, i) => {
    const c = crear("div", "paso", destino);
    crear("h3", "", c).textContent = `${i + 1}. ${p.titulo}`;
    if (p.regla) {
      const r = crear("div", "regla", c);
      if (p.regla.includes("\\")) mate(r, p.regla, false); else r.textContent = p.regla;
    }
    if (p.explicacion) texto(crear("div", "expl", c), p.explicacion);
    if (p.antes_latex) mate(crear("div", "", c), p.antes_latex);
    if (p.despues_latex) mate(crear("div", "", c), "\\Rightarrow\\; " + p.despues_latex);
    if (p.discrepancia) texto(crear("div", "disc", c), "Discrepancia con el texto del docente: " + p.discrepancia);
  });
}
function pintarVerificacion(v, destino) {
  const d = crear("div", "paso", destino);
  crear("div", v.ok ? "ok" : "mal", d).textContent =
    v.ok ? `✔ Verificado por sustitución (${v.como})` : `✘ No verificado / no es solución (${v.como})`;
  if (v.detalle) crear("div", "regla", d).textContent = v.detalle;
}
function error(destino, e) { destino.innerHTML = ""; crear("div", "caja error", destino).textContent = e.message; }

async function leerEnVivo() {
  const caja = $("lectura"); caja.classList.remove("error");
  const q = entradaED();
  if (!q.entrada.trim()) { caja.textContent = "Escribe una ecuación…"; return; }
  try {
    const d = await api("/leer", q);
    caja.innerHTML = "";
    mate(caja, d.latex, false);
    crear("div", "regla", caja).textContent = `Orden ${d.orden} · forma ${d.forma}`;
  } catch (e) { caja.classList.add("error"); caja.textContent = e.message; }
}
let temporizador;
function programarLectura() { clearTimeout(temporizador); temporizador = setTimeout(leerEnVivo, 350); }

async function accion(ruta, destinoId) {
  const destino = $(destinoId); destino.innerHTML = "";
  try {
    const q = entradaED();
    if ($("condiciones").value.trim()) q.condiciones = $("condiciones").value;
    if (ruta === "/resolver" && $("metodo").value) q.metodo = $("metodo").value;
    const d = await api(ruta, q);
    if (d.metodos) poblarMetodos(d.metodos, destino);
    if (d.mensaje) crear("div", "aviso", destino).textContent = d.mensaje;
    if (d.pasos) pintarPasos(d.pasos, destino);
    if (d.solucion) { const s = crear("div", "paso", destino); crear("h3", "", s).textContent = "Solución (" + (d.metodo || "") + ")"; mate(crear("div", "", s), d.solucion); }
    (d.adicionales || []).forEach((a) => { const s = crear("div", "paso", destino); crear("h3", "", s).textContent = a.tipo === "singular" ? "Solución singular" : "Solución perdida al dividir"; mate(crear("div", "", s), a.latex); });
    if (d.verificacion) pintarVerificacion(d.verificacion, destino);
    (d.advertencias || []).forEach((a) => { const av = crear("div", "aviso", destino); texto(av, a); });
    if (d.otros_metodos_aplicables && d.otros_metodos_aplicables.length)
      crear("div", "aviso", destino).textContent = "También aplican: " + d.otros_metodos_aplicables.map((m) => m.titulo).join(", ") + ". Elige uno en el selector «Método» para forzarlo.";
  } catch (e) { error(destino, e); }
}

function poblarMetodos(metodos, destino) {
  const sel = $("metodo"); const actual = sel.value;
  sel.innerHTML = '<option value="">Método: automático</option>';
  metodos.forEach((m) => { const o = document.createElement("option"); o.value = m.metodo; o.textContent = m.titulo; sel.appendChild(o); });
  [["homogenea_yx", "Homogénea con y = t x"], ["homogenea_xy", "Homogénea con x = t y"]].forEach(([v, n]) => {
    if (metodos.some((m) => m.metodo === "homogenea")) { const o = document.createElement("option"); o.value = v; o.textContent = n; sel.appendChild(o); }
  });
  sel.value = [...sel.options].some((o) => o.value === actual) ? actual : "";
  if (metodos.length) {
    const av = crear("div", "aviso", destino);
    av.textContent = "Métodos aplicables: " + metodos.map((m) => m.titulo + " (" + m.motivo + ")").join(" · ");
  }
}

async function verificar() {
  const destino = $("salida-ed"); destino.innerHTML = "";
  try {
    const d = await api("/verificar", { ed: entradaED().entrada, respuesta: $("respuesta").value });
    if (d.pasos) pintarPasos(d.pasos, destino);
    pintarVerificacion(d.verificacion, destino);
  } catch (e) { error(destino, e); }
}

function actualizarCampos() {
  const h = $("c-herr").value;
  document.querySelectorAll(".c-campo").forEach((c) => { c.style.display = c.dataset.herr.split(" ").includes(h) ? "block" : "none"; });
}
async function concepto() {
  const destino = $("salida-conceptos"); destino.innerHTML = "";
  const h = $("c-herr").value;
  try {
    let d;
    if (h === "constantes") d = await api("/conceptos/constantes", { ed: $("c-ed").value, respuesta: $("c-resp").value, condiciones: $("c-cond").value });
    else if (h === "tipo") d = await api("/conceptos/tipo_solucion", { ed: $("c-ed").value, respuesta: $("c-resp").value, general: $("c-gen").value });
    else if (h === "dependencia") d = await api("/conceptos/dependencia", { entrada: $("c-funcs").value, mismo_ed: $("c-mismo").checked });
    else d = await api("/conceptos/raices", { entrada: $("c-raices").value });
    if (d.solucion) mate(crear("div", "paso", destino), d.solucion.includes("\\") || d.solucion.includes("=") ? d.solucion : "\text{" + d.solucion + "}");
    pintarPasos(d.pasos, destino);
    if (d.verificacion) pintarVerificacion(d.verificacion, destino);
    (d.advertencias || []).forEach((a) => { crear("div", "aviso", destino).textContent = a; });
  } catch (e) { error(destino, e); }
}

async function calculo(ruta) {
  const destino = $("salida-calculo"); destino.innerHTML = "";
  try {
    const d = await api(ruta, { entrada: $("f").value });
    mate(crear("div", "paso", destino), d.enunciado_latex);
    pintarPasos(d.pasos, destino);
    if (d.verificacion) pintarVerificacion(d.verificacion, destino);
    (d.advertencias || []).forEach((a) => { crear("div", "aviso", destino).textContent = a; });
  } catch (e) { error(destino, e); }
}

document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("#tabs button").forEach((o) => o.classList.toggle("activa", o === b));
  $("tab-ed").hidden = b.dataset.tab !== "ed";
  $("tab-calculo").hidden = b.dataset.tab !== "calculo";
  $("tab-conceptos").hidden = b.dataset.tab !== "conceptos";
}));
$("entrada").addEventListener("input", programarLectura);
$("ml").addEventListener("input", programarLectura);
$("toggle-ml").addEventListener("click", () => {
  usarML = !usarML;
  $("ml").style.display = usarML ? "block" : "none";
  $("entrada").style.display = usarML ? "none" : "block";
  programarLectura();
});
$("btn-clasificar").addEventListener("click", () => accion("/clasificar", "salida-ed"));
$("btn-resolver").addEventListener("click", () => accion("/resolver", "salida-ed"));
$("btn-verificar").addEventListener("click", verificar);
$("c-herr").addEventListener("change", actualizarCampos);
$("btn-concepto").addEventListener("click", concepto);
actualizarCampos();
$("btn-derivar").addEventListener("click", () => calculo("/calculo/derivar"));
$("btn-integrar").addEventListener("click", () => calculo("/calculo/integrar"));
try { if (window.MathfieldElement) MathfieldElement.fontsDirectory = "vendor/mathlive/fonts"; } catch (e) {}
