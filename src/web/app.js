"use strict";

/* ==========================================================================
   Sazón Urbano · Interfaz de gestión de pedidos
   Todo lo que se muestra al usuario está en español sencillo: sin códigos,
   sin identificadores técnicos y sin mensajes de programación.
   ========================================================================== */

// ---------- Textos y catálogos de la interfaz ----------
const ROLES = {
  "Mesero": "Toma los pedidos de los clientes.",
  "Cocina": "Prepara los pedidos.",
  "Repartidor": "Entrega los pedidos que ya están listos.",
  "Encargado": "Supervisa el local, cancela pedidos y ajusta el inventario.",
  "Gerente": "Tiene todos los permisos, incluida la cancelación de pedidos.",
};
const ROLES_QUE_CANCELAN = ["Encargado", "Gerente"];

const ESTADOS = ["Registrado", "En preparación", "Listo", "Entregado", "Cancelado"];
const ESTADO_VISUAL = {
  "Registrado": { clase: "registrado", ayuda: "El pedido fue recibido y espera a que cocina lo empiece." },
  "En preparación": { clase: "preparacion", ayuda: "Cocina está preparando el pedido." },
  "Listo": { clase: "listo", ayuda: "El pedido está terminado y listo para entregarse al cliente." },
  "Entregado": { clase: "entregado", ayuda: "El pedido ya se entregó al cliente." },
  "Cancelado": { clase: "cancelado", ayuda: "El pedido fue cancelado y no se preparará." },
};
const SIGUIENTE_PASO = {
  "Registrado": { ruta: "preparacion", etiqueta: "Comenzar a preparar", icono: "flame",
    exito: "Listo: el pedido ahora está en preparación." },
  "En preparación": { ruta: "listo", etiqueta: "Marcar como listo", icono: "check",
    exito: "Listo: el pedido quedó terminado y puede entregarse." },
  "Listo": { ruta: "entrega", etiqueta: "Entregar al cliente", icono: "bag", confirmar: true,
    exito: "Pedido entregado. Los productos ya se descontaron del inventario." },
};

const ACCIONES_HISTORIAL = {
  REGISTRAR_PEDIDO: { texto: "Se registró un pedido nuevo", icono: "plus", clase: "e-registrado" },
  INICIAR_PREPARACION: { texto: "El pedido empezó a prepararse", icono: "flame", clase: "e-preparacion" },
  MARCAR_LISTO: { texto: "El pedido quedó listo", icono: "check", clase: "e-listo" },
  ENTREGAR_PEDIDO: { texto: "El pedido fue entregado", icono: "bag", clase: "e-entregado" },
  CANCELAR_PEDIDO: { texto: "El pedido fue cancelado", icono: "x", clase: "e-cancelado" },
  STOCK_CRITICO: { texto: "Aviso: quedan pocas existencias", icono: "alert", clase: "e-aviso" },
  AJUSTE_INVENTARIO: { texto: "Se ajustó el inventario", icono: "box", clase: "e-gris" },
  DESCUENTO_INVENTARIO_FALLIDO: { texto: "No se pudo descontar el inventario", icono: "alert", clase: "e-error" },
};

// En estas acciones el detalle solo repetiría el título, así que no se muestra.
const ACCIONES_SIN_DETALLE = ["INICIAR_PREPARACION", "MARCAR_LISTO", "ENTREGAR_PEDIDO"];

const VISTAS = {
  inicio: { titulo: "Inicio", icono: "home" },
  nuevo: { titulo: "Nuevo pedido", icono: "plus" },
  pedidos: { titulo: "Pedidos", icono: "list" },
  inventario: { titulo: "Inventario", icono: "box" },
  historial: { titulo: "Historial", icono: "clock" },
};

const ICONOS = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  minus: '<path d="M5 12h14"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  box: '<path d="M21 8 12 3 3 8v8l9 5 9-5zM3 8l9 5 9-5M12 13v8"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  flame: '<path d="M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z"/>',
  bag: '<path d="M5 8h14l-1 12H6zM9 8a3 3 0 0 1 6 0"/>',
  alert: '<path d="M12 4 2.5 20h19zM12 10v4M12 17h.01"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  money: '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
};

// ---------- Estado de la aplicación ----------
const S = {
  rol: localStorage.getItem("sazon_rol") || "Mesero",
  clientes: [],
  platillos: [],
  pedidos: [],
  vista: "inicio",
  filtroPedidos: { estado: "Todos", texto: "", pagina: 1 },
  filtroInventario: { situacion: "todos", texto: "" },
  historial: { pestana: "todo", texto: "", limite: 40 },
  nuevo: reiniciarNuevo(),
  modalPedido: null,
};
if (!ROLES[S.rol]) S.rol = "Mesero";

function reiniciarNuevo() {
  return { cliente: "", carrito: {}, notas: {}, promo: false, autorizado: true, referencia: "",
    texto: "", categoria: "Todas", enviando: false, resultado: null };
}

// ---------- Utilidades ----------
const $ = (selector, raiz = document) => raiz.querySelector(selector);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ic = (nombre) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[nombre] || ""}</svg>`;
const cap = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : "");
const unidades = (n) => `${n} ${Number(n) === 1 ? "unidad" : "unidades"}`;
const dinero = (n) => new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" }).format(Number(n) || 0);

function fechaHora(iso) {
  if (!iso) return "";
  let texto = String(iso);
  if (texto.includes("T") && !/(Z|[+-]\d\d:?\d\d)$/.test(texto)) texto += "Z";
  const fecha = new Date(texto);
  if (Number.isNaN(fecha.getTime())) return "";
  return fecha.toLocaleString("es-MX", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}
function soloFecha(iso) {
  if (!iso) return "";
  const [a, m, d] = String(iso).slice(0, 10).split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" });
}
const usuarioActual = () => S.rol.toLowerCase();
const puedeCancelar = () => ROLES_QUE_CANCELAN.includes(S.rol);

const clientePorId = (id) => S.clientes.find((c) => c.id === id);
const platilloPorId = (id) => S.platillos.find((p) => p.id === id);
const nombreCliente = (id) => clientePorId(id)?.nombre || "Cliente no registrado";
const nombreProducto = (id) => platilloPorId(id)?.descripcion || "Producto no registrado";
const nombresEnTexto = (texto) => String(texto || "").replace(/PED-[CP]\d{3}/g, (id) =>
  clientePorId(id)?.nombre || platilloPorId(id)?.descripcion || id);

function etiquetaEstado(estado) {
  const v = ESTADO_VISUAL[estado] || { clase: "gris" };
  return `<span class="etiqueta e-${v.clase}">${esc(estado)}</span>`;
}

function situacionPlatillo(p) {
  if (!p.habilitado) return { clave: "nodisponible", texto: "No disponible", clase: "e-gris" };
  if (p.stock <= 0) return { clave: "agotado", texto: "Agotado", clase: "e-error" };
  if (p.stock_critico) return { clave: "pocas", texto: "Pocas existencias", clase: "e-aviso" };
  return { clave: "disponible", texto: "Disponible", clase: "e-ok" };
}

function resumenProductos(pedido) {
  return pedido.lineas.map((l) => `${l.cantidad} × ${nombreProducto(l.platillo_id)}`).join(", ");
}

// ---------- Comunicación con el sistema ----------
const CAMPOS_AMIGABLES = {
  lineas: "los productos", actor_id: "el cliente", cantidad: "la cantidad", motivo: "el motivo",
  platillo_id: "el producto", tipo: "el tipo de movimiento", usuario: "el usuario", rol: "el rol",
};

function mensajeDeError(cuerpo, estado) {
  let texto = cuerpo && typeof cuerpo.detail === "string" ? cuerpo.detail : "";
  if (texto.startsWith("Los datos enviados están incompletos")) {
    const campos = texto.split("Revisa:")[1] || "";
    const lista = campos.replace(/\.$/, "").split(",").map((c) => CAMPOS_AMIGABLES[c.trim()] || c.trim()).filter(Boolean);
    return `Falta información o hay datos incorrectos en: ${lista.join(", ")}.`;
  }
  if (texto) return nombresEnTexto(texto);
  if (estado === 404) return "No encontramos lo que buscabas. Es posible que ya no exista.";
  if (estado === 403) return "Tu rol no tiene permiso para realizar esta acción.";
  if (estado >= 500) return "Algo salió mal de nuestro lado. Inténtalo de nuevo en unos minutos.";
  return "No pudimos completar la acción. Revisa los datos e inténtalo de nuevo.";
}

async function api(ruta, { metodo = "GET", cuerpo } = {}) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      method: metodo,
      headers: cuerpo ? { "Content-Type": "application/json" } : undefined,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
  } catch (_) {
    throw new Error("No hay conexión con el sistema. Revisa que esté encendido e inténtalo de nuevo.");
  }
  let datos = null;
  try { datos = await respuesta.json(); } catch (_) { /* respuesta sin contenido */ }
  if (!respuesta.ok) throw new Error(mensajeDeError(datos, respuesta.status));
  return datos;
}

// ---------- Avisos, ventanas y diálogos ----------
function aviso(texto, tipo = "ok") {
  const caja = $("#avisos");
  const nodo = document.createElement("div");
  nodo.className = `aviso ${tipo}`;
  nodo.innerHTML = `${ic(tipo === "ok" ? "check" : "alert")}<div>${esc(texto)}</div>`;
  caja.appendChild(nodo);
  setTimeout(() => nodo.remove(), tipo === "ok" ? 4500 : 7000);
}

function actualizarScroll() {
  document.body.classList.toggle("sin-scroll", document.querySelectorAll(".modal-fondo").length > 0);
}
function crearModal(html, { ancho = false, nivel = 1 } = {}) {
  const fondo = document.createElement("div");
  fondo.className = `modal-fondo${nivel > 1 ? " nivel2" : ""}`;
  fondo.innerHTML = `<div class="modal${ancho ? " ancho" : ""}" role="dialog" aria-modal="true">${html}</div>`;
  fondo.addEventListener("mousedown", (e) => { if (e.target === fondo) cerrarModal(fondo); });
  document.body.appendChild(fondo);
  actualizarScroll();
  const primero = fondo.querySelector("input:not([type=hidden]), textarea, select, .btn.primario");
  if (primero) primero.focus({ preventScroll: true });
  return fondo;
}
function cerrarModal(fondo) {
  if (!fondo) return;
  if (S.modalPedido === fondo) S.modalPedido = null;
  fondo.remove();
  actualizarScroll();
}
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  const ventanas = document.querySelectorAll(".modal-fondo");
  if (ventanas.length) cerrarModal(ventanas[ventanas.length - 1]);
});

function cabeceraModal(titulo, subtitulo = "") {
  return `<div class="modal-cabeza"><div><h2>${titulo}</h2>${subtitulo ? `<p>${subtitulo}</p>` : ""}</div>
    <button class="cerrar" data-act="cerrar" aria-label="Cerrar">${ic("x")}</button></div>`;
}
function errorEnModal(fondo, texto) {
  let caja = $(".error-form", fondo);
  if (!caja) {
    caja = document.createElement("div");
    caja.className = "alerta error error-form";
    caja.setAttribute("role", "alert");
    $(".modal-pie", fondo).before(caja);
  }
  caja.innerHTML = `${ic("alert")}<div>${esc(texto)}</div>`;
}

function confirmar({ titulo, texto, boton = "Aceptar", peligro = false }) {
  return new Promise((resolver) => {
    const fondo = crearModal(`${cabeceraModal(esc(titulo))}<p>${esc(texto)}</p>
      <div class="modal-pie">
        <button class="btn" data-resp="no">Volver</button>
        <button class="btn ${peligro ? "peligro" : "primario"}" data-resp="si">${esc(boton)}</button>
      </div>`, { nivel: 2 });
    const terminar = (valor) => { cerrarModal(fondo); resolver(valor); };
    fondo.addEventListener("click", (e) => {
      const b = e.target.closest("[data-resp],[data-act=cerrar]");
      if (!b) return;
      e.stopPropagation();
      terminar(b.dataset.resp === "si");
    });
    new MutationObserver((_, obs) => { if (!fondo.isConnected) { obs.disconnect(); resolver(false); } })
      .observe(document.body, { childList: true });
  });
}

// ---------- Carga de datos ----------
async function cargarBase() {
  const [clientes, platillos, pedidos] = await Promise.all([api("/clientes"), api("/platillos"), api("/pedidos")]);
  S.clientes = clientes;
  S.platillos = platillos;
  S.pedidos = pedidos;
  actualizarInsignias();
}
async function recargarPedidos() { S.pedidos = await api("/pedidos"); actualizarInsignias(); }
async function recargarPlatillos() { S.platillos = await api("/platillos"); }

function actualizarInsignias() {
  const activos = S.pedidos.filter((p) => ["Registrado", "En preparación", "Listo"].includes(p.estado)).length;
  const enlace = $('.menu a[data-vista="pedidos"]');
  if (!enlace) return;
  $(".insignia", enlace)?.remove();
  if (activos > 0) enlace.insertAdjacentHTML("beforeend", `<span class="insignia" title="Pedidos en curso">${activos}</span>`);
}

// ---------- Piezas de pantalla ----------
function encabezado(titulo, subtitulo, acciones = "") {
  return `<header class="encabezado"><div><h1>${esc(titulo)}</h1>${subtitulo ? `<p>${esc(subtitulo)}</p>` : ""}</div>
    ${acciones ? `<div class="acciones">${acciones}</div>` : ""}</header>`;
}
const cargando = (texto = "Cargando información…") => `<div class="cargando"><div class="giro"></div>${esc(texto)}</div>`;
const vacio = (titulo, texto, icono = "info") => `<div class="vacio">${ic(icono)}<strong>${esc(titulo)}</strong>${esc(texto)}</div>`;
function errorDePantalla(texto) {
  return `<div class="tarjeta">${vacio("No pudimos cargar esta sección", texto, "alert")}
    <div style="text-align:center"><button class="btn primario" data-act="reintentar">Intentar de nuevo</button></div></div>`;
}

function lineasDeRevision(ev, estado = "Registrado") {
  const lista = [];
  if (estado === "Registrado") { // solo tiene sentido mientras el pedido no ha empezado a prepararse
    if (ev.puede_procesarse) {
      lista.push({ tipo: "si", texto: "Puede pasar a preparación: el cliente está activo, el pedido tiene productos y está autorizado." });
    } else {
      const motivos = (ev.motivos_puede_procesarse || []).map(cap).join("; ");
      lista.push({ tipo: "no", texto: `Todavía no puede pasar a preparación. ${motivos}.` });
    }
  }
  if (ev.beneficio_referencia) {
    lista.push({ tipo: "si", texto: `Este cliente preferente tiene derecho a un beneficio por su compra de ${dinero(ev.total)}.` });
  } else {
    const motivos = (ev.motivos_beneficio_referencia || []).map(cap).join("; ");
    lista.push({ tipo: "neutro", texto: `No aplica beneficio para clientes preferentes. ${motivos}.` });
  }
  return lista;
}
function htmlRevision(ev, estado = "Registrado") {
  return `<ul class="revision">${lineasDeRevision(ev, estado).map((l) =>
    `<li><span class="${l.tipo}">${ic(l.tipo === "si" ? "check" : l.tipo === "no" ? "x" : "info")}</span><span>${esc(l.texto)}</span></li>`).join("")}</ul>`;
}

function detalleLegible(r) {
  const d = r.detalle || "";
  if (r.accion === "REGISTRAR_PEDIDO") {
    const m = d.match(/^Total ([\d.,]+) MXN\.\s*(.*)$/);
    if (m) {
      const productos = m[2].split("; ").map((x) => {
        const k = x.match(/^(PED-\w+) x(\d+)(?: \((.*)\))?$/);
        return k ? `${k[2]} × ${nombreProducto(k[1])}${k[3] ? ` (${k[3]})` : ""}` : nombresEnTexto(x);
      });
      return `Total del pedido: ${dinero(m[1])}. Productos: ${productos.join(", ")}.`;
    }
  }
  if (r.accion === "AJUSTE_INVENTARIO") {
    const m = d.match(/^(entrada|merma) de (\d+) en «(.+?)»\.?\s*(.*)$/);
    if (m) {
      const que = m[1] === "entrada" ? "Entraron" : "Se dieron de baja";
      return `${que} ${unidades(m[2])} de ${nombresEnTexto(m[3])}.${m[4] ? ` Motivo: ${m[4]}` : ""}`;
    }
  }
  if (r.accion === "STOCK_CRITICO") {
    const m = d.match(/^«(.+?)» quedó con (\d+) unidades?\.?$/);
    if (m) return `Quedan solo ${unidades(m[2])} de ${nombresEnTexto(m[1])}. Conviene reabastecer.`;
  }
  return nombresEnTexto(d);
}

function itemHistorial(r, { conEnlace = true } = {}) {
  const v = ACCIONES_HISTORIAL[r.accion] || { texto: cap(r.accion.toLowerCase().replace(/_/g, " ")), icono: "info", clase: "e-gris" };
  const quien = cap(r.usuario || "sistema") + (r.rol ? ` (${r.rol})` : "");
  const enlace = conEnlace && r.pedido_id && S.pedidos.some((p) => p.id === r.pedido_id)
    ? ` · <button class="btn-texto" data-act="ver-pedido" data-id="${esc(r.pedido_id)}">Ver pedido</button>` : "";
  return `<li>
    <div class="marca-hist etiqueta sin-punto ${v.clase}" style="padding:0">${ic(v.icono)}</div>
    <div>
      <div class="titulo">${esc(v.texto)}${r.pedido_id ? ` <span class="tenue">· Pedido ${esc(r.pedido_id)}</span>` : ""}</div>
      ${r.detalle && !ACCIONES_SIN_DETALLE.includes(r.accion) ? `<div class="detalle">${esc(detalleLegible(r))}</div>` : ""}
      <div class="meta">${esc(fechaHora(r.fecha))} · Realizado por ${esc(quien)}${enlace}</div>
    </div></li>`;
}

// ==========================================================================
// VISTA: INICIO
// ==========================================================================
async function vistaInicio() {
  const [resumen] = await Promise.all([api("/reportes/resumen"), recargarPlatillos(), recargarPedidos()]);
  const por = resumen.pedidos_por_estado;
  const enCurso = por["Registrado"] + por["En preparación"] + por["Listo"];
  const total = Object.values(por).reduce((a, b) => a + b, 0);
  const atencion = S.platillos.filter((p) => ["pocas", "agotado", "nodisponible"].includes(situacionPlatillo(p).clave));
  const porEntregar = por["Listo"];

  const entregados = resumen.ventas.pedidos_entregados;
  const frases = [
    `Hasta ahora se ${entregados === 1 ? "ha entregado <strong>1</strong> pedido" : `han entregado <strong>${entregados}</strong> pedidos`}, con ventas por <strong>${dinero(resumen.ventas.total_mxn)}</strong>.`,
    enCurso ? `Hay <strong>${enCurso}</strong> ${enCurso === 1 ? "pedido en curso" : "pedidos en curso"}${por["Registrado"] ? `; ${por["Registrado"] === 1 ? "<strong>1</strong> espera a que cocina lo empiece" : `<strong>${por["Registrado"]}</strong> esperan a que cocina los empiece`}` : ""}.` : "No hay pedidos pendientes por atender.",
    atencion.length ? `${atencion.length === 1 ? "<strong>1</strong> producto necesita" : `<strong>${atencion.length}</strong> productos necesitan`} tu atención en el inventario.` : "Todos los productos tienen existencias suficientes.",
  ];

  const filas = ESTADOS.map((e) => {
    const n = por[e] || 0;
    const pct = total ? Math.round((n / total) * 100) : 0;
    return `<div class="barra-fila"><div class="cabeza"><span>${etiquetaEstado(e)}</span><strong>${n} <span class="tenue">(${pct}%)</span></strong></div>
      <div class="pista"><div class="relleno c-${ESTADO_VISUAL[e].clase}" style="width:${pct}%"></div></div></div>`;
  }).join("");

  const alertas = atencion.length
    ? `<ul class="lista-simple">${atencion.slice(0, 7).map((p) => {
        const s = situacionPlatillo(p);
        const detalle = s.clave === "nodisponible" ? "Deshabilitado en el menú" : s.clave === "agotado" ? "Sin existencias" : `Quedan ${unidades(p.stock)}`;
        return `<li><div><strong>${esc(p.descripcion)}</strong><div class="tenue">${detalle}</div></div><span class="etiqueta ${s.clase}">${s.texto}</span></li>`;
      }).join("")}</ul>${atencion.length > 7 ? `<p class="tenue" style="margin-top:8px">Y ${atencion.length - 7} más en la sección de inventario.</p>` : ""}`
    : `<div class="alerta ok">${ic("check")}<div>Todo en orden: no hay productos agotados ni con pocas existencias.</div></div>`;

  const ranking = [...resumen.inventario].sort((a, b) => b.unidades_vendidas - a.unidades_vendidas || a.descripcion.localeCompare(b.descripcion)).slice(0, 8);
  const hayVentas = ranking.some((r) => r.unidades_vendidas > 0);
  const tabla = `<div class="tabla-caja" style="box-shadow:none"><table><thead><tr><th>Producto</th><th class="num">Vendidos</th><th class="num">En existencia</th></tr></thead><tbody>
    ${ranking.map((r) => `<tr><td>${esc(r.descripcion)}</td><td class="num">${r.unidades_vendidas}</td><td class="num">${r.stock}${r.stock_critico ? ' <span class="etiqueta e-aviso sin-punto">Pocas</span>' : ""}</td></tr>`).join("")}
    </tbody></table></div>`;

  return `
    ${encabezado("Bienvenido a Sazón Urbano", "Así va el restaurante en este momento.")}
    <section class="saludo"><h2>Resumen general</h2><p>${frases.join(" ")}</p>
      <div class="acciones">
        <a class="btn primario" href="#/nuevo">${ic("plus")} Registrar un pedido</a>
        <a class="btn" href="#/pedidos">${ic("list")} Ver pedidos${porEntregar ? ` (${porEntregar} por entregar)` : ""}</a>
      </div></section>
    <div class="indicadores">
      <div class="indicador"><div class="icono e-ok">${ic("bag")}</div><div><div class="valor">${resumen.ventas.pedidos_entregados}</div><div class="nombre">Pedidos entregados</div></div></div>
      <div class="indicador"><div class="icono e-marca">${ic("money")}</div><div><div class="valor">${dinero(resumen.ventas.total_mxn)}</div><div class="nombre">Ventas totales</div></div></div>
      <div class="indicador"><div class="icono e-preparacion">${ic("flame")}</div><div><div class="valor">${enCurso}</div><div class="nombre">Pedidos en curso</div></div></div>
      <div class="indicador"><div class="icono ${atencion.length ? "e-error" : "e-gris"}">${ic("alert")}</div><div><div class="valor">${atencion.length}</div><div class="nombre">Productos que requieren atención</div></div></div>
    </div>
    <div class="dos-columnas">
      <section class="tarjeta"><h2>Pedidos según su avance</h2><p class="sub">Cuántos pedidos hay en cada etapa (${total} en total).</p><div class="barras">${filas}</div></section>
      <section class="tarjeta"><h2>Productos que requieren atención</h2><p class="sub">Los que tienen pocas existencias, están agotados o no se pueden ofrecer.</p>${alertas}
        <p style="margin-top:12px"><a class="btn-texto" href="#/inventario">Ir al inventario →</a></p></section>
    </div>
    <section class="tarjeta" style="margin-top:18px"><h2>Ventas frente a existencias</h2>
      <p class="sub">${hayVentas ? "Los productos más vendidos y cuántas unidades quedan. Solo se cuentan pedidos ya entregados." : "Todavía no hay pedidos entregados. Cuando se entreguen, aquí verás los productos más vendidos."}</p>${tabla}</section>`;
}

// ==========================================================================
// VISTA: NUEVO PEDIDO
// ==========================================================================
function vistaNuevo() {
  if (S.nuevo.resultado) return pantallaPedidoCreado();
  const n = S.nuevo;
  const categorias = ["Todas", ...new Set(S.platillos.map((p) => p.descripcion.split(" ")[0]))];
  const activos = S.clientes.filter((c) => c.activo);
  const inactivos = S.clientes.filter((c) => !c.activo);
  const opcion = (c) => `<option value="${esc(c.id)}"${n.cliente === c.id ? " selected" : ""}>${esc(c.nombre)} · ${esc(c.ciudad)}${c.es_preferente ? " · Preferente" : ""}</option>`;

  return `
    ${encabezado("Registrar un pedido", "Es muy sencillo: elige al cliente, agrega los productos y confirma.")}
    <div class="pedido-grid">
      <div>
        <section class="tarjeta">
          <div class="pasos-titulo"><span class="paso-num">1</span><h2>¿Quién hace el pedido?</h2></div>
          <div class="campo" style="margin-bottom:0">
            <label for="cliente">Cliente</label>
            <select id="cliente" data-in="cliente">
              <option value="">Selecciona un cliente…</option>
              ${activos.map(opcion).join("")}
              ${inactivos.length ? `<optgroup label="Clientes inactivos (no pueden hacer pedidos)">${inactivos.map((c) => `<option value="${esc(c.id)}" disabled>${esc(c.nombre)} · ${esc(c.ciudad)}</option>`).join("")}</optgroup>` : ""}
            </select>
            <div id="nota-cliente"></div>
          </div>
        </section>
        <section class="tarjeta">
          <div class="pasos-titulo"><span class="paso-num">2</span><h2>¿Qué va a ordenar?</h2></div>
          <div class="barra">
            <div class="buscador">${ic("search")}<input type="search" id="buscar-menu" data-in="buscar-menu" placeholder="Buscar un producto…" aria-label="Buscar un producto" value="${esc(n.texto)}"></div>
          </div>
          <div class="fichas" id="fichas-categoria" style="margin-bottom:16px">
            ${categorias.map((c) => `<button class="ficha${n.categoria === c ? " activa" : ""}" data-act="categoria" data-valor="${esc(c)}">${c === "Todas" ? "Todos" : esc(c) + "s"}</button>`).join("")}
          </div>
          <div class="menu-grid" id="menu-grid"></div>
        </section>
      </div>
      <aside class="tarjeta carrito" id="carrito" aria-label="Resumen del pedido"></aside>
    </div>`;
}

function pintarNotaCliente() {
  const caja = $("#nota-cliente");
  if (!caja) return;
  const c = clientePorId(S.nuevo.cliente);
  caja.innerHTML = c && c.es_preferente
    ? `<div class="alerta info" style="margin-top:6px">${ic("info")}<div><strong>Cliente preferente.</strong> Si su compra llega a ${dinero(1500)} y no tiene otra promoción, tendrá un beneficio.</div></div>`
    : `<span class="ayuda">Solo los clientes activos pueden hacer pedidos.</span>`;
}

function pintarMenu() {
  const caja = $("#menu-grid");
  if (!caja) return;
  const n = S.nuevo;
  const texto = n.texto.trim().toLowerCase();
  const lista = S.platillos.filter((p) =>
    (n.categoria === "Todas" || p.descripcion.startsWith(n.categoria)) && (!texto || p.descripcion.toLowerCase().includes(texto)));
  if (!lista.length) { caja.innerHTML = `<div style="grid-column:1/-1">${vacio("No encontramos productos", "Prueba con otra búsqueda o categoría.", "search")}</div>`; return; }
  caja.innerHTML = lista.map((p) => {
    const cant = n.carrito[p.id] || 0;
    const s = situacionPlatillo(p);
    const sinStock = !p.disponible;
    return `<article class="plato${cant ? " elegido" : ""}${sinStock ? " agotado" : ""}">
      <div class="nombre">${esc(p.descripcion)}</div>
      <div class="precio">${dinero(p.precio)}</div>
      <div>${sinStock ? `<span class="etiqueta ${s.clase}">${s.texto === "No disponible" ? "No disponible por falta de ingredientes" : s.texto}</span>`
        : `<span class="tenue">${s.clave === "pocas" ? `<strong style="color:var(--aviso)">Quedan solo ${p.stock}</strong>` : `Quedan ${p.stock}`}</span>`}</div>
      <div class="pie">${sinStock ? `<span class="tenue">No se puede agregar</span>` : cant
        ? `<div class="cantidad"><button data-act="menos" data-id="${esc(p.id)}" aria-label="Quitar uno de ${esc(p.descripcion)}">${ic("minus")}</button><span aria-live="polite">${cant}</span><button data-act="mas" data-id="${esc(p.id)}" aria-label="Agregar uno de ${esc(p.descripcion)}"${cant >= p.stock ? " disabled" : ""}>${ic("plus")}</button></div>`
        : `<button class="btn chico primario" data-act="mas" data-id="${esc(p.id)}">${ic("plus")} Agregar</button>`}</div>
    </article>`;
  }).join("");
}

function totalCarrito() {
  return Object.entries(S.nuevo.carrito).reduce((suma, [id, c]) => suma + c * Number(platilloPorId(id)?.precio || 0), 0);
}

function pintarCarrito() {
  const caja = $("#carrito");
  if (!caja) return;
  const n = S.nuevo;
  const items = Object.entries(n.carrito).filter(([, c]) => c > 0);
  const unidadesTotales = items.reduce((a, [, c]) => a + c, 0);
  const lineas = items.map(([id, c]) => {
    const p = platilloPorId(id);
    return `<div class="linea"><div class="linea-top"><span>${c} × ${esc(p.descripcion)}</span><span>${dinero(c * Number(p.precio))}</span></div>
      <div class="tenue">${dinero(p.precio)} cada uno</div>
      <input type="text" data-in="nota" data-id="${esc(id)}" value="${esc(n.notas[id] || "")}" maxlength="120" placeholder="Indicaciones (ej. sin cebolla)" aria-label="Indicaciones para ${esc(p.descripcion)}"></div>`;
  }).join("");
  caja.innerHTML = `
    <div class="pasos-titulo"><span class="paso-num">3</span><h2>Resumen del pedido</h2></div>
    ${items.length ? `<div>${lineas}</div>
      <div class="total-fila"><span>Total (${unidades(unidadesTotales)})</span><strong>${dinero(totalCarrito())}</strong></div>
      <p style="text-align:right;margin-bottom:12px"><button class="btn-texto" data-act="vaciar">Quitar todo</button></p>`
      : vacio("Aún no hay productos", "Agrega productos del menú y aparecerán aquí.", "bag")}
    <label class="interruptor"><input type="checkbox" data-in="autorizado"${n.autorizado ? " checked" : ""}><div><strong>El pedido está autorizado</strong><span>Si no lo está, no podrá pasar a preparación.</span></div></label>
    <label class="interruptor"><input type="checkbox" data-in="promo"${n.promo ? " checked" : ""}><div><strong>Tiene una promoción activa</strong><span>Márcalo si al cliente se le aplicó alguna promoción.</span></div></label>
    <div class="campo"><label for="referencia">Referencia (opcional)</label>
      <input type="text" id="referencia" data-in="referencia" maxlength="80" value="${esc(n.referencia)}" placeholder="Un dato adicional del pedido"></div>
    <button class="btn primario grande ancho" data-act="confirmar-pedido"${n.enviando ? " disabled" : ""}>${n.enviando ? "Registrando…" : `${ic("check")} Confirmar pedido`}</button>
    <p class="tenue" style="margin-top:10px;text-align:center">Se registrará a nombre de: ${esc(S.rol)}</p>`;
}

async function confirmarPedido() {
  const n = S.nuevo;
  const items = Object.entries(n.carrito).filter(([, c]) => c > 0);
  if (!n.cliente) return aviso("Antes de continuar, elige al cliente que hace el pedido.", "error");
  if (!items.length) return aviso("Agrega al menos un producto para poder registrar el pedido.", "error");
  n.enviando = true; pintarCarrito();
  try {
    const pedido = await api(`/pedidos?usuario=${encodeURIComponent(usuarioActual())}`, {
      metodo: "POST",
      cuerpo: {
        actor_id: n.cliente,
        lineas: items.map(([id, c]) => ({ platillo_id: id, cantidad: c,
          modificaciones: (n.notas[id] || "").split(",").map((t) => t.trim()).filter(Boolean) })),
        promocion_activa: n.promo, autorizado: n.autorizado, referencia: n.referencia.trim() || null,
      },
    });
    const evaluacion = await api(`/pedidos/${encodeURIComponent(pedido.id)}/evaluacion`).catch(() => null);
    n.resultado = { pedido, evaluacion };
    await Promise.all([recargarPedidos(), recargarPlatillos()]);
    aviso("¡Pedido registrado con éxito!");
    await renderVista();
    window.scrollTo(0, 0);
  } catch (e) {
    n.enviando = false; pintarCarrito();
    aviso(e.message, "error");
  }
}

function pantallaPedidoCreado() {
  const { pedido, evaluacion } = S.nuevo.resultado;
  return `
    ${encabezado("Pedido registrado", "")}
    <section class="tarjeta" style="max-width:720px;margin:0 auto">
      <div class="exito"><div class="sello">${ic("check")}</div><h2>¡Listo! El pedido quedó registrado</h2>
        <p class="tenue">Número de pedido: <strong>${esc(pedido.id)}</strong></p></div>
      <div class="datos" style="margin-top:20px">
        <div class="dato"><small>Cliente</small><div>${esc(nombreCliente(pedido.actor_id))}</div></div>
        <div class="dato"><small>Estado</small><div>${etiquetaEstado(pedido.estado)}</div></div>
        <div class="dato"><small>Total a pagar</small><div>${dinero(pedido.total)}</div></div>
      </div>
      ${tablaProductos(pedido)}
      ${evaluacion ? `<div class="seccion-modal"><h3>Revisión automática</h3>${htmlRevision(evaluacion)}</div>` : ""}
      <div class="modal-pie" style="justify-content:center">
        <button class="btn" data-act="otro-pedido">${ic("plus")} Registrar otro pedido</button>
        <button class="btn primario" data-act="ver-pedido" data-id="${esc(pedido.id)}">Ver el pedido</button>
      </div>
    </section>`;
}

function tablaProductos(pedido) {
  return `<div class="tabla-caja" style="box-shadow:none"><table><thead><tr><th>Producto</th><th class="num">Cantidad</th><th class="num">Precio</th><th class="num">Subtotal</th></tr></thead><tbody>
    ${pedido.lineas.map((l) => `<tr><td>${esc(nombreProducto(l.platillo_id))}${l.modificaciones.length ? `<div class="tenue">Indicaciones: ${esc(l.modificaciones.join(", "))}</div>` : ""}</td>
      <td class="num">${l.cantidad}</td><td class="num">${dinero(l.precio_unitario)}</td><td class="num">${dinero(l.subtotal)}</td></tr>`).join("")}
    <tr><td colspan="3" class="num"><strong>Total</strong></td><td class="num"><strong>${dinero(pedido.total)}</strong></td></tr>
    </tbody></table></div>`;
}

// ==========================================================================
// VISTA: PEDIDOS
// ==========================================================================
const POR_PAGINA = 12;

function pedidosFiltrados() {
  const f = S.filtroPedidos;
  const texto = f.texto.trim().toLowerCase();
  return S.pedidos
    .filter((p) => f.estado === "Todos" || p.estado === f.estado)
    .filter((p) => !texto || p.id.toLowerCase().includes(texto) || nombreCliente(p.actor_id).toLowerCase().includes(texto)
      || resumenProductos(p).toLowerCase().includes(texto))
    .sort((a, b) => b.fecha_solicitud.localeCompare(a.fecha_solicitud) || b.id.localeCompare(a.id));
}

async function vistaPedidos() {
  await recargarPedidos();
  const f = S.filtroPedidos;
  const conteo = (e) => (e === "Todos" ? S.pedidos.length : S.pedidos.filter((p) => p.estado === e).length);
  return `
    ${encabezado("Pedidos", "Consulta el avance de cada pedido y avanza al siguiente paso con un clic.",
      `<a class="btn primario" href="#/nuevo">${ic("plus")} Nuevo pedido</a>`)}
    <div class="barra">
      <div class="buscador">${ic("search")}<input type="search" id="buscar-pedido" data-in="buscar-pedido" value="${esc(f.texto)}" placeholder="Buscar por número, cliente o producto…" aria-label="Buscar pedidos"></div>
    </div>
    <div class="fichas" style="margin-bottom:16px" id="fichas-estado">
      ${["Todos", ...ESTADOS].map((e) => `<button class="ficha${f.estado === e ? " activa" : ""}" data-act="filtro-estado" data-valor="${esc(e)}">${esc(e)}<small>${conteo(e)}</small></button>`).join("")}
    </div>
    ${f.estado !== "Todos" ? `<p class="tenue" style="margin-bottom:12px">${esc(ESTADO_VISUAL[f.estado].ayuda)}</p>` : ""}
    <div id="lista-pedidos"></div>`;
}

function pintarListaPedidos() {
  const caja = $("#lista-pedidos");
  if (!caja) return;
  const f = S.filtroPedidos;
  const lista = pedidosFiltrados();
  const paginas = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
  if (f.pagina > paginas) f.pagina = paginas;
  const visibles = lista.slice((f.pagina - 1) * POR_PAGINA, f.pagina * POR_PAGINA);
  if (!lista.length) { caja.innerHTML = `<div class="tarjeta">${vacio("No hay pedidos para mostrar", "Cambia el filtro o la búsqueda, o registra un pedido nuevo.", "list")}</div>`; return; }
  caja.innerHTML = `<div class="tabla-caja"><table><thead><tr><th>Pedido</th><th>Cliente</th><th class="col-productos">Productos</th><th class="num">Total</th><th>Estado</th><th></th></tr></thead><tbody>
    ${visibles.map((p) => {
      const paso = SIGUIENTE_PASO[p.estado];
      return `<tr class="clic" data-act="ver-pedido" data-id="${esc(p.id)}">
        <td><div class="id-pedido">${esc(p.id)}</div><div class="tenue">${esc(soloFecha(p.fecha_solicitud))}</div></td>
        <td>${esc(nombreCliente(p.actor_id))}${clientePorId(p.actor_id)?.es_preferente ? ' <span class="etiqueta e-marca sin-punto">Preferente</span>' : ""}</td>
        <td class="col-productos"><div class="resumen-productos" title="${esc(resumenProductos(p))}">${esc(resumenProductos(p))}</div></td>
        <td class="num"><strong>${dinero(p.total)}</strong></td>
        <td>${etiquetaEstado(p.estado)}</td>
        <td class="num"><div class="acciones-fila">${paso ? `<button class="btn chico primario" data-act="avanzar" data-id="${esc(p.id)}">${esc(paso.etiqueta)}</button>` : ""}<button class="btn chico" data-act="ver-pedido" data-id="${esc(p.id)}">Ver detalle</button></div></td></tr>`;
    }).join("")}</tbody></table></div>
    <div class="paginacion"><span>Mostrando ${(f.pagina - 1) * POR_PAGINA + 1}–${(f.pagina - 1) * POR_PAGINA + visibles.length} de ${lista.length} pedidos</span>
      <span><button class="btn chico" data-act="pagina" data-valor="-1"${f.pagina <= 1 ? " disabled" : ""}>← Anterior</button>
      <span style="margin:0 10px">Página ${f.pagina} de ${paginas}</span>
      <button class="btn chico" data-act="pagina" data-valor="1"${f.pagina >= paginas ? " disabled" : ""}>Siguiente →</button></span></div>`;
}

// ---- Detalle de un pedido (ventana) ----
async function abrirPedido(id) {
  if (!S.modalPedido) S.modalPedido = crearModal(cargando("Abriendo pedido…"), { ancho: true });
  const modal = $(".modal", S.modalPedido);
  try {
    const [pedido, evaluacion, historial] = await Promise.all([
      api(`/pedidos/${encodeURIComponent(id)}`),
      api(`/pedidos/${encodeURIComponent(id)}/evaluacion`),
      api(`/auditoria?pedido_id=${encodeURIComponent(id)}`),
    ]);
    if (!S.modalPedido) return;
    modal.innerHTML = htmlDetallePedido(pedido, evaluacion, historial);
  } catch (e) {
    modal.innerHTML = `${cabeceraModal("No se pudo abrir el pedido")}<div class="alerta error">${ic("alert")}<div>${esc(e.message)}</div></div>`;
  }
}

function htmlDetallePedido(p, ev, historial) {
  const c = clientePorId(p.actor_id);
  const paso = SIGUIENTE_PASO[p.estado];
  const cancelado = p.estado === "Cancelado";
  const etapas = ["Registrado", "En preparación", "Listo", "Entregado"];
  const indice = etapas.indexOf(p.estado);
  const lineaDeAvance = cancelado
    ? `<div class="alerta error">${ic("x")}<div><strong>Este pedido fue cancelado.</strong><br>Motivo: ${esc(p.motivo_cancelacion || "No se indicó")}</div></div>`
    : `<div class="pasos" aria-label="Avance del pedido">${etapas.map((e, i) => {
        const hecho = i < indice || p.estado === "Entregado";
        const clase = hecho ? "hecho" : i === indice ? "actual" : "";
        return `<div class="paso ${clase}"><div class="punto">${hecho ? ic("check") : ""}</div>${e}</div>`;
      }).join("")}</div>
       <p class="tenue" style="margin-bottom:18px">${esc(ESTADO_VISUAL[p.estado].ayuda)}</p>`;
  const puedeCancelarEste = ["Registrado", "En preparación", "Listo"].includes(p.estado);

  return `
    ${cabeceraModal(`Pedido ${esc(p.id)}`, `Registrado el ${esc(soloFecha(p.fecha_solicitud))}`)}
    ${lineaDeAvance}
    <div class="datos">
      <div class="dato"><small>Cliente</small><div>${esc(nombreCliente(p.actor_id))}${c ? `<div class="tenue" style="font-weight:400">${esc(c.ciudad)}${c.es_preferente ? " · Cliente preferente" : ""}</div>` : ""}</div></div>
      <div class="dato"><small>Estado</small><div>${etiquetaEstado(p.estado)}</div></div>
      <div class="dato"><small>Total</small><div>${dinero(p.total)}</div></div>
      <div class="dato"><small>Autorización</small><div>${p.autorizado ? "Autorizado" : "Sin autorización"}</div></div>
      <div class="dato"><small>Promoción</small><div>${p.promocion_activa ? "Con promoción" : "Sin promoción"}</div></div>
      ${p.referencia ? `<div class="dato"><small>Referencia</small><div>${esc(p.referencia)}</div></div>` : ""}
    </div>
    ${tablaProductos(p)}
    <div class="seccion-modal"><h3>Revisión automática</h3>${htmlRevision(ev, p.estado)}</div>
    <div class="seccion-modal"><h3>Qué ha pasado con este pedido</h3>
      ${historial.length ? `<ul class="linea-tiempo">${historial.map((r) => itemHistorial(r, { conEnlace: false })).join("")}</ul>` : '<p class="tenue">Todavía no hay movimientos registrados.</p>'}</div>
    <div class="modal-pie">
      ${puedeCancelarEste ? (puedeCancelar()
        ? `<button class="btn peligro" data-act="cancelar" data-id="${esc(p.id)}">Cancelar pedido</button>`
        : `<span class="tenue" style="margin-right:auto;align-self:center;max-width:300px">Para cancelar necesitas el rol de Encargado o Gerente (cámbialo en el menú).</span>`)
        : ""}
      <button class="btn" data-act="cerrar">Cerrar</button>
      ${paso ? `<button class="btn primario" data-act="avanzar" data-id="${esc(p.id)}">${ic(paso.icono)} ${esc(paso.etiqueta)}</button>` : ""}
    </div>`;
}

async function avanzarPedido(id) {
  const pedido = S.pedidos.find((p) => p.id === id) || await api(`/pedidos/${encodeURIComponent(id)}`);
  const paso = SIGUIENTE_PASO[pedido.estado];
  if (!paso) return;
  if (paso.confirmar) {
    const ok = await confirmar({ titulo: "¿Entregar el pedido al cliente?",
      texto: `Al confirmar la entrega del pedido ${id}, los productos se descontarán del inventario. Esta acción no se puede deshacer.`,
      boton: "Sí, entregar" });
    if (!ok) return;
  }
  try {
    await api(`/pedidos/${encodeURIComponent(id)}/${paso.ruta}?usuario=${encodeURIComponent(usuarioActual())}`, { metodo: "POST" });
    aviso(paso.exito);
    await refrescarTrasCambio(id);
  } catch (e) {
    aviso(e.message, "error");
  }
}

async function refrescarTrasCambio(idPedido) {
  await Promise.all([recargarPedidos(), recargarPlatillos()]);
  if (S.vista === "pedidos") { await renderVista(); }
  if (S.vista === "inicio") { await renderVista(); }
  if (idPedido && S.modalPedido) await abrirPedido(idPedido);
}

function dialogoCancelar(id) {
  const fondo = crearModal(`${cabeceraModal("Cancelar el pedido " + esc(id), "Esta acción no se puede deshacer.")}
    <div class="campo"><label for="motivo">¿Por qué se cancela?</label>
      <textarea id="motivo" maxlength="200" placeholder="Por ejemplo: el cliente ya no quiso esperar"></textarea>
      <span class="ayuda">El motivo es obligatorio y quedará guardado en el historial. Se cancelará como: ${esc(S.rol)}.</span></div>
    <div class="modal-pie"><button class="btn" data-act="cerrar">Volver</button>
      <button class="btn peligro" data-enviar="1">Sí, cancelar pedido</button></div>`, { nivel: 2 });
  $("[data-enviar]", fondo).addEventListener("click", async (e) => {
    const motivo = $("#motivo", fondo).value.trim();
    if (!motivo) return errorEnModal(fondo, "Escribe el motivo de la cancelación para continuar.");
    e.currentTarget.disabled = true;
    try {
      await api(`/pedidos/${encodeURIComponent(id)}/cancelacion`, { metodo: "POST",
        cuerpo: { motivo, usuario: usuarioActual(), rol: S.rol } });
      cerrarModal(fondo);
      aviso("El pedido fue cancelado.");
      await refrescarTrasCambio(id);
    } catch (err) {
      e.currentTarget.disabled = false;
      errorEnModal(fondo, err.message);
    }
  });
}

// ==========================================================================
// VISTA: INVENTARIO
// ==========================================================================
async function vistaInventario() {
  await recargarPlatillos();
  const f = S.filtroInventario;
  const cuenta = (clave) => (clave === "todos" ? S.platillos.length : S.platillos.filter((p) => situacionPlatillo(p).clave === clave).length);
  const fichas = [["todos", "Todos"], ["disponible", "Disponibles"], ["pocas", "Pocas existencias"], ["agotado", "Agotados"], ["nodisponible", "No disponibles"]];
  return `
    ${encabezado("Inventario", "Consulta cuántas unidades hay de cada producto y registra entradas de mercancía o productos dados de baja.")}
    <div class="barra"><div class="buscador">${ic("search")}<input type="search" data-in="buscar-inventario" value="${esc(f.texto)}" placeholder="Buscar un producto…" aria-label="Buscar un producto"></div></div>
    <div class="fichas" style="margin-bottom:16px">${fichas.map(([k, t]) =>
      `<button class="ficha${f.situacion === k ? " activa" : ""}" data-act="filtro-inventario" data-valor="${k}">${t}<small>${cuenta(k)}</small></button>`).join("")}</div>
    <div id="lista-inventario"></div>`;
}

function pintarInventario() {
  const caja = $("#lista-inventario");
  if (!caja) return;
  const f = S.filtroInventario;
  const texto = f.texto.trim().toLowerCase();
  const lista = S.platillos.filter((p) => (f.situacion === "todos" || situacionPlatillo(p).clave === f.situacion)
    && (!texto || p.descripcion.toLowerCase().includes(texto)));
  if (!lista.length) { caja.innerHTML = `<div class="tarjeta">${vacio("No hay productos con ese filtro", "Prueba con otra búsqueda.", "box")}</div>`; return; }
  const maximo = Math.max(1, ...S.platillos.map((p) => p.stock));
  caja.innerHTML = `<div class="tabla-caja"><table><thead><tr><th>Producto</th><th class="num">Precio</th><th>Existencias</th><th>Situación</th><th></th></tr></thead><tbody>
    ${lista.map((p) => {
      const s = situacionPlatillo(p);
      const color = s.clave === "pocas" ? "#f59e0b" : s.clave === "agotado" ? "#ef4444" : "#22a05a";
      return `<tr><td><strong>${esc(p.descripcion)}</strong></td><td class="num">${dinero(p.precio)}</td>
        <td style="min-width:170px"><div><strong>${p.stock}</strong> <span class="tenue">${Number(p.stock) === 1 ? "unidad" : "unidades"}</span></div>
          <div class="barra-fila"><div class="pista" style="height:6px;margin-top:4px"><div class="relleno" style="width:${Math.max(2, Math.round((p.stock / maximo) * 100))}%;background:${color}"></div></div></div></td>
        <td><span class="etiqueta ${s.clase}">${s.texto}</span></td>
        <td class="num"><div class="acciones-fila"><button class="btn chico" data-act="entrada" data-id="${esc(p.id)}">${ic("plus")} Llegó mercancía</button>
          <button class="btn chico" data-act="merma" data-id="${esc(p.id)}">Dar de baja</button></div></td></tr>`;
    }).join("")}</tbody></table></div>`;
}

function dialogoAjuste(id, tipo) {
  const p = platilloPorId(id);
  const esEntrada = tipo === "entrada";
  const fondo = crearModal(`${cabeceraModal(esEntrada ? "Registrar llegada de mercancía" : "Dar de baja unidades", esc(p.descripcion) + " · Hay " + unidades(p.stock))}
    <p class="tenue" style="margin-bottom:14px">${esEntrada ? "Úsalo cuando llegan más unidades de este producto." : "Úsalo cuando se pierde, se daña o se echa a perder producto (a esto se le llama merma)."}</p>
    <div class="campo"><label for="cantidad">¿Cuántas unidades ${esEntrada ? "llegaron" : "se dan de baja"}?</label>
      <input type="number" id="cantidad" min="1" step="1" inputmode="numeric" placeholder="Ej. 5"><span class="ayuda" id="previa"></span></div>
    ${esEntrada ? "" : `<div class="campo"><label for="motivo-merma">¿Qué pasó?</label><input type="text" id="motivo-merma" maxlength="120" placeholder="Escribe el motivo">
      <div class="sugerencias">${["Se echó a perder", "Se cayó o se dañó", "Error de preparación", "Producto caducado"].map((t) => `<button type="button" class="ficha" data-sug="${t}">${t}</button>`).join("")}</div></div>`}
    <div class="modal-pie"><button class="btn" data-act="cerrar">Volver</button><button class="btn primario" data-enviar="1">${esEntrada ? "Registrar entrada" : "Dar de baja"}</button></div>`, { nivel: 2 });

  const cantidad = $("#cantidad", fondo);
  cantidad.addEventListener("input", () => {
    const n = parseInt(cantidad.value, 10);
    $("#previa", fondo).textContent = n > 0 ? `Después del cambio habrá ${unidades(esEntrada ? p.stock + n : Math.max(0, p.stock - n))}.` : "";
  });
  fondo.addEventListener("click", (e) => {
    const s = e.target.closest("[data-sug]");
    if (s) $("#motivo-merma", fondo).value = s.dataset.sug;
  });
  $("[data-enviar]", fondo).addEventListener("click", async (e) => {
    const n = Number(cantidad.value);
    const motivo = esEntrada ? "" : $("#motivo-merma", fondo).value.trim();
    if (!Number.isInteger(n) || n <= 0) return errorEnModal(fondo, "Escribe una cantidad entera mayor a cero.");
    if (!esEntrada && n > p.stock) return errorEnModal(fondo, `Solo hay ${unidades(p.stock)} de este producto; no puedes dar de baja más.`);
    if (!esEntrada && !motivo) return errorEnModal(fondo, "Cuéntanos qué pasó para poder dar de baja el producto.");
    e.currentTarget.disabled = true;
    try {
      await api("/inventario/ajustes", { metodo: "POST", cuerpo: { platillo_id: id, tipo, cantidad: n, motivo, usuario: usuarioActual() } });
      cerrarModal(fondo);
      aviso(esEntrada ? `Se registró la llegada de ${unidades(n)} de ${p.descripcion}.` : `Se dieron de baja ${unidades(n)} de ${p.descripcion}.`);
      await renderVista();
    } catch (err) {
      e.currentTarget.disabled = false;
      errorEnModal(fondo, err.message);
    }
  });
}

// ==========================================================================
// VISTA: HISTORIAL
// ==========================================================================
async function vistaHistorial() {
  await recargarPedidos();
  const h = S.historial;
  const ruta = h.pestana === "cancelaciones" ? "/cancelaciones" : "/auditoria";
  const registros = (await api(ruta)).slice().reverse();
  const texto = h.texto.trim().toLowerCase();
  const filtrados = registros.filter((r) => !texto
    || (ACCIONES_HISTORIAL[r.accion]?.texto || "").toLowerCase().includes(texto)
    || detalleLegible(r).toLowerCase().includes(texto) || (r.pedido_id || "").toLowerCase().includes(texto)
    || (r.usuario || "").toLowerCase().includes(texto));
  const visibles = filtrados.slice(0, h.limite);
  return `
    ${encabezado("Historial", "Aquí queda guardado todo lo que ocurre en el restaurante: quién hizo qué y cuándo. Nada se borra.")}
    <div class="fichas" style="margin-bottom:14px">
      <button class="ficha${h.pestana === "todo" ? " activa" : ""}" data-act="pestana-historial" data-valor="todo">Toda la actividad</button>
      <button class="ficha${h.pestana === "cancelaciones" ? " activa" : ""}" data-act="pestana-historial" data-valor="cancelaciones">Solo cancelaciones</button>
    </div>
    <div class="barra"><div class="buscador">${ic("search")}<input type="search" data-in="buscar-historial" value="${esc(h.texto)}" placeholder="Buscar por pedido, persona o descripción…" aria-label="Buscar en el historial"></div></div>
    <section class="tarjeta">
      ${visibles.length ? `<ul class="linea-tiempo">${visibles.map((r) => itemHistorial(r)).join("")}</ul>
        ${filtrados.length > visibles.length ? `<div style="text-align:center;margin-top:12px"><button class="btn" data-act="mas-historial">Mostrar más (${filtrados.length - visibles.length} restantes)</button></div>` : ""}`
        : vacio(h.pestana === "cancelaciones" ? "No hay cancelaciones" : "Todavía no hay actividad", h.texto ? "Prueba con otra búsqueda." : "Cuando se registren pedidos o movimientos, aparecerán aquí.", "clock")}
    </section>`;
}

// ==========================================================================
// Navegación y arranque
// ==========================================================================
const POST_RENDER = {
  nuevo: () => { pintarNotaCliente(); pintarMenu(); pintarCarrito(); },
  pedidos: pintarListaPedidos,
  inventario: pintarInventario,
};

async function renderVista() {
  const contenido = $("#contenido");
  const vista = S.vista;
  const desplazamiento = window.scrollY;
  document.querySelectorAll(".menu a").forEach((a) => {
    a.classList.toggle("activo", a.dataset.vista === vista);
    if (a.dataset.vista === vista) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  document.title = `${VISTAS[vista].titulo} · Sazón Urbano`;
  const html = { inicio: vistaInicio, nuevo: vistaNuevo, pedidos: vistaPedidos, inventario: vistaInventario, historial: vistaHistorial }[vista];
  const vistaPrevia = contenido.dataset.vista;
  if (vistaPrevia !== vista) contenido.innerHTML = cargando();
  try {
    if (vista === "nuevo" && !S.nuevo.resultado) await recargarPlatillos();
    const resultado = await html();
    if (S.vista !== vista) return; // el usuario ya cambió de sección
    contenido.innerHTML = resultado;
    contenido.dataset.vista = vista;
    POST_RENDER[vista]?.();
    if (vistaPrevia === vista) window.scrollTo(0, desplazamiento);
  } catch (e) {
    contenido.innerHTML = errorDePantalla(e.message);
    contenido.dataset.vista = vista;
  }
}

function rutaActual() {
  const clave = (location.hash.replace(/^#\/?/, "") || "inicio").split("?")[0];
  return VISTAS[clave] ? clave : "inicio";
}
function alCambiarRuta() {
  S.vista = rutaActual();
  document.querySelectorAll(".modal-fondo").forEach(cerrarModal);
  $("#contenido").dataset.vista = "";
  window.scrollTo(0, 0);
  renderVista();
}

function prepararMenu() {
  document.querySelectorAll(".menu a").forEach((a) => {
    a.innerHTML = `${ic(VISTAS[a.dataset.vista].icono)}<span>${VISTAS[a.dataset.vista].titulo}</span>`;
  });
  const selector = $("#selector-rol");
  selector.innerHTML = Object.keys(ROLES).map((r) => `<option${r === S.rol ? " selected" : ""}>${r}</option>`).join("");
  const ayuda = () => { $("#rol-ayuda").textContent = `${ROLES[S.rol]} Solo Encargado y Gerente pueden cancelar pedidos.`; };
  ayuda();
  selector.addEventListener("change", () => {
    S.rol = selector.value;
    localStorage.setItem("sazon_rol", S.rol);
    ayuda();
    aviso(`Ahora trabajas como ${S.rol}.`);
    if (S.modalPedido) { const id = $(".modal-cabeza h2", S.modalPedido)?.textContent.replace("Pedido ", ""); if (id) abrirPedido(id); }
    if (S.vista === "nuevo") pintarCarrito();
  });
}

// ---------- Eventos de clic ----------
const ACCIONES = {
  cerrar: (el) => cerrarModal(el.closest(".modal-fondo")),
  reintentar: () => arrancar(),
  "ver-pedido": (el) => abrirPedido(el.dataset.id),
  avanzar: (el, e) => { e.stopPropagation(); avanzarPedido(el.dataset.id); },
  cancelar: (el) => dialogoCancelar(el.dataset.id),
  mas: (el) => {
    const p = platilloPorId(el.dataset.id);
    const actual = S.nuevo.carrito[p.id] || 0;
    if (actual >= p.stock) return aviso(`Solo quedan ${unidades(p.stock)} de ${p.descripcion}.`, "error");
    S.nuevo.carrito[p.id] = actual + 1;
    pintarMenu(); pintarCarrito();
  },
  menos: (el) => {
    const id = el.dataset.id;
    const nuevo = (S.nuevo.carrito[id] || 0) - 1;
    if (nuevo <= 0) { delete S.nuevo.carrito[id]; delete S.nuevo.notas[id]; } else S.nuevo.carrito[id] = nuevo;
    pintarMenu(); pintarCarrito();
  },
  vaciar: () => { S.nuevo.carrito = {}; S.nuevo.notas = {}; pintarMenu(); pintarCarrito(); },
  categoria: (el) => {
    S.nuevo.categoria = el.dataset.valor;
    document.querySelectorAll("#fichas-categoria .ficha").forEach((b) => b.classList.toggle("activa", b === el));
    pintarMenu();
  },
  "confirmar-pedido": () => confirmarPedido(),
  "otro-pedido": () => { S.nuevo = reiniciarNuevo(); renderVista(); },
  "filtro-estado": (el) => { S.filtroPedidos.estado = el.dataset.valor; S.filtroPedidos.pagina = 1; renderVista(); },
  pagina: (el) => { S.filtroPedidos.pagina += Number(el.dataset.valor); pintarListaPedidos(); $("#fichas-estado")?.scrollIntoView({ block: "start" }); },
  "filtro-inventario": (el) => { S.filtroInventario.situacion = el.dataset.valor; renderVista(); },
  entrada: (el) => dialogoAjuste(el.dataset.id, "entrada"),
  merma: (el) => dialogoAjuste(el.dataset.id, "merma"),
  "pestana-historial": (el) => { S.historial.pestana = el.dataset.valor; S.historial.limite = 40; renderVista(); },
  "mas-historial": () => { S.historial.limite += 40; renderVista(); },
};
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (!el || el.closest(".modal-fondo[data-bloqueado]")) return;
  const accion = ACCIONES[el.dataset.act];
  if (accion) accion(el, e);
});

// ---------- Eventos de escritura ----------
let temporizador;
const retrasar = (fn) => { clearTimeout(temporizador); temporizador = setTimeout(fn, 180); };
const ENTRADAS = {
  cliente: (el) => { S.nuevo.cliente = el.value; pintarNotaCliente(); },
  "buscar-menu": (el) => { S.nuevo.texto = el.value; retrasar(pintarMenu); },
  nota: (el) => { S.nuevo.notas[el.dataset.id] = el.value; },
  autorizado: (el) => { S.nuevo.autorizado = el.checked; },
  promo: (el) => { S.nuevo.promo = el.checked; },
  referencia: (el) => { S.nuevo.referencia = el.value; },
  "buscar-pedido": (el) => { S.filtroPedidos.texto = el.value; S.filtroPedidos.pagina = 1; retrasar(pintarListaPedidos); },
  "buscar-inventario": (el) => { S.filtroInventario.texto = el.value; retrasar(pintarInventario); },
  "buscar-historial": (el) => {
    S.historial.texto = el.value; S.historial.limite = 40;
    retrasar(async () => { const foco = el.selectionStart; await renderVista(); const n = $('[data-in="buscar-historial"]'); if (n) { n.focus(); n.setSelectionRange(foco, foco); } });
  },
};
["input", "change"].forEach((tipo) => document.addEventListener(tipo, (e) => {
  const el = e.target.closest("[data-in]");
  if (!el) return;
  const esCaja = el.type === "checkbox" || el.tagName === "SELECT";
  if ((tipo === "change") !== esCaja) return;
  ENTRADAS[el.dataset.in]?.(el);
}));

async function arrancar() {
  $("#contenido").innerHTML = cargando("Conectando con el sistema…");
  try {
    await cargarBase();
  } catch (e) {
    $("#contenido").innerHTML = errorDePantalla(e.message);
    return;
  }
  alCambiarRuta();
}

prepararMenu();
window.addEventListener("hashchange", alCambiarRuta);
arrancar();
