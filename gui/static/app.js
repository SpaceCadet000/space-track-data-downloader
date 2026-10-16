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

function controllerLabel(controller) {
  return controller === "publicfiles" ? "Public files" : "Basic space data";
}

async function datasetsView() {
  const groups = await loadCatalog();

  const row = (dataset) =>
    h(
      "a",
      { class: "dataset-row", href: `#/build/${encodeURIComponent(dataset.key)}` },
      h(
        "span",
        { class: "dataset-text" },
        h("h3", {}, dataset.label),
        h("span", { class: "muted" }, dataset.description),
        h(
          "span",
          { class: "dataset-meta subtle" },
          h("span", {}, `class/${dataset.api_class}`),
          h("span", {}, controllerLabel(dataset.controller)),
          h("span", {}, `${dataset.default_format.toUpperCase()} by default`),
          dataset.warning ? h("span", { class: "meta-warn" }, "Large: narrow it down") : null,
        ),
      ),
      h("span", { class: "row-orb" }, icon("arrow", 16)),
    );

  return h(
    "div",
    { class: "datasets" },
    h(
      "header",
      { class: "view-head reveal" },
      h("h1", {}, "What do you want to download?"),
      h("p", {}, "Pick a dataset to build its query. The URL is previewed as you go; Space-Track is only contacted when you confirm the download."),
    ),
    groups.map((group) =>
      h(
        "section",
        { class: "group reveal", "aria-labelledby": `group-${group.key}` },
        h("div", { class: "group-head" }, h("h2", { id: `group-${group.key}` }, group.label), h("p", { class: "muted" }, group.description)),
        panel(h("div", { class: "dataset-list" }, group.datasets.map(row))),
      ),
    ),
  );
}

// ============================================================================
// Filter builder
// ============================================================================

const OPTION_TOGGLES = [
  ["show_empty", "Say so explicitly when nothing matches", "Adds /emptyresult/show."],
  ["distinct", "Distinct rows only", "Adds /distinct/true."],
  ["metadata", "Include Space-Track metadata", "Adds /metadata/true; ignored for CSV, TLE, 3LE and KVN."],
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

/** Turn a field's help text into clickable examples. */
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

function fieldControl(field, build, onChange) {
  const id = `f-${field.id}`;

  if (["preset", "choice", "favorites", "country"].includes(field.kind)) {
    const select = h(
      "select",
      {
        class: "select",
        id,
        onchange: () => {
          build.values[field.id] = select.value;
          if (field.kind === "country") customBox.hidden = select.value !== "custom";
          onChange();
        },
      },
      field.options.map((opt) => h("option", { value: opt.key, selected: opt.key === build.values[field.id] }, opt.label)),
    );

    let customBox = null;

    if (field.kind === "country") {
      const customInput = h("input", {
        class: "input",
        id: `${id}-custom`,
        value: build.countryCustom,
        placeholder: "Space-Track owner code, e.g. ISRA",
        autocapitalize: "characters",
        oninput: () => {
          build.countryCustom = customInput.value;
          onChange();
        },
      });
      customBox = h("div", { class: "field", hidden: build.values[field.id] !== "custom" }, h("label", { for: `${id}-custom` }, "Custom country or owner code"), customInput);
    }

    return h("div", { class: "control" }, h("label", { class: "visually-hidden", for: id }, field.label), select, customBox);
  }

  if (field.kind === "text" || field.kind === "date") {
    const examples = parseExamples(field.help);
    const input = h("input", {
      class: "input",
      id,
      value: build.values[field.id] ?? "",
      placeholder: examples[0]?.value || "",
      spellcheck: "false",
      autocapitalize: field.uppercase ? "characters" : "off",
      oninput: () => {
        build.values[field.id] = input.value;
        onChange();
      },
    });

    const chips = examples.length
      ? h(
          "div",
          { class: "examples", role: "group", "aria-label": `Examples for ${field.predicate}` },
          examples.map((ex) =>
            h(
              "button",
              {
                class: "chip",
                type: "button",
                title: ex.title || `Use ${ex.value}`,
                onclick: () => {
                  input.value = ex.value;
                  build.values[field.id] = ex.value;
                  onChange();
                },
              },
              ex.title ? `${ex.value} · ${ex.title}` : ex.value,
            ),
          ),
        )
      : null;

    const prose = field.help && !examples.length ? h("p", { class: "subtle" }, field.help) : null;

    return h("div", { class: "control" }, h("label", { class: "visually-hidden", for: id }, field.label), input, chips, prose);
  }

  if (field.kind === "custom") {
    const list = h("div", { class: "custom-list" });

    const drawRows = () => {
      list.replaceChildren(
        ...build.custom.map((pair, index) => {
          const predicate = h("input", {
            class: "input",
            value: pair[0],
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
              class: "icon-btn",
              type: "button",
              "aria-label": `Remove custom filter ${index + 1}`,
              onclick: () => {
                build.custom.splice(index, 1);
                if (!build.custom.length) build.custom.push(["", ""]);
                drawRows();
                onChange();
              },
            },
            icon("close", 16),
          );
          return h("div", { class: "custom-row" }, predicate, value, remove);
        }),
      );
    };

    drawRows();

    return h(
      "div",
      { class: "control" },
      list,
      h(
        "button",
        {
          class: "btn btn-quiet btn-small add-row",
          type: "button",
          onclick: () => {
            build.custom.push(["", ""]);
            drawRows();
            list.lastElementChild?.querySelector("input")?.focus();
          },
        },
        icon("plus", 16),
        "Add another filter",
      ),
      h("p", { class: "subtle" }, "Any predicate the class supports: operators , (or), -- (range), ~~ (wildcard), < > and null-val all work."),
    );
  }

  return null;
}

function fieldRow(field, build, onChange) {
  const id = `f-${field.id}`;

  if (!field.gate) {
    return h("div", { class: "filter-row" }, h("label", { class: "filter-label", for: id }, field.label), fieldControl(field, build, onChange));
  }

  const toggleId = `g-${field.id}`;
  const body = field.kind === "flag" ? null : h("div", { class: "filter-body", hidden: !build.gates[field.id] }, fieldControl(field, build, onChange));
  const toggle = h("input", {
    class: "switch",
    type: "checkbox",
    role: "switch",
    id: toggleId,
    checked: build.gates[field.id],
    onchange: () => {
      build.gates[field.id] = toggle.checked;
      if (body) body.hidden = !toggle.checked;
      row.classList.toggle("on", toggle.checked);
      onChange();
      if (toggle.checked) body?.querySelector("input, select")?.focus();
    },
  });

  const row = h(
    "div",
    { class: `filter-row gated${build.gates[field.id] ? " on" : ""}` },
    h("label", { class: "check-row", for: toggleId }, h("span", { class: "filter-label" }, field.gate.replace(/\?$/, "")), toggle),
    body,
  );

  return row;
}

function optionsSection(desc, build, onChange) {
  const box = h("div", { class: "options" });

  const draw = () => {
    const fmt = formatInfo(desc, build);
    const avail = fmt.options;
    const q = build.query;

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

    const parts = [h("div", { class: "filter-row" }, h("span", { class: "filter-label" }, "Format"), formats, h("p", { class: "subtle" }, fmt.label))];

    if (fmt.warning) parts.push(notice("warn", fmt.warning));

    if (avail.predicates && desc.predicate_options.length) {
      const chips = desc.predicate_options.map((opt) => {
        const on = q.predicates.includes(opt.key);
        return h(
          "button",
          {
            class: "chip toggle",
            type: "button",
            "aria-pressed": on ? "true" : "false",
            title: opt.label,
            onclick: (event) => {
              const i = q.predicates.indexOf(opt.key);
              if (i >= 0) q.predicates.splice(i, 1);
              else q.predicates.push(opt.key);
              event.currentTarget.setAttribute("aria-pressed", i >= 0 ? "false" : "true");
              onChange();
            },
          },
          opt.key,
        );
      });

      parts.push(
        h(
          "div",
          { class: "filter-row" },
          h("span", { class: "filter-label" }, "Columns to return"),
          h("div", { class: "examples", role: "group", "aria-label": "Columns to return" }, chips),
          h("p", { class: "subtle" }, "Leave all off to get every column."),
        ),
      );
    }

    if (avail.orderby || avail.limit) {
      const orderby = h("input", {
        class: "input",
        id: "q-orderby",
        value: q.orderby,
        placeholder: desc.default_orderby ? `Default: ${desc.default_orderby}` : "e.g. EPOCH desc",
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
        placeholder: "No limit",
        oninput: () => {
          q.limit = limit.value;
          offset.disabled = !limit.value.trim();
          onChange();
        },
      });

      parts.push(
        h(
          "div",
          { class: "option-grid" },
          h("div", { class: "field wide" }, h("label", { for: "q-orderby" }, "Order by"), orderby),
          h("div", { class: "field" }, h("label", { for: "q-limit" }, "Limit"), limit),
          h("div", { class: "field" }, h("label", { for: "q-offset" }, "Offset"), offset),
        ),
      );
    }

    const toggles = OPTION_TOGGLES.filter(([key]) => avail[key]).map(([key, label, hint]) => {
      const input = h("input", {
        class: "switch",
        type: "checkbox",
        role: "switch",
        id: `q-${key}`,
        checked: q[key],
        onchange: () => {
          q[key] = input.checked;
          onChange();
        },
      });
      return h("label", { class: "check-row toggle-row", for: `q-${key}` }, h("span", {}, h("span", { class: "filter-label" }, label), h("span", { class: "subtle block" }, hint)), input);
    });

    if (toggles.length) parts.push(h("div", { class: "toggle-list" }, toggles));

    box.replaceChildren(...parts);
  };

  draw();
  return box;
}

function previewPanel(desc, build) {
  const urlBox = h("pre", { class: "url-box", tabindex: "0", "aria-label": "Query URL" }, h("code", { class: "url" }, "Building…"));
  const facts = h("dl", { class: "facts" });
  const messages = h("div", { class: "messages", "aria-live": "polite" });
  const copy = h("button", { class: "icon-btn", type: "button", "aria-label": "Copy query URL", onclick: () => lastUrl && copyText(lastUrl) }, icon("copy", 16));
  const next = primaryButton("Review download", { onclick: () => (location.hash = `#/download/${encodeURIComponent(desc.key)}`) });
  let lastUrl = "";
  let seq = 0;
  let timer;

  const fact = (term, value) => [h("dt", {}, term), h("dd", { class: "num" }, value)];

  const update = async () => {
    const mine = ++seq;
    const body = queryPayload(desc, build);

    try {
      const data = await api("/api/preview", { method: "POST", body });
      if (mine !== seq) return;

      lastUrl = data.url;
      urlBox.replaceChildren(urlView(data.url));
      const filterCount = Object.keys(data.filters).length;
      facts.replaceChildren(
        ...fact("Format", data.query_options.output_format.toUpperCase()),
        ...fact("Filters", filterCount ? String(filterCount) : "None"),
        ...fact("Limit", data.query_options.limit ?? "None"),
        ...fact("Order", data.summary.orderby || "Default"),
        ...(data.favorites ? fact("Favorites", data.favorites) : []),
      );
      messages.replaceChildren(...data.warnings.map((w) => notice("warn", w)));
      next.disabled = false;
      urlBox.classList.remove("stale");
    } catch (error) {
      if (mine !== seq) return;
      // 400s are "this query isn't complete yet" guidance, not failures.
      messages.replaceChildren(notice(error.status === 400 ? "warn" : "error", error.message));
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
    panel(
      h("div", { class: "preview-head" }, h("h2", {}, "Query preview"), copy),
      urlBox,
      facts,
      messages,
      next,
      h("p", { class: "subtle" }, "Built on this machine. Nothing has been sent to Space-Track."),
    ),
  );

  update();
  return { el, schedule };
}

async function builderView(key) {
  const desc = await loadDataset(key);
  const build = getBuild(desc);
  const preview = previewPanel(desc, build);
  const onChange = preview.schedule;

  const filters = desc.fields.length
    ? panel(h("h2", {}, "Filters"), h("div", { class: "filter-list" }, desc.fields.map((field) => fieldRow(field, build, onChange))))
    : panel(h("h2", {}, "Filters"), h("p", { class: "muted" }, "This dataset takes no filters."));

  const reset = h(
    "button",
    {
      class: "btn btn-quiet btn-small",
      type: "button",
      onclick: () => {
        state.builds.delete(desc.key);
        render();
      },
    },
    icon("refresh", 16),
    "Reset to defaults",
  );

  return h(
    "div",
    { class: "builder" },
    h(
      "header",
      { class: "view-head reveal" },
      h("a", { class: "back", href: "#/datasets" }, icon("back", 16), "All datasets"),
      h("h1", {}, desc.label),
      h("p", {}, desc.description),
      desc.warning ? notice("warn", desc.warning) : null,
    ),
    h(
      "div",
      { class: "builder-grid" },
      h("div", { class: "builder-main reveal" }, filters, panel(h("h2", {}, "Output"), optionsSection(desc, build, onChange)), h("div", { class: "builder-foot" }, reset)),
      h("div", { class: "reveal" }, preview.el),
    ),
  );
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
  const dialog = h("dialog", { class: "dialog", "aria-labelledby": "dialog-title" });
  const close = h("button", { class: "icon-btn", type: "button", "aria-label": "Close", onclick: () => closeDialog(dialog) }, icon("close", 18));
  dialog.append(h("div", { class: "dialog-head" }, h("h2", { id: "dialog-title" }, title), close), ...body);
  return dialog;
}

function previewBlock(preview) {
  if (!preview) return null;

  if (preview.table && preview.table.columns.length) {
    const { columns, rows, total } = preview.table;
    const note = total > rows.length ? `First ${rows.length} of ${total} rows.` : `${total} ${total === 1 ? "row" : "rows"}.`;

    return h(
      "div",
      { class: "preview-data" },
      h(
        "div",
        { class: "table-wrap", tabindex: "0", role: "region", "aria-label": "Data preview" },
        h("table", { class: "data" }, h("thead", {}, h("tr", {}, columns.map((c) => h("th", { scope: "col" }, c)))), h("tbody", {}, rows.map((r) => h("tr", {}, r.map((cell) => h("td", {}, cell)))))),
      ),
      h("p", { class: "subtle" }, note),
    );
  }

  return h("div", { class: "preview-data" }, h("pre", { class: "text-preview", tabindex: "0" }, preview.text));
}

function stat(label, value) {
  return h("div", { class: "stat" }, h("span", { class: "stat-value num" }, value), h("span", { class: "stat-label" }, label));
}

// ============================================================================
// Download
// ============================================================================

async function downloadView(key) {
  const desc = await loadDataset(key);
  const build = getBuild(desc);
  const payload = queryPayload(desc, build);
  let prepared;

  try {
    prepared = await api("/api/preview", { method: "POST", body: payload });
  } catch (error) {
    if (error.status !== 400) throw error;

    return h(
      "div",
      { class: "download" },
      h("header", { class: "view-head" }, h("a", { class: "back", href: `#/build/${encodeURIComponent(key)}` }, icon("back", 16), "Back to filters"), h("h1", {}, "This query isn't ready yet")),
      panel(notice("warn", error.message)),
    );
  }

  const ex = build.export;
  const isJson = prepared.query_options.output_format === "json";

  const dir = h("input", { class: "input", id: "x-dir", value: ex.download_dir, placeholder: "optional/subfolder", spellcheck: "false", oninput: () => (ex.download_dir = dir.value) });
  const name = h("input", {
    class: "input",
    id: "x-name",
    value: ex.custom_name,
    placeholder: key === "publicfiles_download" ? "Keep the original file name" : `Automatic: spacetrack_${key}_<UTC time>`,
    spellcheck: "false",
    oninput: () => (ex.custom_name = name.value),
  });
  const switchRow = (id, label, hint, prop) => {
    const input = h("input", { class: "switch", type: "checkbox", role: "switch", id, checked: ex[prop], onchange: () => (ex[prop] = input.checked) });
    return h("label", { class: "check-row toggle-row", for: id }, h("span", {}, h("span", { class: "filter-label" }, label), h("span", { class: "subtle block" }, hint)), input);
  };

  const result = h("div", { class: "result", "aria-live": "polite" });
  const go = primaryButton("Download from Space-Track", {}, "download");

  const run = async () => {
    setBusy(go, true);
    result.replaceChildren(
      panel(h("div", { class: "waiting" }, h("span", { class: "spinner", "aria-hidden": "true" }), h("div", {}, h("h2", {}, "Waiting for Space-Track"), h("p", { class: "muted" }, "Large queries can take a few minutes. Keep this tab open.")))),
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
      result.replaceChildren(panel(h("h2", {}, "The download didn't complete"), notice("error", error.message)));
    } finally {
      setBusy(go, false);
    }
  };

  go.addEventListener("click", () => {
    const confirm = primaryButton("Send request", {}, "download");
    const dialog = dialogShell(
      "Send this request to Space-Track?",
      h("pre", { class: "url-box" }, urlView(prepared.url)),
      h("p", { class: "muted" }, "This is one request against your account's limits (about 30 a minute and 300 an hour). Prefer one well-filtered query to many small ones."),
      h("div", { class: "dialog-actions" }, h("button", { class: "btn", type: "button", onclick: () => closeDialog(dialog) }, "Cancel"), confirm),
    );
    confirm.addEventListener("click", () => {
      closeDialog(dialog);
      run();
    });
    openDialog(dialog);
    confirm.focus();
  });

  return h(
    "div",
    { class: "download" },
    h(
      "header",
      { class: "view-head reveal" },
      h("a", { class: "back", href: `#/build/${encodeURIComponent(key)}` }, icon("back", 16), "Back to filters"),
      h("h1", {}, `Download ${desc.label}`),
      h("p", {}, "Check the query, choose where to save it, then send it. A metadata file is written beside the data."),
    ),
    h(
      "div",
      { class: "download-grid" },
      h(
        "div",
        { class: "reveal" },
        panel(
          h("h2", {}, "Query"),
          h("pre", { class: "url-box" }, urlView(prepared.url)),
          h(
            "dl",
            { class: "facts" },
            h("dt", {}, "Dataset"),
            h("dd", {}, `${desc.label} (class/${desc.api_class})`),
            h("dt", {}, "Format"),
            h("dd", {}, prepared.query_options.output_format.toUpperCase()),
            h("dt", {}, "Filters"),
            h("dd", {}, Object.keys(prepared.filters).length ? Object.entries(prepared.filters).map(([k, v]) => `${k} ${v}`).join(", ") : "None"),
            h("dt", {}, "Limit"),
            h("dd", { class: "num" }, prepared.query_options.limit ?? "None"),
          ),
          ...prepared.warnings.map((w) => notice("warn", w)),
        ),
      ),
      h(
        "div",
        { class: "reveal" },
        panel(
          h("h2", {}, "Save to"),
          h("div", { class: "field" }, h("label", { for: "x-dir" }, "Folder"), h("div", { class: "prefixed" }, h("span", { class: "prefix" }, "downloads/"), dir)),
          h("div", { class: "field" }, h("label", { for: "x-name" }, "File name"), name, h("p", { class: "subtle" }, "Without an extension; it's added for you.")),
          h(
            "div",
            { class: "toggle-list" },
            switchRow("x-overwrite", "Overwrite a file with the same name", "Otherwise _1, _2 … is appended.", "overwrite"),
            isJson ? switchRow("x-pretty", "Pretty-print JSON", "Indented for reading; turn off for smaller files.", "pretty_json") : null,
          ),
          state.session.logged_in ? go : notice("warn", "Sign in to download."),
        ),
      ),
    ),
    result,
  );
}

function resultPanel(data) {
  const file = data.file;

  return panel(
    h("div", { class: "result-head" }, h("h2", {}, "Saved"), h("span", { class: "ok" }, `HTTP ${data.status_code}`)),
    h(
      "div",
      { class: "stats" },
      stat("records", file.record_count ?? "–"),
      stat("on disk", formatBytes(file.size_bytes)),
      stat("seconds", data.elapsed_seconds.toFixed(2)),
    ),
    h("dl", { class: "facts" }, h("dt", {}, "File"), h("dd", {}, h("code", {}, file.path)), h("dt", {}, "Metadata"), h("dd", {}, data.metadata_file ? h("code", {}, data.metadata_file) : "Not saved")),
    data.metadata_error ? notice("warn", data.metadata_error) : null,
    previewBlock(data.preview),
    h("div", { class: "result-actions" }, h("a", { class: "btn", href: "#/datasets" }, "Build another query"), h("a", { class: "btn btn-quiet", href: "#/history" }, "Open history")),
  );
}

// ============================================================================
// History
// ============================================================================

function historyDialog(entry) {
  const previewBox = h("div", { class: "preview-slot" }, entry.output_exists ? h("div", { class: "waiting" }, h("span", { class: "spinner", "aria-hidden": "true" }), h("span", { class: "muted" }, "Reading the saved file…")) : notice("warn", "The data file is no longer on disk."));
  const filters = Object.entries(entry.filters || {});

  const dialog = dialogShell(
    entry.dataset_label || entry.dataset_key,
    h(
      "div",
      { class: "url-row" },
      h("pre", { class: "url-box" }, urlView(entry.query_url || "")),
      h("button", { class: "icon-btn", type: "button", "aria-label": "Copy query URL", onclick: () => copyText(entry.query_url || "") }, icon("copy", 16)),
    ),
    h(
      "dl",
      { class: "facts" },
      h("dt", {}, "Saved"),
      h("dd", {}, formatTime(entry.created_utc)),
      h("dt", {}, "Filters"),
      h("dd", {}, filters.length ? filters.map(([k, v]) => `${k} ${v}`).join(", ") : "None"),
      entry.favorites ? [h("dt", {}, "Favorites"), h("dd", {}, entry.favorites)] : null,
      h("dt", {}, "Records"),
      h("dd", { class: "num" }, entry.estimated_record_count ?? "–"),
      h("dt", {}, "Size"),
      h("dd", { class: "num" }, formatBytes(entry.output_size_bytes)),
      h("dt", {}, "Response"),
      h("dd", { class: "num" }, entry.response_status_code ? `HTTP ${entry.response_status_code} in ${Number(entry.response_elapsed_seconds || 0).toFixed(2)} s` : "–"),
      h("dt", {}, "File"),
      h("dd", {}, h("code", {}, entry.output_file)),
      h("dt", {}, "Metadata"),
      h("dd", {}, h("code", {}, entry.meta_file)),
    ),
    ...(entry.notes || []).map((note) => h("p", { class: "subtle" }, note)),
    previewBox,
  );

  dialog.classList.add("dialog-wide");
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
      class: "btn btn-small",
      type: "button",
      onclick: () => {
        state.history = null;
        render();
      },
    },
    icon("refresh", 16),
    "Refresh",
  );

  const row = (entry) =>
    h(
      "button",
      { class: "history-row", type: "button", onclick: () => historyDialog(entry) },
      h("span", { class: "history-main" }, h("span", { class: "history-title" }, entry.dataset_label || entry.dataset_key), h("span", { class: "subtle history-file" }, entry.output_filename || entry.output_file)),
      h(
        "span",
        { class: "history-meta num" },
        h("span", { class: "format" }, (entry.output_format || "").toUpperCase()),
        h("span", {}, entry.estimated_record_count === null || entry.estimated_record_count === undefined ? "–" : `${entry.estimated_record_count} records`),
        h("span", {}, formatBytes(entry.output_size_bytes)),
        entry.output_exists ? null : h("span", { class: "meta-warn" }, "File missing"),
      ),
      h("span", { class: "history-time subtle" }, formatTime(entry.created_utc)),
    );

  const body = entries.length
    ? panel(h("div", { class: "history-list" }, entries.map(row)))
    : panel(
        h("div", { class: "empty" }, h("h2", {}, "No downloads yet"), h("p", { class: "muted" }, "Each download writes a _meta.json file beside its data. They'll be listed here."), state.session.logged_in ? h("a", { class: "btn", href: "#/datasets" }, "Choose a dataset") : null),
      );

  return h(
    "div",
    { class: "history" },
    h(
      "header",
      { class: "view-head history-head reveal" },
      h("div", {}, h("h1", {}, "Download history"), h("p", {}, `Read from the metadata files under downloads/. ${entries.length} ${entries.length === 1 ? "download" : "downloads"}; nothing here contacts Space-Track.`)),
      refresh,
    ),
    errors.length
      ? h(
          "details",
          { class: "notice notice-warn errors reveal" },
          h("summary", {}, `${errors.length} metadata ${errors.length === 1 ? "file" : "files"} couldn't be read`),
          h("ul", {}, errors.map((e) => h("li", {}, e))),
        )
      : null,
    h("div", { class: "reveal" }, body),
  );
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
