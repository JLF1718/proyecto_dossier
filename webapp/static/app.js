const REFRESH_MS = 10 * 60 * 60 * 1000;
let ACCESS_KEY = sessionStorage.getItem("dossier_access_key") || "";

const urlParams = new URLSearchParams(window.location.search);
const queryKey = urlParams.get("k");
if (queryKey) {
  ACCESS_KEY = queryKey;
  sessionStorage.setItem("dossier_access_key", ACCESS_KEY);
  urlParams.delete("k");
  const cleaned = `${window.location.pathname}${urlParams.toString() ? `?${urlParams.toString()}` : ""}`;
  window.history.replaceState({}, "", cleaned);
}

function authHeaders() {
  const headers = {};
  if (ACCESS_KEY) {
    headers["x-access-key"] = ACCESS_KEY;
  }
  return headers;
}

function withAccessKey(url) {
  if (!ACCESS_KEY) return url;
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}k=${encodeURIComponent(ACCESS_KEY)}`;
}

async function postJson(url, payload) {
  const response = await fetch(withAccessKey(url), {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = Array.isArray(data.detail) ? data.detail.join(" | ") : data.detail || `Error ${response.status}`;
    throw new Error(detail);
  }

  return response.json();
}

function fmtNumber(n) {
  return new Intl.NumberFormat("es-MX").format(Number(n || 0));
}

function fmtPct(n) {
  return `${Number(n || 0).toFixed(1)}%`;
}

function makeCards(containerId, metrics) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const items = [
    ["Dossieres", fmtNumber(metrics.total_dossiers)],
    ["Liberados", fmtNumber(metrics.dossiers_liberados)],
    ["% Liberado", fmtPct(metrics.pct_liberado)],
    ["Peso Total (ton)", fmtNumber(metrics.peso_total)],
    ["Peso Liberado (ton)", fmtNumber(metrics.peso_liberado)],
    ["% Peso Liberado", fmtPct(metrics.pct_peso_liberado)],
  ];

  container.innerHTML = items
    .map(
      ([label, value]) =>
        `<article class="metric"><div class="label">${label}</div><div class="value">${value}</div></article>`
    )
    .join("");
}

function renderPosters(payload) {
  const wrap = document.getElementById("postersWrap");
  const count = document.getElementById("postersCount");
  if (!wrap || !count) return;

  const items = payload.items || [];
  count.textContent = `${payload.count || 0} poster(s) mostrados`;

  if (!items.length) {
    wrap.innerHTML = `<p class="muted">No hay posters HTML disponibles en output/tablas.</p>`;
    return;
  }

  wrap.innerHTML = items
    .map(
      (item, idx) => `
      <article class="poster-card">
        <div class="poster-head">
          <div class="poster-title">
            <strong>Poster principal ${idx + 1}</strong>
            <span class="muted">${item.name}</span>
          </div>
          <div class="poster-actions">
            <span class="muted">${new Date(item.updated_at).toLocaleString("es-MX")}</span>
            <a class="poster-link" href="${item.url}" target="_blank" rel="noopener noreferrer">Abrir limpio</a>
          </div>
        </div>
        <iframe class="poster-frame" src="${item.url}" loading="lazy" scrolling="no" title="${item.name}"></iframe>
      </article>
    `
    )
    .join("");

  autoResizePosters();
}

function computePosterHeight(frame) {
  try {
    const doc = frame.contentDocument || frame.contentWindow?.document;
    if (!doc) return;
    const body = doc.body;
    const html = doc.documentElement;
    const height = Math.max(
      body?.scrollHeight || 0,
      body?.offsetHeight || 0,
      html?.clientHeight || 0,
      html?.scrollHeight || 0,
      html?.offsetHeight || 0
    );
    if (height > 0) {
      frame.style.height = `${height + 24}px`;
    }
  } catch {
    // Si el contenido no se puede medir, se conserva la altura mínima CSS.
  }
}

function autoResizePosters() {
  const frames = document.querySelectorAll(".poster-frame");
  frames.forEach((frame) => {
    frame.addEventListener("load", () => {
      computePosterHeight(frame);
      window.setTimeout(() => computePosterHeight(frame), 500);
      window.setTimeout(() => computePosterHeight(frame), 1500);
    }, { once: true });
  });
}

async function getJson(url) {
  const response = await fetch(withAccessKey(url), { cache: "no-store", headers: { ...authHeaders() } });
  if (!response.ok) {
    throw new Error(`Error ${response.status} en ${url}`);
  }
  return response.json();
}

function initAccessPanel() {
  const accessPanel = document.getElementById("accessPanel");
  const accessForm = document.getElementById("accessForm");
  const accessInput = document.getElementById("accessKeyInput");
  const accessMessage = document.getElementById("accessMessage");

  if (!accessPanel || !accessForm || !accessInput || !accessMessage) return;

  const setProtected = (enabled) => {
    accessPanel.classList.toggle("hidden", !enabled);
  };

  window.__setProtectedView = setProtected;

  accessForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    ACCESS_KEY = accessInput.value.trim();
    sessionStorage.setItem("dossier_access_key", ACCESS_KEY);
    accessMessage.textContent = "Verificando clave...";
    try {
      await refreshAll();
      setProtected(false);
      accessMessage.textContent = "Acceso concedido.";
    } catch {
      setProtected(true);
      accessMessage.textContent = "Clave inválida o servicio no disponible.";
    }
  });
}

async function initForm() {
  const bloque = document.getElementById("bloque");
  const estatus = document.getElementById("estatus");
  const estatusFilter = document.getElementById("estatusFilter");
  const estatusActual = document.getElementById("estatusActual");
  const bloqueSearch = document.getElementById("bloqueSearch");
  const bloqueCount = document.getElementById("bloqueCount");
  const form = document.getElementById("baysaForm");
  const submitBtn = document.getElementById("submitBtn");
  const formMessage = document.getElementById("formMessage");
  let metaBloques = [];

  if (!bloque || !estatus || !estatusFilter || !estatusActual || !bloqueSearch || !bloqueCount || !form || !submitBtn || !formMessage) return;

  const syncCurrentStatus = () => {
    const selected = metaBloques.find((item) => item.BLOQUE === bloque.value);
    estatusActual.value = selected?.ESTATUS || "";
    if (selected?.ESTATUS) {
      estatus.value = selected.ESTATUS;
    }
  };

  const renderBloqueOptions = () => {
    const searchTerm = bloqueSearch.value.trim().toUpperCase();
    const filterValue = estatusFilter.value;

    const filtered = metaBloques.filter((item) => {
      const byStatus = !filterValue || item.ESTATUS === filterValue;
      const bySearch = !searchTerm || item.BLOQUE.toUpperCase().includes(searchTerm);
      return byStatus && bySearch;
    });

    bloque.innerHTML = filtered
      .map((item) => `<option value="${item.BLOQUE}">${item.BLOQUE}</option>`)
      .join("");

    bloqueCount.textContent = `${filtered.length} bloque(s) disponibles`;
    syncCurrentStatus();
  };

  const loadMeta = async () => {
    const meta = await getJson("/api/baysa-form-meta");
    metaBloques = [...(meta.bloques || [])].sort((a, b) => a.BLOQUE.localeCompare(b.BLOQUE, "es"));
    estatus.innerHTML = (meta.estatus_options || [])
      .map((item) => `<option value="${item}">${item}</option>`)
      .join("");

    estatusFilter.innerHTML = ["<option value=\"\">Todos</option>", ...(meta.estatus_options || []).map((item) => `<option value=\"${item}\">${item}</option>`)]
      .join("");

    renderBloqueOptions();
  };

  try {
    await loadMeta();
    bloque.addEventListener("change", syncCurrentStatus);
    bloqueSearch.addEventListener("input", renderBloqueOptions);
    estatusFilter.addEventListener("change", renderBloqueOptions);
  } catch (err) {
    formMessage.textContent = `No se pudo cargar el formulario: ${err.message}`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitBtn.disabled = true;
    formMessage.textContent = "Guardando cambio de estatus...";

    const payload = {
      bloque: document.getElementById("bloque").value.trim(),
      estatus: document.getElementById("estatus").value,
    };

    try {
      const result = await postJson("/api/baysa-block-status", payload);
      const regenMsg = result.regeneration?.ok ? " Poster actualizado." : " Datos guardados; revisa regeneracion.";
      formMessage.textContent = `${result.updated.bloque}: ${result.updated.estatus_anterior} -> ${result.updated.estatus_nuevo}.${regenMsg}`;
      await loadMeta();
      bloque.value = result.updated.bloque;
      estatusActual.value = result.updated.estatus_nuevo;
      await refreshAll();
    } catch (err) {
      formMessage.textContent = `Error: ${err.message}`;
    } finally {
      submitBtn.disabled = false;
    }
  });
}

async function refreshAll() {
  const healthBadge = document.getElementById("healthBadge");
  const lastRefresh = document.getElementById("lastRefresh");

  try {
    const [health, summary, posters] = await Promise.all([
      getJson("/api/health"),
      getJson("/api/summary"),
      getJson("/api/tablas-posters?limit=1"),
    ]);

    healthBadge.textContent = health.status === "ok" ? "Servicio activo" : "Servicio con problemas";
    makeCards("cardsBAYSA", summary.contractors?.BAYSA || {});
    renderPosters(posters);

    const now = new Date();
    lastRefresh.textContent = `Actualizado: ${now.toLocaleString("es-MX")}`;
    if (window.__setProtectedView) {
      window.__setProtectedView(false);
    }
  } catch (err) {
    if (String(err.message || "").includes("Error 401")) {
      healthBadge.textContent = "Acceso requerido";
      healthBadge.style.background = "#fff2e8";
      healthBadge.style.color = "#a55010";
      lastRefresh.textContent = "Autenticacion requerida para continuar.";
      if (window.__setProtectedView) {
        window.__setProtectedView(true);
      }
      throw err;
    }
    healthBadge.textContent = "No disponible";
    healthBadge.style.background = "#fdeaea";
    healthBadge.style.color = "#8c1f1f";
    lastRefresh.textContent = `Error: ${err.message}`;
    throw err;
  }
}

initAccessPanel();
refreshAll().catch(() => null);
initForm();
const refreshNow = document.getElementById("refreshNow");
if (refreshNow) {
  refreshNow.addEventListener("click", () => {
    refreshAll();
  });
}
setInterval(refreshAll, REFRESH_MS);
