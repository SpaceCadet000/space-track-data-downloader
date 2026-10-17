/*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT NAME: Space-Track Data Downloader
FILE:         app.js
PATH:         space-track-data-downloader/gui/static/app.js
AUTHOR:       Sooraj Suresh
DATE:         October 2026
VERSION:      1.1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION:  Single-page client for the local web GUI: API helper, hash router,
              sidebar and toolbar chrome, theme toggle, and the screens. Only
              the login form and the confirmed download dialog cause requests
              to Space-Track; every other call stays on this machine.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
*/

const TOKEN = document.querySelector('meta[name="gui-token"]').content;
const app = document.getElementById("app");

const state = {
  session: { logged_in: false, identity: null },
  catalog: null,
  datasets: new Map(),
  builds: new Map(),
  history: null,
};

// ============================================================================
// Helpers
// ============================================================================

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: { Accept: "application/json" } };

  if (method !== "GET") {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-GUI-Token"] = TOKEN;
    options.body = JSON.stringify(body ?? {});
  }

  let response;

  try {
    response = await fetch(path, options);
  } catch {
    throw new ApiError(0, "The local server is not responding. Is spacetrack_gui.py still running?");
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, data.error || `Request failed (${response.status}).`);
  }

  return data;
}

/** Create an element: h("div", {class: "x", onclick}, child, "text"). */
function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);

  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;

    if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2), value);
    } else if (key === "class") {
      el.className = value;
    } else if (key === "dataset") {
      Object.assign(el.dataset, value);
    } else if (value === true) {
      el.setAttribute(key, "");
    } else {
      el.setAttribute(key, value);
    }
  }

  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }

  return el;
}

const SVG_NS = "http://www.w3.org/2000/svg";

/** Thin line icons drawn inline. */
const ICONS = {
  copy: "M9 9h10v10H9zM5 15V5h10",
  close: "M6 6l12 12M18 6 6 18",
  plus: "M12 5v14M5 12h14",
  chevronRight: "M9 6l6 6-6 6",
  chevronLeft: "M15 6l-6 6 6 6",
  updown: "M8 10l4-4 4 4M8 14l4 4 4-4",
  sidebar: "M4 5h16v14H4zM9 5v14",
  sun: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  moon: "M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z",
};

function icon(name, size = 16) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", ICONS[name]);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.75");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

function primaryButton(label, attrs = {}) {
  return h("button", { class: "btn btn-primary", type: "button", ...attrs }, label);
}

/** A grouped inset list: optional heading, solid rounded body, optional footnote. */
function group(title, body, ...footer) {
  return h(
    "section",
    { class: "group" },
    title ? h("h2", { class: "group-title" }, title) : null,
    h("div", { class: "group-body" }, body),
    footer.flat().filter(Boolean).length ? h("div", { class: "group-foot" }, footer) : null,
  );
}

/** A settings row: label on the left, control on the right. */
function row(label, control, { forId, title, extra = "" } = {}) {
  return h(
    "div",
    { class: `row ${extra}`.trim() },
    label === null ? null : h(forId ? "label" : "span", { class: "row-label", for: forId, title }, label),
    h("div", { class: "row-control" }, control),
  );
}

function valueRow(label, value) {
  return h("div", { class: "row" }, h("span", { class: "row-label" }, label), h("span", { class: "row-value" }, value));
}

function switchRow(id, label, checked, onchange, { title, extra = "" } = {}) {
  const input = h("input", { class: "switch", type: "checkbox", role: "switch", id, checked, onchange: () => onchange(input.checked) });
  return { input, el: h("label", { class: `row row-switch ${extra}`.trim(), for: id, title }, h("span", { class: "row-label" }, label), input) };
}

function notice(kind, text) {
  return h("div", { class: `notice notice-${kind}`, role: kind === "error" ? "alert" : "note" }, text);
}

function setBusy(button, busy) {
  button.disabled = busy;
  button.setAttribute("aria-busy", busy ? "true" : "false");
}

let toastTimer;

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 2600);
}

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return "–";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unit = 0;

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }

  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function formatTime(iso) {
  if (!iso) return "–";
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// ============================================================================
// Display names (presentation only; the API labels stay the source of truth)
// ============================================================================

const SHORT_NAMES = {
  gp: "Latest GP",
  gp_history: "GP history",
  satcat: "SATCAT",
  satcat_change: "SATCAT changes",
  satcat_debut: "SATCAT debuts",
  launch_site: "Launch sites",
  decay: "Decay",
  tip: "TIP messages",
  cdm_public: "Public CDMs",
  boxscore: "Box score",
  publicfiles_dirs: "Directories",
  publicfiles_files: "Files",
  publicfiles_loadpublicdata: "File details",
  publicfiles_download: "Download a file",
};

const GROUP_NAMES = {
  object_elset: "Orbital elements",
  catalog: "Catalog",
  decay_reentry: "Decay & reentry",
  conjunctions: "Conjunctions",
  summary: "Summary",
  publicfiles: "Public files",
};

const FIELD_NAMES = {
  "Object type / object population": "Object type",
  "Country / owner filter": "Country / owner",
  "Radar cross-section size filter": "RCS size",
  "Advanced custom predicate/value filters": "Custom filters",
  "Use only current SATCAT records?": "Current records only",
  "Filter by on-orbit only using DECAY/null-val?": "On orbit only",
  "Filter high-interest TIPs only?": "High interest only",
  "Public file LINK/name value": "File LINK / name",
};

const shortName = (dataset) => SHORT_NAMES[dataset.key] || dataset.label;

function fieldName(field) {
  if (FIELD_NAMES[field.label]) return FIELD_NAMES[field.label];
  return field.label.split(", for example")[0].replace(/\?$/, "").replace(/\s+(value|filter)$/i, "").trim();
}

/** "PC value, for example >0.00001" → ">0.00001". */
function labelExample(field) {
  const match = /for example (.+)$/.exec(field.label);
  return match ? match[1] : "";
}

// ============================================================================
// Theme
// ============================================================================

const THEME_KEY = "spacetrack-gui-theme";

function storedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

function currentTheme() {
  const explicit = document.documentElement.dataset.theme;
  if (explicit) return explicit;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  const button = document.getElementById("theme-toggle");
  const next = currentTheme() === "dark" ? "light" : "dark";
  button.replaceChildren(icon(next === "light" ? "sun" : "moon"));
  button.setAttribute("aria-label", `Switch to ${next} theme`);
  button.title = `Switch to ${next} theme`;
}

document.getElementById("theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";

  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* Theme just won't persist. */
  }

  applyTheme(next);
});

// ============================================================================
// Sidebar and toolbar
// ============================================================================

const sidebarNav = document.getElementById("sidebar-nav");
const sidebarPill = document.getElementById("sidebar-pill");
let sidebarMode = null;

function navItem(key, href, label, title) {
  return h("a", { class: "nav-item", href, title: title || null, dataset: { navKey: key } }, label);
}

function navSection(heading, items) {
  return h("div", { class: "nav-section" }, heading ? h("div", { class: "nav-heading" }, heading) : null, items);
}

async function buildSidebar() {
  const mode = state.session.logged_in ? "in" : "out";
  if (sidebarMode === mode) return;

  const sections = [];

  if (mode === "in") {
    sections.push(navSection(null, [navItem("datasets", "#/datasets", "All datasets")]));

    try {
      for (const g of await loadCatalog()) {
        sections.push(navSection(GROUP_NAMES[g.key] || g.label, g.datasets.map((d) => navItem(d.key, `#/build/${encodeURIComponent(d.key)}`, shortName(d), d.label))));
      }
    } catch {
      /* The overview page shows the error; the sidebar keeps working without groups. */
    }

    sections.push(navSection("Library", [navItem("history", "#/history", "History")]));
  } else {
    sections.push(navSection(null, [navItem("login", "#/login", "Sign in"), navItem("history", "#/history", "History")]));
  }

  sidebarNav.replaceChildren(sidebarPill, ...sections);
  sidebarPill.classList.remove("visible");
  sidebarMode = mode;
}

/** Slide the selection pill to the item for `key`, or fade it out. */
function moveSidebarPill(key) {
  let active = null;

  for (const item of sidebarNav.querySelectorAll("[data-nav-key]")) {
    const on = item.dataset.navKey === key;
    item.classList.toggle("active", on);
    if (on) {
      item.setAttribute("aria-current", "page");
      active = item;
    } else {
      item.removeAttribute("aria-current");
    }
  }

  if (!active) {
    sidebarPill.classList.remove("visible");
    return;
  }

  // Appear in place the first time instead of sliding from the top.
  const appearing = !sidebarPill.classList.contains("visible");
  if (appearing) sidebarPill.classList.add("no-slide");
  sidebarPill.style.height = `${active.offsetHeight}px`;
  sidebarPill.style.transform = `translateY(${active.offsetTop}px)`;

  if (appearing) {
    void sidebarPill.offsetHeight;
    sidebarPill.classList.remove("no-slide");
  }

  sidebarPill.classList.add("visible");
  active.scrollIntoView?.({ block: "nearest" });
}

function setSidebarOpen(open) {
  document.body.classList.toggle("sidebar-open", open);
  document.getElementById("sidebar-toggle").setAttribute("aria-expanded", open ? "true" : "false");
}

document.getElementById("sidebar-toggle").append(icon("sidebar", 18));
document.getElementById("sidebar-toggle").addEventListener("click", () => setSidebarOpen(!document.body.classList.contains("sidebar-open")));
document.getElementById("scrim").addEventListener("click", () => setSidebarOpen(false));

const toolbar = document.getElementById("toolbar");
const updateToolbar = () => toolbar.classList.toggle("scrolled", window.scrollY > 2);
window.addEventListener("scroll", updateToolbar, { passive: true });

async function renderChrome() {
  const loggedIn = state.session.logged_in;
  document.getElementById("logout").hidden = !loggedIn;
  const label = document.getElementById("session-label");
  label.hidden = !loggedIn;
  label.textContent = loggedIn ? state.session.identity : "";
  label.title = loggedIn ? state.session.identity : "";
  await buildSidebar();
}

/** Put a view's title and actions in the toolbar and its body in the page. */
function showPage(page) {
  document.getElementById("page-title").textContent = page.title || "";
  document.title = page.title ? `${page.title} · Space-Track Downloader` : "Space-Track Downloader";
  document.getElementById("toolbar-lead").replaceChildren(page.back ? h("a", { class: "icon-btn back-btn", href: page.back.href, "aria-label": page.back.label, title: page.back.label }, icon("chevronLeft", 18)) : "");
  document.getElementById("toolbar-actions").replaceChildren(...(page.actions || []).filter(Boolean));
  app.replaceChildren(h("div", { class: `page page-enter ${page.className || ""}`.trim() }, page.body));
}

document.getElementById("logout").addEventListener("click", async () => {
  try {
    state.session = await api("/api/logout", { method: "POST" });
  } catch (error) {
    toast(error.message);
  }

  location.hash = "#/login";
});

function sessionExpired() {
  state.session = { logged_in: false, identity: null };
  toast("Your Space-Track session ended. Sign in again.");
  location.hash = "#/login";
}

// ============================================================================
// Login
// ============================================================================

function loginView() {
  const username = h("input", { class: "input input-bare", id: "username", name: "username", autocomplete: "username", required: true, spellcheck: "false", placeholder: "Required" });
  const password = h("input", { class: "input input-bare", id: "password", name: "password", type: "password", autocomplete: "current-password", required: true, placeholder: "Required" });
  const error = h("div", { class: "login-error", "aria-live": "assertive" });
  const submit = primaryButton("Sign In", { type: "submit", class: "btn btn-primary btn-wide" });

  const form = h(
    "form",
    {
      class: "login-form",
      novalidate: true,
      onsubmit: async (event) => {
        event.preventDefault();
        error.replaceChildren();

        if (!username.value.trim() || !password.value) {
          error.append(notice("error", "Enter your Space-Track username and password."));
          (username.value.trim() ? password : username).focus();
          return;
        }

        setBusy(submit, true);

        try {
          state.session = await api("/api/login", {
            method: "POST",
            body: { username: username.value.trim(), password: password.value },
          });
          password.value = "";
          location.hash = "#/datasets";
        } catch (err) {
          password.value = "";
          error.append(notice("error", err.message));
          password.focus();
        } finally {
          setBusy(submit, false);
        }
      },
    },
    h("div", { class: "group-body" }, row("Username", username, { forId: "username" }), row("Password", password, { forId: "password" })),
    error,
    submit,
  );

  const body = h(
    "div",
    { class: "login" },
    h(
      "div",
      { class: "login-card" },
      h("span", { class: "app-glyph app-glyph-large", "aria-hidden": "true" }),
      h("h2", {}, "Sign in to Space-Track"),
      h("p", { class: "muted" }, "Your password is sent only to space-track.org."),
      form,
      h("p", { class: "subtle" }, "No account? ", h("a", { href: "https://www.space-track.org/auth/createAccount", target: "_blank", rel: "noopener noreferrer" }, "Register for free")),
    ),
  );

  queueMicrotask(() => username.focus());
  return { title: "", body };
}

// ============================================================================
// Dataset picker
// ============================================================================

async function loadCatalog() {
  if (!state.catalog) state.catalog = (await api("/api/datasets")).groups;
  return state.catalog;
}

async function loadDataset(key) {
  if (!state.datasets.has(key)) state.datasets.set(key, await api(`/api/datasets/${encodeURIComponent(key)}`));
  return state.datasets.get(key);
}

async function datasetsView() {
  const groups = await loadCatalog();

  const listRow = (dataset) =>
    h(
      "a",
      { class: "list-row", href: `#/build/${encodeURIComponent(dataset.key)}` },
      h("span", { class: "row-text" }, h("span", { class: "row-title" }, shortName(dataset)), h("span", { class: "row-detail" }, dataset.description)),
      dataset.warning ? h("span", { class: "tag tag-warn", title: dataset.warning }, "Large") : null,
      h("span", { class: "chevron" }, icon("chevronRight", 14)),
    );

  return {
    title: "Datasets",
    body: groups.map((g) => group(GROUP_NAMES[g.key] || g.label, g.datasets.map(listRow))),
  };
}

// ============================================================================
// Filter builder
// ============================================================================

const OPTION_TOGGLES = [
  ["show_empty", "Show empty result", "Adds /emptyresult/show."],
  ["distinct", "Distinct rows only", "Adds /distinct/true."],
  ["metadata", "Include metadata", "Adds /metadata/true; ignored for CSV, TLE, 3LE and KVN."],
];

function newBuild(desc) {
  const gates = {};
  const values = {};

  for (const field of desc.fields) {
    if (field.gate) gates[field.id] = field.gate_default;
    if (field.id in desc.default_values) values[field.id] = desc.default_values[field.id];
    else if (field.default !== null) values[field.id] = field.default;
    else values[field.id] = field.kind === "custom" ? null : "";
  }

  return {
    gates,
    values,
    countryCustom: "",
    custom: [["", ""]],
    query: {
      output_format: desc.default_format,
      predicates: [],
      orderby: "",
      limit: "",
      offset: "",
      metadata: false,
      show_empty: true,
      distinct: false,
    },
    export: { download_dir: "", custom_name: "", overwrite: false, pretty_json: true },
  };
}

function getBuild(desc) {
  if (!state.builds.has(desc.key)) state.builds.set(desc.key, newBuild(desc));
  return state.builds.get(desc.key);
}

function formatInfo(desc, build) {
  return desc.formats.find((fmt) => fmt.key === build.query.output_format) || desc.formats[0];
}

function collectValues(desc, build) {
  const values = {};

  for (const field of desc.fields) {
    if (field.gate && !build.gates[field.id]) continue;

    if (field.kind === "flag") {
      values[field.id] = true;
    } else if (field.kind === "custom") {
      const pairs = build.custom.filter(([p, v]) => p.trim() || v.trim());
      if (pairs.length) values[field.id] = pairs;
    } else if (field.kind === "country" && build.values[field.id] === "custom") {
      values[field.id] = { preset: "custom", custom: build.countryCustom };
    } else {
      values[field.id] = build.values[field.id] ?? "";
    }
  }

  return values;
}

function queryPayload(desc, build) {
  const q = build.query;
  const limit = String(q.limit).trim();

  return {
    dataset_key: desc.key,
    values: collectValues(desc, build),
    query_options: {
      output_format: q.output_format,
      predicates: q.predicates.length ? q.predicates : null,
      orderby: q.orderby.trim() || null,
      limit: limit || null,
      offset: limit ? String(q.offset).trim() || null : null,
      metadata: q.metadata,
      show_empty: q.show_empty,
      distinct: q.distinct,
    },
  };
}

/** Turn a field's help text into example values for a datalist. */
function parseExamples(help) {
  if (!help) return [];

  return help
    .split("\n")
    .filter((line) => line.startsWith("  ") && !line.includes("Predicate:"))
    .map((line) => {
      const text = line.trim();
      const [value, ...rest] = text.split(" = ");
      return { value: value.trim(), title: rest.join(" = ") };
    });
}

/** Predicate and value suggestions from the custom-filter help ("Predicate: X  Value: Y"). */
function customSuggestions(help) {
  const predicates = new Set();
  const values = new Map([["null-val", "empty / not set"]]);

  for (const match of (help || "").matchAll(/Predicate:\s*(\S+)\s+Value:\s*(\S+)/g)) {
    predicates.add(match[1]);
    if (!values.has(match[2])) values.set(match[2], "");
  }

  return { predicates: [...predicates], values: [...values] };
}

/** An inline "null" → "null-val" hint under a filter input; previewGroup fills it. */
function hintSlot(slots, key) {
  const el = h("p", { class: "row-hint", role: "note", hidden: true });
  slots.set(key, el);
  return el;
}

function urlView(url) {
  const base = "https://www.space-track.org";
  const code = h("code", { class: "url" });

  if (url.startsWith(base)) code.append(h("span", { class: "url-base" }, base), url.slice(base.length));
  else code.append(url);

  return code;
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to the clipboard.");
  } catch {
    toast("Could not copy; select the text instead.");
  }
}

/**
 * The rows that hold a field's control. `label` is the left-hand label, or
 * null for an indented sub-row under a switch (the control then spans the row).
 */
function controlRows(field, build, onChange, label, slots) {
  const id = `f-${field.id}`;
  const extra = label ? "" : "row-sub row-full";
  const name = fieldName(field);

  if (["preset", "choice", "favorites", "country"].includes(field.kind)) {
    let customRow = null;

    const select = h(
      "select",
      {
        class: "select",
        id,
        "aria-label": label ? null : name,
        onchange: () => {
          build.values[field.id] = select.value;
          if (customRow) customRow.hidden = select.value !== "custom";
          onChange();
        },
      },
      field.options.map((opt) => h("option", { value: opt.key, selected: opt.key === build.values[field.id], title: opt.label }, opt.label.split(" - ")[0])),
    );

    const rows = [row(label, select, { forId: id, extra })];

    if (field.kind === "country") {
      const customInput = h("input", {
        class: "input",
        id: `${id}-custom`,
        value: build.countryCustom,
        placeholder: "Owner code, e.g. ISRA",
        autocapitalize: "characters",
        spellcheck: "false",
        oninput: () => {
          build.countryCustom = customInput.value;
          onChange();
        },
      });
      customRow = row("Custom code", customInput, { forId: `${id}-custom`, extra: "row-sub" });
      customRow.hidden = build.values[field.id] !== "custom";
      rows.push(customRow);
    }

    return rows;
  }

  if (field.kind === "text" || field.kind === "date") {
    const examples = parseExamples(field.help);
    const listId = examples.length ? `${id}-examples` : null;
    const input = h("input", {
      class: "input",
      id,
      list: listId,
      value: build.values[field.id] ?? "",
      placeholder: examples[0]?.value || labelExample(field),
      title: field.help && !examples.length ? field.help : null,
      "aria-label": label ? null : name,
      spellcheck: "false",
      autocomplete: "off",
      autocapitalize: field.uppercase ? "characters" : "off",
      oninput: () => {
        build.values[field.id] = input.value;
        onChange();
      },
    });
    const datalist = listId ? h("datalist", { id: listId }, examples.map((ex) => h("option", { value: ex.value, label: ex.title || null }))) : null;

    return [row(label, [input, datalist], { forId: id, extra }), hintSlot(slots, field.id)];
  }

  if (field.kind === "custom") {
    const list = h("div", { class: "row-stack" });
    const suggestions = customSuggestions(field.help);
    const predicateList = h("datalist", { id: `${id}-predicates` }, suggestions.predicates.map((p) => h("option", { value: p })));
    const valueList = h("datalist", { id: `${id}-values` }, suggestions.values.map(([v, title]) => h("option", { value: v, label: title || null })));

    const drawRows = () => {
      for (const key of [...slots.keys()]) if (key.startsWith(`${field.id}:`)) slots.delete(key);

      list.replaceChildren(
        ...build.custom.map((pair, index) => {
          const predicate = h("input", {
            class: "input",
            value: pair[0],
            list: `${id}-predicates`,
            autocomplete: "off",
            placeholder: "Predicate, e.g. PERIOD",
            "aria-label": `Custom filter ${index + 1} predicate`,
            spellcheck: "false",
            oninput: () => {
              pair[0] = predicate.value;
              onChange();
            },
          });
          const value = h("input", {
            class: "input",
            value: pair[1],
            list: `${id}-values`,
            autocomplete: "off",
            placeholder: "Value, e.g. 1430--1450",
            "aria-label": `Custom filter ${index + 1} value`,
            spellcheck: "false",
            oninput: () => {
              pair[1] = value.value;
              onChange();
            },
          });
          const remove = h(
            "button",
            {
              class: "icon-btn icon-btn-small",
              type: "button",
              "aria-label": `Remove custom filter ${index + 1}`,
              onclick: () => {
                build.custom.splice(index, 1);
                if (!build.custom.length) build.custom.push(["", ""]);
                drawRows();
                onChange();
              },
            },
            icon("close", 14),
          );
          return h("div", { class: "custom-pair" }, h("div", { class: "row row-sub row-custom" }, predicate, value, remove), hintSlot(slots, `${field.id}:${index}`));
        }),
      );
    };

    drawRows();

    const add = h(
      "button",
      {
        class: "btn btn-small btn-plain",
        type: "button",
        title: "Operators: , (or)  -- (range)  ~~ (wildcard)  < >  null-val",
        onclick: () => {
          build.custom.push(["", ""]);
          drawRows();
          list.lastElementChild?.querySelector("input")?.focus();
        },
      },
      icon("plus", 14),
      "Add filter",
    );

    return [list, h("div", { class: "row row-sub row-add" }, add, predicateList, valueList)];
  }

  return [];
}

function fieldRows(field, build, onChange, slots) {
  if (!field.gate) return controlRows(field, build, onChange, fieldName(field), slots);

  const sub = field.kind === "flag" ? null : h("div", { class: "row-stack", hidden: !build.gates[field.id] }, controlRows(field, build, onChange, null, slots));
  const toggle = switchRow(
    `g-${field.id}`,
    fieldName(field),
    build.gates[field.id],
    (checked) => {
      build.gates[field.id] = checked;
      if (sub) sub.hidden = !checked;
      onChange();
      if (checked) sub?.querySelector("input, select")?.focus();
    },
    { title: field.gate },
  );

  return [toggle.el, sub];
}

let popoverCount = 0;

/** A "Columns" button that opens a glass popover with a checkbox per predicate. */
function columnsPicker(desc, q, onChange) {
  const id = `columns-pop-${++popoverCount}`;
  const button = h("button", { class: "btn btn-small popup-btn", type: "button", popovertarget: id, "aria-haspopup": "true" });

  const label = () => {
    button.replaceChildren(h("span", {}, q.predicates.length ? `${q.predicates.length} selected` : "All columns"), icon("updown", 12));
  };

  const pop = h(
    "div",
    { class: "popover glass", id, popover: "auto", role: "group", "aria-label": "Columns to return" },
    desc.predicate_options.map((opt) => {
      const box = h("input", {
        type: "checkbox",
        checked: q.predicates.includes(opt.key),
        onchange: () => {
          const i = q.predicates.indexOf(opt.key);
          if (i >= 0) q.predicates.splice(i, 1);
          else q.predicates.push(opt.key);
          label();
          onChange();
        },
      });
      return h("label", { class: "pop-item", title: opt.label }, box, h("span", {}, opt.key));
    }),
  );

  pop.addEventListener("beforetoggle", (event) => {
    if (event.newState !== "open") return;
    const rect = button.getBoundingClientRect();
    const width = 260;
    pop.style.left = `${Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8))}px`;
    pop.style.top = `${rect.bottom + 6}px`;
    pop.style.maxHeight = `${Math.max(160, window.innerHeight - rect.bottom - 24)}px`;
  });

  label();
  return [button, pop];
}

function outputGroup(desc, build, onChange) {
  const box = h("div");

  const draw = () => {
    const fmt = formatInfo(desc, build);
    const avail = fmt.options;
    const q = build.query;
    const rows = [];

    const formats = h(
      "div",
      { class: "segmented", role: "radiogroup", "aria-label": "Output format" },
      desc.formats.map((f) =>
        h(
          "button",
          {
            type: "button",
            role: "radio",
            "aria-checked": f.key === q.output_format ? "true" : "false",
            title: f.label,
            onclick: () => {
              q.output_format = f.key;
              draw();
              onChange();
            },
          },
          f.key.toUpperCase(),
        ),
      ),
    );

    rows.push(row("Format", formats, { extra: "row-wide" }));

    if (avail.predicates && desc.predicate_options.length) {
      rows.push(row("Columns", columnsPicker(desc, q, onChange)));
    }

    if (avail.orderby || avail.limit) {
      const orderby = h("input", {
        class: "input",
        id: "q-orderby",
        value: q.orderby,
        placeholder: desc.default_orderby || "e.g. EPOCH desc",
        spellcheck: "false",
        oninput: () => {
          q.orderby = orderby.value;
          onChange();
        },
      });
      const offset = h("input", {
        class: "input num",
        id: "q-offset",
        type: "number",
        min: "0",
        inputmode: "numeric",
        value: q.offset,
        disabled: !String(q.limit).trim(),
        placeholder: "0",
        oninput: () => {
          q.offset = offset.value;
          onChange();
        },
      });
      const limit = h("input", {
        class: "input num",
        id: "q-limit",
        type: "number",
        min: "1",
        inputmode: "numeric",
        value: q.limit,
        placeholder: "None",
        oninput: () => {
          q.limit = limit.value;
          offset.disabled = !limit.value.trim();
          onChange();
        },
      });

      rows.push(row("Order by", orderby, { forId: "q-orderby" }), row("Limit", limit, { forId: "q-limit", extra: "row-narrow" }), row("Offset", offset, { forId: "q-offset", extra: "row-narrow" }));
    }

    for (const [key, label, hint] of OPTION_TOGGLES.filter(([k]) => avail[k])) {
      const toggle = (checked) => {
        q[key] = checked;
        onChange();
      };
      rows.push(switchRow(`q-${key}`, label, q[key], toggle, { title: hint }).el);
    }

    box.replaceChildren(group("Output", rows, fmt.warning ? notice("warn", fmt.warning) : null));
  };

  draw();
  return box;
}

function previewGroup(desc, build, slots) {
  const urlBox = h("pre", { class: "url-box", tabindex: "0", "aria-label": "Query URL" }, h("code", { class: "url" }, "Building…"));
  const messages = h("div", { class: "messages", "aria-live": "polite" });
  const copy = h("button", { class: "icon-btn icon-btn-small", type: "button", "aria-label": "Copy query URL", title: "Copy URL", onclick: () => lastUrl && copyText(lastUrl) }, icon("copy", 14));
  const next = primaryButton("Review", { onclick: () => (location.hash = `#/download/${encodeURIComponent(desc.key)}`) });
  let lastUrl = "";
  let seq = 0;
  let timer;

  // Custom-pair hints come back indexed among the non-empty pairs the payload sent.
  const showHints = (hints) => {
    for (const el of slots.values()) el.hidden = true;
    const customIds = new Set(desc.fields.filter((f) => f.kind === "custom").map((f) => f.id));
    const sent = build.custom.flatMap(([p, v], i) => (p.trim() || v.trim() ? [i] : []));

    for (const hint of hints) {
      const key = customIds.has(hint.field) && hint.index !== undefined ? `${hint.field}:${sent[hint.index]}` : hint.field;
      const el = slots.get(key);
      if (!el) continue;
      el.textContent = hint.message;
      el.hidden = false;
    }
  };

  const update = async () => {
    const mine = ++seq;
    const body = queryPayload(desc, build);

    try {
      const data = await api("/api/preview", { method: "POST", body });
      if (mine !== seq) return;

      lastUrl = data.url;
      urlBox.replaceChildren(urlView(data.url));
      messages.replaceChildren(...data.warnings.map((w) => notice("warn", w)));
      showHints(data.value_hints || []);
      next.disabled = false;
      urlBox.classList.remove("stale");
    } catch (error) {
      if (mine !== seq) return;
      // 400s are "this query isn't complete yet" guidance, not failures.
      messages.replaceChildren(notice(error.status === 400 ? "warn" : "error", error.message));
      showHints([]);
      next.disabled = true;
      urlBox.classList.add("stale");
    }
  };

  const schedule = () => {
    clearTimeout(timer);
    urlBox.classList.add("stale");
    timer = setTimeout(update, 220);
  };

  const el = h(
    "aside",
    { class: "preview", "aria-label": "Query preview" },
    h("div", { class: "group-head" }, h("h2", { class: "group-title" }, "Query"), copy),
    h("div", { class: "group-body group-pad" }, urlBox),
    messages,
  );

  update();
  return { el, schedule, next };
}

async function builderView(key) {
  const desc = await loadDataset(key);
  const build = getBuild(desc);
  const slots = new Map();
  const preview = previewGroup(desc, build, slots);
  const onChange = preview.schedule;

  const filters = desc.fields.length
    ? group("Filters", desc.fields.flatMap((field) => fieldRows(field, build, onChange, slots)))
    : group("Filters", h("div", { class: "row" }, h("span", { class: "row-label muted" }, "No filters for this dataset.")));

  const reset = h(
    "button",
    {
      class: "btn",
      type: "button",
      title: "Reset to defaults",
      onclick: () => {
        state.builds.delete(desc.key);
        render();
      },
    },
    "Reset",
  );

  return {
    title: shortName(desc),
    actions: [reset, preview.next],
    body: h(
      "div",
      { class: "builder" },
      h("div", { class: "builder-side" }, preview.el),
      h("div", { class: "builder-main" }, desc.warning ? notice("warn", desc.warning) : null, filters, outputGroup(desc, build, onChange)),
    ),
  };
}

// ============================================================================
// Shared result pieces
// ============================================================================

function openDialog(dialog) {
  document.body.append(dialog);
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
  dialog.addEventListener("close", () => dialog.remove(), { once: true });
}

function closeDialog(dialog) {
  if (typeof dialog.close === "function") dialog.close();
  else {
    dialog.removeAttribute("open");
    dialog.dispatchEvent(new Event("close"));
  }
}

function dialogShell(title, ...body) {
  const dialog = h("dialog", { class: "sheet glass", "aria-labelledby": "dialog-title" });
  dialog.append(h("h2", { class: "sheet-title", id: "dialog-title" }, title), ...body.flat().filter(Boolean));
  return dialog;
}

function previewBlock(preview) {
  if (!preview) return null;

  if (preview.table && preview.table.columns.length) {
    const { columns, rows, total } = preview.table;
    const note = total > rows.length ? `First ${rows.length} of ${total} rows` : `${total} ${total === 1 ? "row" : "rows"}`;

    return h(
      "div",
      { class: "preview-data" },
      h(
        "div",
        { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "Data preview" },
        h("table", { class: "data" }, h("thead", {}, h("tr", {}, columns.map((c) => h("th", { scope: "col" }, c)))), h("tbody", {}, rows.map((r) => h("tr", {}, r.map((cell) => h("td", {}, cell)))))),
      ),
      h("p", { class: "group-foot" }, note),
    );
  }

  return h("div", { class: "preview-data" }, h("pre", { class: "text-preview", tabindex: "0" }, preview.text));
}

// ============================================================================
// Download
// ============================================================================

async function downloadView(key) {
  const desc = await loadDataset(key);
  const build = getBuild(desc);
  const payload = queryPayload(desc, build);
  const back = { href: `#/build/${encodeURIComponent(key)}`, label: "Back to filters" };
  let prepared;

  try {
    prepared = await api("/api/preview", { method: "POST", body: payload });
  } catch (error) {
    if (error.status !== 400) throw error;
    return { title: "Download", back, body: notice("warn", error.message) };
  }

  const ex = build.export;
  const isJson = prepared.query_options.output_format === "json";

  const dir = h("input", { class: "input input-bare", id: "x-dir", value: ex.download_dir, placeholder: "subfolder", spellcheck: "false", oninput: () => (ex.download_dir = dir.value) });
  const name = h("input", {
    class: "input",
    id: "x-name",
    value: ex.custom_name,
    placeholder: key === "publicfiles_download" ? "Original name" : "Automatic",
    title: "Without an extension; it's added for you.",
    spellcheck: "false",
    oninput: () => (ex.custom_name = name.value),
  });

  const result = h("div", { class: "result", "aria-live": "polite" });
  const go = primaryButton("Download");

  const run = async () => {
    setBusy(go, true);
    result.replaceChildren(
      group(null, h("div", { class: "row waiting" }, h("span", { class: "spinner", "aria-hidden": "true" }), h("span", { class: "row-label" }, "Waiting for Space-Track…"), h("span", { class: "row-value" }, "Large queries can take minutes"))),
    );

    try {
      const data = await api("/api/download", {
        method: "POST",
        body: { ...payload, export: { download_dir: ex.download_dir.trim() || null, custom_name: ex.custom_name.trim() || null, overwrite: ex.overwrite, pretty_json: ex.pretty_json } },
      });
      state.history = null;
      result.replaceChildren(resultPanel(data));
      result.scrollIntoView?.({ behavior: "smooth", block: "start" });
    } catch (error) {
      if (error.status === 401 && !state.session.logged_in) {
        sessionExpired();
        return;
      }

      if (error.status === 401) state.session = await api("/api/session").catch(() => state.session);
      result.replaceChildren(group("Download failed", h("div", { class: "group-pad" }, notice("error", error.message))));
    } finally {
      setBusy(go, false);
    }
  };

  go.addEventListener("click", () => {
    const confirm = primaryButton("Send Request");
    const dialog = dialogShell(
      "Send this request to Space-Track?",
      h("pre", { class: "url-box" }, urlView(prepared.url)),
      h("p", { class: "muted" }, "Counts toward your rate limit (about 30 a minute, 300 an hour)."),
      h("div", { class: "sheet-actions" }, h("button", { class: "btn", type: "button", onclick: () => closeDialog(dialog) }, "Cancel"), confirm),
    );
    confirm.addEventListener("click", () => {
      closeDialog(dialog);
      run();
    });
    openDialog(dialog);
    confirm.focus();
  });

  const filters = Object.entries(prepared.filters);

  return {
    title: "Download",
    back,
    actions: [state.session.logged_in ? go : null],
    body: h(
      "div",
      { class: "stack" },
      state.session.logged_in ? null : notice("warn", "Sign in to download."),
      group(
        "Query",
        [
          h("div", { class: "group-pad" }, h("pre", { class: "url-box" }, urlView(prepared.url))),
          valueRow("Dataset", shortName(desc)),
          valueRow("Format", prepared.query_options.output_format.toUpperCase()),
          valueRow("Filters", filters.length ? filters.map(([k, v]) => `${k} ${v}`).join(", ") : "None"),
          valueRow("Limit", prepared.query_options.limit ?? "None"),
        ],
        prepared.warnings.map((w) => notice("warn", w)),
      ),
      group("Save to", [
        row("Folder", h("div", { class: "prefixed" }, h("span", { class: "prefix" }, "downloads/"), dir), { forId: "x-dir" }),
        row("File name", name, { forId: "x-name" }),
        switchRow("x-overwrite", "Overwrite existing file", ex.overwrite, (checked) => (ex.overwrite = checked), { title: "Otherwise _1, _2 … is appended." }).el,
        isJson ? switchRow("x-pretty", "Pretty-print JSON", ex.pretty_json, (checked) => (ex.pretty_json = checked)).el : null,
      ]),
      result,
    ),
  };
}

function resultPanel(data) {
  const file = data.file;

  return h(
    "div",
    { class: "stack" },
    group(
      "Saved",
      [
        valueRow("Records", file.record_count ?? "–"),
        valueRow("Size", formatBytes(file.size_bytes)),
        valueRow("Time", `${data.elapsed_seconds.toFixed(2)} s`),
        valueRow("Response", h("span", { class: "ok" }, `HTTP ${data.status_code}`)),
        valueRow("File", h("code", {}, file.path)),
        valueRow("Metadata", data.metadata_file ? h("code", {}, data.metadata_file) : "Not saved"),
      ],
      data.metadata_error ? notice("warn", data.metadata_error) : null,
    ),
    previewBlock(data.preview),
    h("div", { class: "button-row" }, h("a", { class: "btn", href: "#/datasets" }, "New Query"), h("a", { class: "btn", href: "#/history" }, "Open History")),
  );
}

// ============================================================================
// History
// ============================================================================

function historyDialog(entry) {
  const previewBox = h("div", { class: "preview-slot" }, entry.output_exists ? h("div", { class: "waiting" }, h("span", { class: "spinner", "aria-hidden": "true" }), h("span", { class: "muted" }, "Reading the saved file…")) : notice("warn", "The data file is no longer on disk."));
  const filters = Object.entries(entry.filters || {});
  let dialog;

  dialog = dialogShell(
    SHORT_NAMES[entry.dataset_key] || entry.dataset_label || entry.dataset_key,
    h(
      "div",
      { class: "url-row" },
      h("pre", { class: "url-box" }, urlView(entry.query_url || "")),
      h("button", { class: "icon-btn icon-btn-small", type: "button", "aria-label": "Copy query URL", title: "Copy URL", onclick: () => copyText(entry.query_url || "") }, icon("copy", 14)),
    ),
    group(null, [
      valueRow("Saved", formatTime(entry.created_utc)),
      valueRow("Filters", filters.length ? filters.map(([k, v]) => `${k} ${v}`).join(", ") : "None"),
      entry.favorites ? valueRow("Favorites", entry.favorites) : null,
      valueRow("Records", entry.estimated_record_count ?? "–"),
      valueRow("Size", formatBytes(entry.output_size_bytes)),
      valueRow("Response", entry.response_status_code ? `HTTP ${entry.response_status_code} in ${Number(entry.response_elapsed_seconds || 0).toFixed(2)} s` : "–"),
      valueRow("File", h("code", {}, entry.output_file)),
      valueRow("Metadata", h("code", {}, entry.meta_file)),
    ]),
    (entry.notes || []).map((note) => h("p", { class: "subtle" }, note)),
    previewBox,
    h("div", { class: "sheet-actions" }, h("button", { class: "btn btn-primary", type: "button", onclick: () => closeDialog(dialog) }, "Done")),
  );

  dialog.classList.add("sheet-wide");
  openDialog(dialog);

  if (entry.output_exists) {
    api(`/api/history/preview?meta_file=${encodeURIComponent(entry.meta_file)}`)
      .then((preview) => previewBox.replaceChildren(previewBlock(preview)))
      .catch((error) => previewBox.replaceChildren(notice("warn", error.message)));
  }
}

async function historyView() {
  if (!state.history) state.history = await api("/api/history");
  const { entries, errors } = state.history;

  const refresh = h(
    "button",
    {
      class: "btn",
      type: "button",
      onclick: () => {
        state.history = null;
        render();
      },
    },
    "Refresh",
  );

  const listRow = (entry) =>
    h(
      "button",
      { class: "list-row", type: "button", onclick: () => historyDialog(entry) },
      h("span", { class: "row-text" }, h("span", { class: "row-title" }, SHORT_NAMES[entry.dataset_key] || entry.dataset_label || entry.dataset_key), h("span", { class: "row-detail" }, entry.output_filename || entry.output_file)),
      entry.output_exists ? null : h("span", { class: "tag tag-warn" }, "File missing"),
      h("span", { class: "row-meta num" }, [(entry.output_format || "").toUpperCase(), formatBytes(entry.output_size_bytes), formatTime(entry.created_utc)].filter(Boolean).join(" · ")),
      h("span", { class: "chevron" }, icon("chevronRight", 14)),
    );

  const body = entries.length
    ? group(null, entries.map(listRow))
    : h("div", { class: "empty" }, h("p", { class: "muted" }, "No downloads yet."), state.session.logged_in ? h("a", { class: "btn", href: "#/datasets" }, "Choose a Dataset") : null);

  return {
    title: "History",
    actions: [refresh],
    body: [
      errors.length
        ? h(
            "details",
            { class: "notice notice-warn errors" },
            h("summary", {}, `${errors.length} metadata ${errors.length === 1 ? "file" : "files"} couldn't be read`),
            h("ul", {}, errors.map((e) => h("li", {}, e))),
          )
        : null,
      body,
    ],
  };
}

// ============================================================================
// Router
// ============================================================================

const routes = {
  login: { view: loginView, public: true },
  datasets: { view: datasetsView },
  build: { view: builderView },
  download: { view: downloadView },
  history: { view: historyView, public: true },
};

function parseRoute() {
  const [name = "", ...rest] = location.hash.replace(/^#\/?/, "").split("/");
  return { name, params: rest.map(decodeURIComponent) };
}

let renderSeq = 0;

async function render() {
  const { name, params } = parseRoute();
  const fallback = state.session.logged_in ? "datasets" : "login";
  const route = routes[name];

  if (!route || (!route.public && !state.session.logged_in)) {
    if (name !== fallback && routes[fallback]) {
      location.replace(`#/${fallback}`);
      return;
    }
  }

  if (name === "login" && state.session.logged_in && routes.datasets) {
    location.replace("#/datasets");
    return;
  }

  const mine = ++renderSeq;
  const activeName = routes[name] ? name : fallback;
  const active = routes[activeName] || routes.login;
  setSidebarOpen(false);
  for (const sheet of document.querySelectorAll("dialog.sheet")) closeDialog(sheet);
  await renderChrome();

  let page;

  try {
    page = await active.view(...params);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      sessionExpired();
      return;
    }

    page = { title: "Something went wrong", body: notice("error", error.message) };
  }

  // A newer navigation started while this view was loading.
  if (mine !== renderSeq) return;

  showPage(page);
  moveSidebarPill(["build", "download"].includes(activeName) ? params[0] : activeName);
  window.scrollTo({ top: 0 });
  updateToolbar();
}

async function start() {
  applyTheme(storedTheme());

  try {
    state.session = await api("/api/session");
  } catch (error) {
    toast(error.message);
  }

  window.addEventListener("hashchange", render);
  render();
}

start();
