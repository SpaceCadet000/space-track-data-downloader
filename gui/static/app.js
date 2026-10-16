/*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROJECT NAME: Space-Track Data Downloader
FILE:         app.js
PATH:         space-track-data-downloader/gui/static/app.js
AUTHOR:       Sooraj Suresh
DATE:         October 2026
VERSION:      1.0.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION:  Single-page client for the local web GUI: API helper, hash router,
              theme toggle, and the screens. Only the login form and the
              confirmed download dialog cause requests to Space-Track; every
              other call stays on this machine.
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

/** Thin line icons drawn inline (1.5px strokes). */
const ICONS = {
  arrow: "M5 12h14M13 6l6 6-6 6",
  lock: "M7 11V8a5 5 0 0 1 10 0v3M6 11h12v9H6z",
  chip: "M8 8h8v8H8zM12 3v3M12 18v3M3 12h3M18 12h3",
  pulse: "M3 12h4l2-6 4 12 2-6h6",
  copy: "M9 9h10v10H9zM5 15V5h10",
  close: "M6 6l12 12M18 6 6 18",
  plus: "M12 5v14M5 12h14",
  back: "M19 12H5M11 18l-6-6 6-6",
  refresh: "M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6",
  download: "M12 4v11M7 10l5 5 5-5M5 20h14",
  sun: "M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
  moon: "M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9Z",
};

function icon(name, size = 18) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", ICONS[name]);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.5");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

function primaryButton(label, attrs = {}, iconName = "arrow") {
  return h("button", { class: "btn btn-primary", type: "button", ...attrs }, h("span", {}, label), h("span", { class: "btn-orb" }, icon(iconName, 16)));
}

function panel(...children) {
  return h("section", { class: "panel" }, h("div", { class: "panel-core" }, ...children));
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
  return matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  const button = document.getElementById("theme-toggle");
  const next = currentTheme() === "dark" ? "light" : "dark";
  button.replaceChildren(icon(next === "light" ? "sun" : "moon"));
  button.setAttribute("aria-label", `Switch to ${next} theme`);
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
// Session chrome
// ============================================================================

function renderChrome(route) {
  const topbar = document.getElementById("topbar");
  const loggedIn = state.session.logged_in;
  topbar.hidden = false;

  document.querySelector('[data-nav="datasets"]').hidden = !loggedIn;
  document.getElementById("logout").hidden = !loggedIn;
  const label = document.getElementById("session-label");
  label.hidden = !loggedIn;
  label.textContent = loggedIn ? state.session.identity : "";

  for (const link of document.querySelectorAll("[data-nav]")) {
    if (link.dataset.nav === route) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
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
  const username = h("input", { class: "input", id: "username", name: "username", autocomplete: "username", required: true, spellcheck: "false" });
  const password = h("input", { class: "input", id: "password", name: "password", type: "password", autocomplete: "current-password", required: true });
  const error = h("div", { "aria-live": "assertive" });
  const submit = primaryButton("Sign in to Space-Track", { type: "submit" });

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
    h("h2", {}, "Sign in"),
    h("div", { class: "field" }, h("label", { for: "username" }, "Username or email"), username),
    h("div", { class: "field" }, h("label", { for: "password" }, "Password"), password),
    error,
    submit,
    h("p", { class: "subtle" }, "No account yet? Register for free at ", h("a", { href: "https://www.space-track.org/auth/createAccount", target: "_blank", rel: "noopener noreferrer" }, "space-track.org"), "."),
  );

  const fact = (iconName, title, text) => h("li", {}, icon(iconName, 20), h("span", {}, h("strong", {}, title), " ", text));

  const view = h(
    "div",
    { class: "login" },
    h(
      "div",
      { class: "login-copy reveal" },
      h("h1", {}, "Orbital data, one careful query at a time"),
      h("p", {}, "Build Space-Track queries for element sets, the satellite catalogue, decay and conjunction data, and download them with a metadata record beside each file."),
      h(
        "ul",
        { class: "login-facts" },
        fact("lock", "Your password is never stored.", "It goes once to space-track.org; only the session cookie stays, in this server's memory, until you log out or stop it."),
        fact("pulse", "Nothing is sent until you click download.", "Query previews are built on this machine, so you stay well inside Space-Track's rate limits."),
        fact("chip", "Local only.", "The app listens on 127.0.0.1 and saves everything under downloads/."),
      ),
    ),
    h("div", { class: "reveal" }, panel(form)),
  );

  queueMicrotask(() => username.focus());
  return view;
}

// ============================================================================
// Router
// ============================================================================

const routes = {
  login: { view: loginView, public: true },
  datasets: { view: () => panel(h("h2", {}, "Signed in"), h("p", { class: "muted" }, "The dataset picker arrives in the next stage.")) },
};

function parseRoute() {
  const [name = "", ...rest] = location.hash.replace(/^#\/?/, "").split("/");
  return { name, params: rest.map(decodeURIComponent) };
}

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

  const active = routes[name] || routes[fallback] || routes.login;
  renderChrome(name);

  try {
    const view = await active.view(...params);
    app.replaceChildren(view);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      sessionExpired();
      return;
    }

    app.replaceChildren(panel(notice("error", error.message)));
  }

  window.scrollTo({ top: 0 });
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
