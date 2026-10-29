const $ = (id) => document.getElementById(id);
let usarML = false;
let ultimo = null; // último resultado de /resolver: { entrada, condiciones, metodo, datos }

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

// ------------------------------------------------------------------ resolver
async function accion(ruta, destinoId) {
  const destino = $(destinoId); destino.innerHTML = "";
  $("herramientas").hidden = true;
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
    if (ruta === "/resolver" && d.solucion) {
      ultimo = { entrada: q.entrada, latex: q.latex, condiciones: q.condiciones || "", metodo: $("metodo").value, datos: d };
      $("herramientas").hidden = false;
      $("msg-herramientas").textContent = "";
      $("btn-gg").disabled = !(d.geogebra && d.geogebra.length);
      guardarHistorial(ultimo);
    }
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

// ------------------------------------------------------ revisar mi respuesta
async function verificar() {
  const destino = $("salida-revisar"); destino.innerHTML = "";
  try {
    const q = { ed: entradaED().entrada, respuesta: $("respuesta").value };
    if (!q.ed.trim() || !q.respuesta.trim()) throw new Error("Escribe la ecuación (arriba) y tu respuesta.");
    const d = await api("/verificar", q);
    const r = crear("div", "paso", destino);
    crear("div", d.verificacion.ok ? "ok" : "mal", r).textContent =
      d.verificacion.ok ? "✔ Tu respuesta es solución de la ecuación." : "✘ Tu respuesta NO es solución de la ecuación.";
    if (d.tipo) texto(crear("div", "regla", r), d.tipo);
    if (d.verificacion.detalle) crear("div", "regla", r).textContent = d.verificacion.detalle;
    if (d.pasos) pintarPasos(d.pasos, destino);
    pintarVerificacion(d.verificacion, destino);
  } catch (e) { error(destino, e); }
}

// ---------------------------------------------------------------- GeoGebra / PDF
async function copiarGeoGebra() {
  if (!ultimo || !ultimo.datos.geogebra || !ultimo.datos.geogebra.length) return;
  const txt = ultimo.datos.geogebra.join("\n");
  let ok = false;
  try { await navigator.clipboard.writeText(txt); ok = true; }
  catch (e) {
    const ta = crear("textarea", "", document.body); ta.value = txt; ta.select();
    try { ok = document.execCommand("copy"); } catch (e2) { ok = false; }
    ta.remove();
  }
  const msg = $("msg-herramientas");
  if (ok) { msg.textContent = "Copiado: pega cada línea en la barra de entrada de GeoGebra (geogebra.org/classic)."; return; }
  msg.textContent = "No pude usar el portapapeles; copia estas líneas a mano:";
  const pre = crear("pre", "", msg); pre.textContent = txt; pre.style.userSelect = "all";
}
function exportarPDF() {
  const cab = $("cabecera-impresion"); cab.innerHTML = "";
  const t = crear("h2", "", cab); t.textContent = "edo-solver · " + new Date().toLocaleDateString("es-BO");
  if (ultimo) {
    mate(crear("div", "", cab), ultimo.datos.lectura ? ultimo.datos.lectura.latex : ultimo.entrada);
    if (ultimo.condiciones) crear("div", "regla", cab).textContent = "Condiciones: " + ultimo.condiciones;
  }
  $("tab-ed").hidden = false;
  window.print();
}

// ------------------------------------------------------------------ historial
const CLAVE = "edo_historial";
function leerHistorial() { try { return JSON.parse(localStorage.getItem(CLAVE) || "[]"); } catch (e) { return []; } }
function escribirHistorial(h) { try { localStorage.setItem(CLAVE, JSON.stringify(h.slice(0, 60))); } catch (e) { /* sin almacenamiento */ } }
function guardarHistorial(u) {
  const h = leerHistorial().filter((e) => !(e.entrada === u.entrada && e.condiciones === u.condiciones && e.metodo === u.metodo));
  h.unshift({ entrada: u.entrada, latex: !!u.latex, condiciones: u.condiciones, metodo: u.metodo, metodoNombre: u.datos.metodo,
    solucion: u.datos.solucion, ok: !!(u.datos.verificacion && u.datos.verificacion.ok), fecha: new Date().toISOString() });
  escribirHistorial(h);
}
function pintarHistorial() {
  const lista = $("lista-historial"); lista.innerHTML = "";
  const h = leerHistorial();
  if (!h.length) { crear("div", "caja", lista).textContent = "Todavía no hay ecuaciones resueltas. Se guardan en este navegador."; return; }
  h.forEach((e, i) => {
    const c = crear("div", "paso", lista);
    const cab = crear("div", "fila", c);
    const txt = crear("div", "", cab); txt.style.flex = "1";
    crear("code", "", txt).textContent = e.entrada + (e.condiciones ? "   [" + e.condiciones + "]" : "");
    crear("div", "regla", txt).textContent = `${e.metodoNombre || ""} · ${e.ok ? "verificada" : "sin verificar"} · ${new Date(e.fecha).toLocaleString("es-BO")}`;
    const bc = crear("button", "", cab); bc.textContent = "Cargar";
    bc.addEventListener("click", () => cargarDelHistorial(e));
    const bb = crear("button", "", cab); bb.textContent = "Borrar";
    bb.addEventListener("click", () => { const x = leerHistorial(); x.splice(i, 1); escribirHistorial(x); pintarHistorial(); });
    if (e.solucion) mate(crear("div", "", c), e.solucion);
  });
}
function cargarDelHistorial(e) {
  mostrarTab("ed");
  if (e.latex && usarML) $("ml").setValue(e.entrada); else { if (usarML) $("toggle-ml").click(); $("entrada").value = e.entrada; }
  $("condiciones").value = e.condiciones || "";
  leerEnVivo();
}

// ----------------------------------------------------------- conceptos y cálculo
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
    if (d.solucion) mate(crear("div", "paso", destino), d.solucion.includes("\\") || d.solucion.includes("=") ? d.solucion : "\\text{" + d.solucion + "}");
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

// ------------------------------------------------------------------ pestañas
function mostrarTab(nombre) {
  document.querySelectorAll("#tabs button").forEach((o) => o.classList.toggle("activa", o.dataset.tab === nombre));
  ["ed", "calculo", "conceptos", "historial", "problemas"].forEach((t) => { $("tab-" + t).hidden = t !== nombre; });
  if (nombre === "historial") pintarHistorial();
}
document.querySelectorAll("#tabs button").forEach((b) => b.addEventListener("click", () => mostrarTab(b.dataset.tab)));
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
$("btn-gg").addEventListener("click", copiarGeoGebra);
$("btn-pdf").addEventListener("click", exportarPDF);
$("btn-vaciar").addEventListener("click", () => { escribirHistorial([]); pintarHistorial(); });
$("c-herr").addEventListener("change", actualizarCampos);
$("btn-concepto").addEventListener("click", concepto);
actualizarCampos();
$("btn-derivar").addEventListener("click", () => calculo("/calculo/derivar"));
$("btn-integrar").addEventListener("click", () => calculo("/calculo/integrar"));
// ------------------------------------------------------------------ gráfica
const COLORES = ["#1f77b4", "#2ca02c", "#9467bd", "#8c564b", "#17becf", "#e377c2", "#bcbd22", "#7f7f7f"];
function dibujarGrafica(canvas, datos) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const g = canvas.getContext("2d"); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const css = getComputedStyle(document.body);
  const fg = css.getPropertyValue("--fg").trim() || "#222", bd = css.getPropertyValue("--bd").trim() || "#ccc";
  const { xmin, xmax, ymin, ymax } = datos.rango;
  const px = (x) => ((x - xmin) / (xmax - xmin)) * W, py = (y) => H - ((y - ymin) / (ymax - ymin)) * H;
  g.clearRect(0, 0, W, H);
  const paso = (a, b) => { const r = (b - a) / 8, m = Math.pow(10, Math.floor(Math.log10(r))); const f = r / m; return (f < 1.5 ? 1 : f < 3.5 ? 2 : f < 7.5 ? 5 : 10) * m; };
  g.font = "11px system-ui"; g.fillStyle = fg; g.strokeStyle = bd; g.lineWidth = 1;
  const sx = paso(xmin, xmax), sy = paso(ymin, ymax);
  for (let v = Math.ceil(xmin / sx) * sx; v <= xmax; v += sx) { g.beginPath(); g.moveTo(px(v), 0); g.lineTo(px(v), H); g.stroke(); g.fillText(String(+v.toFixed(6)), px(v) + 2, Math.min(H - 3, Math.max(11, py(0) + 12))); }
  for (let v = Math.ceil(ymin / sy) * sy; v <= ymax; v += sy) { g.beginPath(); g.moveTo(0, py(v)); g.lineTo(W, py(v)); g.stroke(); g.fillText(String(+v.toFixed(6)), Math.min(W - 28, Math.max(2, px(0) + 3)), py(v) - 2); }
  g.strokeStyle = fg; g.lineWidth = 1.6;
  if (ymin < 0 && ymax > 0) { g.beginPath(); g.moveTo(0, py(0)); g.lineTo(W, py(0)); g.stroke(); }
  if (xmin < 0 && xmax > 0) { g.beginPath(); g.moveTo(px(0), 0); g.lineTo(px(0), H); g.stroke(); }
  datos.series.forEach((s, i) => {
    g.strokeStyle = s.singular ? "#d62728" : COLORES[i % COLORES.length];
    g.lineWidth = s.singular ? 2.6 : 1.8; g.setLineDash(s.singular ? [6, 4] : []);
    s.segmentos.forEach((seg) => { g.beginPath(); seg.forEach((p, k) => { const X = px(p[0]), Y = py(p[1]); if (k) g.lineTo(X, Y); else g.moveTo(X, Y); }); g.stroke(); });
  });
  g.setLineDash([]);
}
async function graficar() {
  if (!ultimo) return;
  const zona = $("zona-grafica"); zona.hidden = false;
  const num = (id, d) => { const v = parseFloat($(id).value); return Number.isFinite(v) ? v : d; };
  const cuerpo = { entrada: ultimo.entrada, latex: !!ultimo.latex, condiciones: ultimo.condiciones || null, metodo: ultimo.metodo || null,
    xmin: num("g-xmin", -5), xmax: num("g-xmax", 5), ymin: num("g-ymin", -5), ymax: num("g-ymax", 5), familia: $("g-familia").value };
  const msg = $("g-msg"); msg.textContent = "";
  try {
    const d = await api("/grafica", cuerpo);
    dibujarGrafica($("canvas-grafica"), d);
    const leyenda = $("g-leyenda"); leyenda.innerHTML = "";
    d.series.forEach((s, i) => { const sp = crear("span", "leyenda", leyenda); sp.style.borderColor = s.singular ? "#d62728" : COLORES[i % COLORES.length]; sp.textContent = s.nombre; });
    if (!d.series.some((s) => s.segmentos.length)) msg.textContent = "No hay puntos en este rango: prueba otro rango o otros valores de la constante.";
  } catch (e) { msg.textContent = e.message; }
}
$("btn-graficar").addEventListener("click", graficar);
["g-xmin", "g-xmax", "g-ymin", "g-ymax", "g-familia"].forEach((id) => $(id).addEventListener("change", graficar));

// ------------------------------------------------------------------ problemas
let plantillas = [];
async function cargarPlantillas() {
  try { plantillas = await (await fetch("/problema/plantillas")).json(); } catch (e) { return; }
  const sel = $("p-plantilla"); sel.innerHTML = "";
  plantillas.forEach((p) => { const o = document.createElement("option"); o.value = p.id; o.textContent = p.titulo; sel.appendChild(o); });
  pintarCamposPlantilla();
}
function pintarCamposPlantilla() {
  const p = plantillas.find((q) => q.id === $("p-plantilla").value); if (!p) return;
  $("p-desc").textContent = p.descripcion;
  const cont = $("p-campos"); cont.innerHTML = "";
  p.parametros.forEach((q) => {
    const d = crear("div", "campo-param", cont);
    crear("label", "", d).textContent = q.etiqueta;
    const i = crear("input", "", d); i.dataset.nombre = q.nombre; i.value = q.ejemplo; i.placeholder = q.ejemplo; i.autocomplete = "off";
  });
}
async function resolverPlantilla() {
  const destino = $("salida-problema"); destino.innerHTML = "";
  const parametros = {}; document.querySelectorAll("#p-campos input").forEach((i) => { parametros[i.dataset.nombre] = i.value; });
  try {
    const d = await api("/problema/plantilla", { id: $("p-plantilla").value, parametros });
    (d.respuestas || []).forEach((r) => { const c = crear("div", "paso respuesta", destino); crear("h3", "", c).textContent = r.etiqueta; mate(c, r.latex + (r.aprox ? "\\approx " + r.aprox : "")); });
    pintarPasos(d.pasos, destino);
    if (d.verificacion) pintarVerificacion(d.verificacion, destino);
    (d.advertencias || []).forEach((a) => { texto(crear("div", "aviso", destino), a); });
    crear("div", "aviso", destino).textContent = "En el modelo, x representa el tiempo t y y la cantidad que cambia.";
  } catch (e) { error(destino, e); }
}
async function estadoIA() {
  try {
    const d = await (await fetch("/problema/ia/estado")).json();
    $("ia-estado").textContent = d.disponible ? "IA disponible (clave detectada en este equipo)." : "IA apagada: para activarla define la variable de entorno ANTHROPIC_API_KEY y reinicia el programa. Las plantillas funcionan sin internet.";
    $("ia-form").hidden = !d.disponible;
  } catch (e) { /* sin servidor */ }
}
async function proponerIA() {
  const destino = $("salida-ia"); destino.innerHTML = "";
  if (!$("ia-confirmo").checked) { error(destino, new Error("Marca la casilla para confirmar el envío del enunciado a la API.")); return; }
  try {
    const d = await api("/problema/ia/proponer", { enunciado: $("ia-enunciado").value, confirmo_envio: true });
    const c = crear("div", "paso", destino);
    crear("h3", "", c).textContent = "Propuesta de la IA (revísala antes de resolver)";
    if (d.interpretacion) crear("div", "expl", c).textContent = d.interpretacion;
    if (d.pregunta) crear("div", "expl", c).textContent = "Pregunta: " + d.pregunta;
    (d.supuestos || []).forEach((s) => crear("div", "aviso", c).textContent = "Supuesto a confirmar: " + s);
    if (!d.valida) { crear("div", "caja error", c).textContent = d.error; }
    crear("label", "", c).textContent = "Ecuación (puedes corregirla)";
    const e1 = crear("input", "", c); e1.id = "ia-ed"; e1.value = d.ed || "";
    crear("label", "", c).textContent = "Condiciones / datos";
    const e2 = crear("input", "", c); e2.id = "ia-cond"; e2.value = d.condiciones || "";
    const b = crear("button", "primario", crear("div", "fila", c)); b.textContent = "Usar en «Ecuación diferencial» para resolver";
    b.addEventListener("click", () => { mostrarTab("ed"); if (usarML) $("toggle-ml").click(); $("entrada").value = e1.value; $("condiciones").value = e2.value; leerEnVivo(); });
  } catch (e) { error(destino, e); }
}
$("p-plantilla").addEventListener("change", pintarCamposPlantilla);
$("btn-plantilla").addEventListener("click", resolverPlantilla);
$("btn-ia").addEventListener("click", proponerIA);
cargarPlantillas(); estadoIA();
try { if (window.MathfieldElement) MathfieldElement.fontsDirectory = "vendor/mathlive/fonts"; } catch (e) {}
