/* SPDX-License-Identifier: MIT
 * Copyright (c) 2026 Reinhard-M. Unofficial community integration, not affiliated with Home Assistant. */
/*
 * Rollladen Steuerung - Lovelace card (manual control and monitoring of all shutters)
 * Loaded automatically by the integration (no manual resource entry needed).
 *
 * type: custom:rollladen-steuerung-card
 * title: Rolll\u00e4den
 * devices: [<device IDs of the Rollladen Steuerung instances>]   # order = row order
 * show_state: false                                           # extra column "state" / delay
 *
 * Columns: name (link to the device) | status | height | up | stop | down | back | MyPosition/slats
 */
const CARD_TYPE = "rollladen-steuerung-card";
const EDITOR_TYPE = "rollladen-steuerung-card-editor";
const PLATFORM = "rollladen_steuerung";
// Documentation shown by the "?" icon (German README for German UI, English README otherwise)
const DOCS = {
  de: "https://github.com/Reinhard-M/ha-rollladen-steuerung#readme",
  en: "https://github.com/Reinhard-M/ha-rollladen-steuerung/blob/main/README.en.md",
};

const TEXTS = {
  de: {
    height: "H\u00f6he",
    slats: "Lamellen",
    up: "Hoch",
    stop: "Stopp",
    down: "Runter",
    mypos: "MyPosition",
    back: "Zur\u00fcck",
    empty: "Keine Rollos ausgew\u00e4hlt. Im Karteneditor die Ger\u00e4te w\u00e4hlen.",
    unknown: "unbekannt",
    phase: { night: "Nacht", day: "Tag", shading: "Beschattung", shading_ending: "Beschattung endet", unknown: "unbekannt" },
    contact: { open: "offen", tilted: "gekippt", closed: "geschlossen" },
    info: {
      clock: { short: "Zeit:", long: "Aktuelle Uhrzeit" },
      outdoor: { short: "Temp:", long: "Au\u00dfentemperatur" },
      brightness: { short: "Hell:", long: "Helligkeit" },
      elevation: { short: "Sonnenh\u00f6he:", long: "Sonnenh\u00f6he (Elevation)" },
      azimuth: { short: "Azimut:", long: "Sonnenrichtung (Azimut)" },
      sun: { short: "Sonne H\u00f6he/Az:", long: "Sonnenh\u00f6he (Elevation) / Sonnenrichtung (Azimut)" },
    },
    help: "Hilfe / Dokumentation",
    moving: { opening: "f\u00e4hrt hoch", closing: "f\u00e4hrt runter" },
    head: { status: "Status", phase: "Zustand", name: "Rollo", open: "Auf", close: "Zu", height: "H\u00f6he", move: "Fahren", last: "MyPos./Lam.", slats: "Lam." },
    editor: {
      title: "Titel",
      devices: "Rollos (Ger\u00e4te der Rollladen Steuerung)",
      show_state: "Zustand anzeigen",
      show_help: "Hilfe-Symbol (?) anzeigen",
      show_times: "Fahrzeiten anzeigen",
      show_header: "\u00dcberschriften anzeigen",
      show_seconds: "Sekunden anzeigen",
      show_clock: "Uhrzeit in der Info-Zeile",
      info_outdoor: "Info-Zeile: Au\u00dfentemperatur",
      info_brightness: "Info-Zeile: Helligkeit",
      info_elevation: "Info-Zeile: Elevation",
      info_azimuth: "Info-Zeile: Azimut",
    },
  },
  en: {
    height: "Height",
    slats: "Slats",
    up: "Up",
    stop: "Stop",
    down: "Down",
    mypos: "MyPosition",
    back: "Back",
    empty: "No shutters selected. Choose the devices in the card editor.",
    unknown: "unknown",
    phase: { night: "Night", day: "Day", shading: "Shading", shading_ending: "Shading ending", unknown: "unknown" },
    contact: { open: "open", tilted: "tilted", closed: "closed" },
    info: {
      clock: { short: "Time:", long: "Current time" },
      outdoor: { short: "Temp:", long: "Outdoor temperature" },
      brightness: { short: "Bright:", long: "Brightness" },
      elevation: { short: "SunAlt:", long: "Sun altitude (elevation)" },
      azimuth: { short: "Az:", long: "Sun azimuth" },
      sun: { short: "SunAlt/Az:", long: "Sun altitude (elevation) / azimuth" },
    },
    help: "Help / documentation",
    moving: { opening: "opening", closing: "closing" },
    head: { status: "Status", phase: "State", name: "Shutter", open: "Open", close: "Close", height: "Pos.", move: "Move", last: "MyPos./Slats", slats: "Slats" },
    editor: {
      title: "Title",
      devices: "Shutters (Rollladen Steuerung devices)",
      show_state: "Show state",
      show_help: "Show help icon (?)",
      show_times: "Show drive times",
      show_header: "Show headings",
      show_seconds: "Show seconds",
      show_clock: "Clock in the info row",
      info_outdoor: "Info row: outdoor temperature",
      info_brightness: "Info row: brightness",
      info_elevation: "Info row: elevation",
      info_azimuth: "Info row: azimuth",
    },
  },
};
const langOf = (hass) => ((hass?.locale?.language || hass?.language || "en").startsWith("de") ? "de" : "en");

const STEPS = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10, 0];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const ICONS = {
  button_up: '<svg viewBox="0 0 24 24"><path d="M12 4l-8 8h5v8h6v-8h5z"/></svg>',
  button_stop: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>',
  button_down: '<svg viewBox="0 0 24 24"><path d="M12 20l8-8h-5V4H9v8H4z"/></svg>',
  button_back: '<svg viewBox="0 0 24 24"><path d="M12.5 8c-2.65 0-5.05 1-6.9 2.6L2 7v9h9l-3.6-3.6A7.96 7.96 0 0112.5 10c3.5 0 6.5 2.3 7.5 5.5l2.4-.8C21.2 10.9 17.2 8 12.5 8z"/></svg>',
  button_mypos:
    '<svg viewBox="0 0 24 24"><path d="M3 3h18v4H3zM3 9h18v3H3zM3 14h18v3H3z"/><path d="M12 19l-3 3h6z"/></svg>',
};

const INFO = [
  { key: "outdoor", cfg: "info_outdoor", icon: "mdi:thermometer", unit: "\u00b0C", dec: 1 },
  { key: "brightness", cfg: "info_brightness", icon: "mdi:brightness-5", unit: "lx", dec: 0 },
  { key: "elevation", cfg: "info_elevation", icon: "mdi:weather-sunset-up", unit: "\u00b0", dec: 1, attr: "elevation" },
  { key: "azimuth", cfg: "info_azimuth", icon: "mdi:compass-outline", unit: "\u00b0", dec: 0, attr: "azimuth" },
];

class RollladenSteuerungCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._sig = "";
  }

  static getConfigElement() {
    return document.createElement(EDITOR_TYPE);
  }

  static getStubConfig(hass) {
    const ids = new Set();
    try {
      for (const e of Object.values(hass?.entities || {})) {
        if (e.platform === PLATFORM && e.device_id) ids.add(e.device_id);
      }
    } catch (_) { /* leave empty */ }
    return { type: `custom:${CARD_TYPE}`, devices: [...ids] };
  }

  setConfig(config) {
    if (!config || typeof config !== "object") throw new Error("Invalid configuration");
    this._config = {
      title: "",
      show_state: false,
      show_times: true,
      show_header: true,
      show_seconds: false,
      show_clock: true,
      show_help: true,
      ...config,
      devices: Array.isArray(config.devices) ? config.devices : [],
    };
    this._sig = "";
    this._maybeRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._maybeRender();
  }

  getCardSize() {
    return 1 + Math.max(1, this._config?.devices?.length || 1);
  }

  // ---------- Helpers ----------
  _hasFocus() {
    const a = this.shadowRoot.activeElement;
    return !!a && a.tagName === "SELECT";
  }

  _entityMap() {
    const ents = this._hass?.entities;
    if (this._map && this._mapSource === ents) return this._map;
    const map = {};
    for (const e of Object.values(ents || {})) {
      if (e.platform !== PLATFORM || !e.device_id || !e.translation_key) continue;
      (map[e.device_id] ||= {})[e.translation_key] = e.entity_id;
    }
    this._mapSource = ents;
    this._map = map;
    return map;
  }

  _st(devId, key) {
    const eid = this._entityMap()[devId]?.[key];
    return eid ? this._hass.states[eid] : undefined;
  }

  _num(devId, key) {
    const st = this._st(devId, key);
    if (!st || st.state === "unknown" || st.state === "unavailable") return null;
    const v = Number(st.state);
    return Number.isFinite(v) ? v : null;
  }

  _time(devId, key) {
    const st = this._st(devId, key);
    if (!st || st.state === "unknown" || st.state === "unavailable") return "\u2013";
    let m = /^(\d{1,2}):(\d{2})(:\d{2})?$/.exec(st.state);
    if (m) return this._config.show_seconds && m[3] ? st.state : `${m[1].padStart(2, "0")}:${m[2]}`;
    const d = new Date(st.state);
    if (!Number.isNaN(d.getTime())) {
      const pad = (n) => String(n).padStart(2, "0");
      return `${pad(d.getHours())}:${pad(d.getMinutes())}${this._config.show_seconds ? ":" + pad(d.getSeconds()) : ""}`;
    }
    return st.state;
  }

  _name(devId) {
    const d = this._hass.devices?.[devId];
    return d?.name_by_user || d?.name || devId;
  }

  _signature() {
    const parts = [langOf(this._hass), JSON.stringify([this._config.show_state, this._config.show_times, this._config.show_header, this._config.show_seconds, this._config.show_clock, this._config.show_help])];
    for (const id of this._config.devices) {
      const map = this._entityMap()[id] || {};
      parts.push(id, this._name(id));
      for (const key of ["target_position", "target_slat", "state", "input_contact", "delay_status", "button_mypos", "button_back", "input_morning", "input_evening"]) {
        const st = map[key] ? this._hass.states[map[key]] : undefined;
        parts.push(st ? st.state + (key === "state" ? "/" + st.attributes?.cover_state + "/" + st.attributes?.device_type : "") : "-");
      }
    }
    for (const i of INFO) {
      const eid = this._config[i.cfg];
      const st = eid ? this._hass.states[eid] : undefined;
      parts.push(eid ? `${eid}=${st ? st.state + "/" + (i.attr ? st.attributes?.[i.attr] : "") : "-"}` : "-");
    }
    return parts.join("|");
  }

  _infoValue(i) {
    const eid = this._config[i.cfg];
    if (!eid) return null;
    const st = this._hass.states[eid];
    const raw = st ? (i.attr && st.attributes?.[i.attr] != null ? st.attributes[i.attr] : st.state) : null;
    const v = raw == null || raw === "unknown" || raw === "unavailable" ? NaN : Number(raw);
    const lang = langOf(this._hass);
    const unit = (!i.attr && st?.attributes?.unit_of_measurement) || i.unit;
    const num = Number.isFinite(v)
      ? v.toLocaleString(lang, { minimumFractionDigits: i.dec, maximumFractionDigits: i.dec })
      : "\u2013";
    return { num, unit: Number.isFinite(v) ? unit : "" };
  }

  _clockText() {
    const opts = { hour: "2-digit", minute: "2-digit", hourCycle: "h23" };
    if (this._config.show_seconds) opts.second = "2-digit";
    const tz = this._hass?.config?.time_zone;
    if (tz) opts.timeZone = tz;
    try {
      return new Date().toLocaleTimeString(langOf(this._hass), opts);
    } catch (_) {
      return new Date().toLocaleTimeString();
    }
  }

  _tickClock() {
    const el = this.shadowRoot?.querySelector(".clock");
    if (el) el.textContent = this._clockText();
  }

  connectedCallback() {
    this._clockTimer = setInterval(() => this._tickClock(), 1000);
  }

  disconnectedCallback() {
    clearInterval(this._clockTimer);
    this._clockTimer = null;
  }

  _infoRow(t) {
    const val = Object.fromEntries(INFO.map((i) => [i.key, this._infoValue(i)]));
    const items = [];
    const add = (icon, label, text, title, html = false) =>
      items.push(`<span class="info" title="${esc(title)}"><ha-icon icon="${icon}"></ha-icon><b>${esc(label)}</b>\u202f${html ? text : esc(text)}</span>`);
    const one = (key, icon) => {
      const v = val[key];
      if (v) add(icon, t.info[key].short, `${v.num}${v.unit ? "\u202f" + v.unit : ""}`, t.info[key].long);
    };
    if (this._config.show_clock) add("mdi:clock-outline", t.info.clock.short, `<span class="clock">${esc(this._clockText())}</span>`, t.info.clock.long, true);
    one("outdoor", "mdi:thermometer");
    one("brightness", "mdi:white-balance-sunny");
    if (val.elevation && val.azimuth) {
      const e = val.elevation, a = val.azimuth;
      add("mdi:sun-compass", t.info.sun.short, `${e.num}${e.unit}/${a.num}${a.unit}`, t.info.sun.long);
    } else {
      one("elevation", "mdi:weather-sunset-up");
      one("azimuth", "mdi:compass-outline");
    }
    // "?" help icon at the right end of the row, linking to the README
    if (this._config.show_help !== false) {
      const lang = langOf(this._hass);
      items.push(`<a class="help" href="${DOCS[lang]}" target="_blank" rel="noopener noreferrer" title="${esc(t.help)}" aria-label="${esc(t.help)}">?</a>`);
    }
    return items.length ? `<div class="infos">${items.join("")}</div>` : "";
  }

  _maybeRender() {
    if (!this._config || !this._hass) return;
    const sig = this._signature();
    if (sig === this._sig) return;
    if (this._hasFocus()) return; // do not re-render a select while the user is operating it
    this._sig = sig;
    this._render();
  }

  // ---------- Rendering ----------
  _statusIcon(pos, phase, contact, moving, type) {
    const p = pos == null ? 0 : Math.max(0, Math.min(100, pos));
    const h = Math.round(24 * (1 - p / 100));
    const color =
      moving ? "var(--error-color, #db4437)"
      : phase === "night" ? "var(--info-color, #039be5)"
        : phase === "shading" || phase === "shading_ending" ? "var(--warning-color, #ff9800)"
          : "var(--success-color, #4c8c2b)";
    let slats = "";
    for (let y = 5; y < 2 + h; y += 3) slats += `<line x1="3" y1="${y}" x2="25" y2="${y}" stroke="var(--card-background-color,#fff)" stroke-width=".6" opacity=".7"/>`;
    const badge = contact === "open" || contact === "tilted"
      ? `<path d="M28 20l-6 8h6z" fill="var(--warning-color,#ff9800)"/>` : "";
    const arrow = moving === "closing"
      ? `<path d="M9 29h12l-6 6.5z" fill="currentColor"/>`
      : moving === "opening" ? `<path d="M9 35.5h12l-6-6.5z" fill="currentColor"/>` : "";
    if (type === "awning") {
      // Awning: striped cloth with scallops; 100 % = retracted (narrow roll), 0 % = fully extended
      const ah = 5 + 19 * (1 - p / 100);
      let cloth = "";
      for (let i = 0; i < 6; i++) {
        const x = 2 + i * 4;
        cloth += `<rect x="${x}" y="2" width="4" height="${ah}" fill="currentColor" opacity="${i % 2 ? 0.55 : 0.95}"/>`;
        cloth += `<path d="M${x} ${2 + ah}a2 2 0 0 0 4 0z" fill="currentColor" opacity="${i % 2 ? 0.55 : 0.95}"/>`;
      }
      return `<svg viewBox="0 0 30 36" width="29" height="35" style="color:${color}">
      <rect x="2" y="2" width="24" height="24" rx="2" fill="none" stroke="currentColor" stroke-width="1" opacity=".45"/>
      ${cloth}${badge}${arrow}</svg>`;
    }
    if (type === "door") {
      return `<svg viewBox="0 0 30 36" width="29" height="35" style="color:${color}">
      <rect x="5" y="2" width="18" height="24" rx="1.5" fill="none" stroke="currentColor" stroke-width="2"/>
      ${h > 0 ? `<rect x="5" y="2" width="18" height="${h}" fill="currentColor" opacity=".9"/>${slats.replace('x1="3"', 'x1="6"').replace(/x2="25"/g, 'x2="22"').replace(/x1="3"/g, 'x1="6"')}` : ""}
      <circle cx="19" cy="15" r="1.6" fill="var(--card-background-color,#fff)" stroke="currentColor" stroke-width="1"/>
      ${badge}${arrow}</svg>`;
    }
    return `<svg viewBox="0 0 30 36" width="29" height="35" style="color:${color}">
      <rect x="2" y="2" width="24" height="24" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>
      <line x1="14" y1="2" x2="14" y2="26" stroke="currentColor" stroke-width="1.5"/>
      ${h > 0 ? `<rect x="2" y="2" width="24" height="${h}" fill="currentColor" opacity=".9"/>${slats}` : ""}
      ${badge}${arrow}</svg>`;
  }

  _options(current) {
    const set = new Set(STEPS);
    const cur = current == null ? null : Math.round(current);
    const list = cur != null && !set.has(cur) ? [...STEPS, cur].sort((a, b) => b - a) : STEPS;
    const empty = cur == null ? '<option value="" selected>-</option>' : "";
    return empty + list.map((v) => `<option value="${v}"${v === cur ? " selected" : ""}>${v}</option>`).join("");
  }

  _render() {
    const t = TEXTS[langOf(this._hass)];
    const cfg = this._config;
    const map0 = this._entityMap();
    const hasTimes =
      cfg.show_times && cfg.devices.some((id) => map0[id]?.input_morning || map0[id]?.input_evening);
    const hasMy = cfg.devices.some((id) => map0[id]?.button_mypos);
    const hasSlat = cfg.devices.some((id) => map0[id]?.target_slat);
    const rows = cfg.devices.map((id) => {
      const map = this._entityMap()[id] || {};
      const pos = this._num(id, "target_position");
      const phase = this._st(id, "state")?.state || "unknown";
      const contact = this._st(id, "input_contact")?.state;
      const cs = this._st(id, "state")?.attributes?.cover_state;
      const moving = cs === "opening" || cs === "closing" ? cs : null;
      const tip = [
        `${t.phase[phase] || phase}`,
        moving ? t.moving[moving] : null,
        contact && t.contact[contact] ? `${t.contact[contact]}` : null,
        pos != null ? `${Math.round(pos)} %` : t.unknown,
      ].filter(Boolean).join(" \u00b7 ");
      const btn = (key, cls = "b") =>
        map[key]
          ? `<td class="${cls}"><button class="ic" data-press="${esc(map[key])}" title="${t[key.replace("button_", "")]}" aria-label="${t[key.replace("button_", "")]}">${ICONS[key]}</button></td>`
          : `<td class="${cls}"></td>`;
      const slatSel = map.target_slat
        ? `<select class="sel" data-set="${esc(map.target_slat)}" title="${t.slats}">${this._options(this._num(id, "target_slat"))}</select>`
        : "";
      const myBtn = map.button_mypos ? btn("button_mypos").replace('<td class="b">', "").replace("</td>", "") : "";
      const last = hasMy || hasSlat ? `<td class="b g">${myBtn}${slatSel}</td>` : "";
      const state = cfg.show_state
        ? `<td class="s g">${esc(t.phase[phase] || phase)}${this._st(id, "delay_status") && this._st(id, "delay_status").state !== "keine" && this._st(id, "delay_status").state !== "none" ? `<br><small>${esc(this._st(id, "delay_status").state)}</small>` : ""}</td>`
        : "";
      return `<tr>
        <th><a class="dev" data-device="${esc(id)}" href="/config/devices/device/${esc(id)}">${esc(this._name(id))}</a></th>
        <td class="st g" title="${esc(tip)}">${this._statusIcon(pos, phase, contact, moving, this._st(id, "state")?.attributes?.device_type)}</td>
        ${hasTimes ? `<td class="t g">${this._time(id, "input_morning")}</td><td class="t g">${this._time(id, "input_evening")}</td>` : ""}
        <td class="h g">${map.target_position ? `<select class="sel" data-set="${esc(map.target_position)}" title="${t.height}">${this._options(pos)}</select>` : ""}</td>
        ${btn("button_up", "b g")}${btn("button_stop")}${btn("button_down")}${btn("button_back")}${last}${state}
      </tr>`;
    });
    const th = t.head;
    const head = `<thead><tr><th>${th.name}</th><th class="g">${th.status}</th>${hasTimes ? `<th class="g">${th.open}</th><th class="g">${th.close}</th>` : ""}<th class="g">${th.height}</th><th class="g" colspan="4">${th.move}</th>${hasMy || hasSlat ? `<th class="g">${hasMy && hasSlat ? th.last : hasMy ? "MyPos." : th.slats}</th>` : ""}${cfg.show_state ? `<th class="g">${th.phase}</th>` : ""}</tr></thead>`;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        table { width: 100%; border-collapse: collapse; white-space: nowrap; }
        tr:nth-child(odd) { background: color-mix(in srgb, var(--primary-text-color, #000) 4%, transparent); }
        th, td { padding: 4px 8px; vertical-align: middle; text-align: center; }
        th { text-align: left; font-weight: 500; }
        a.dev { color: var(--primary-color, #03a9f4); text-decoration: none; cursor: pointer; }
        a.dev:hover { text-decoration: underline; }
        button.ic { background: none; border: 1px solid var(--divider-color, #ccc); border-radius: 8px;
          width: 38px; height: 34px; padding: 6px; cursor: pointer; color: var(--primary-text-color); }
        button.ic:hover { background: color-mix(in srgb, var(--primary-color, #03a9f4) 18%, transparent); }
        button.ic svg { width: 100%; height: 100%; fill: currentColor; }
        select.sel { background: var(--card-background-color, #fff); color: var(--primary-text-color);
          border: 1px solid var(--divider-color, #999); border-radius: 4px; padding: 3px 4px; font: inherit; }
        td.s { text-align: left; }
        td.t { font-variant-numeric: tabular-nums; }
        thead th { font-size: 0.78em; font-weight: 400; color: var(--secondary-text-color);
          padding: 2px 8px; border-bottom: 1px solid var(--divider-color, #ddd); text-align: center; }
        thead th:first-child { text-align: left; }
        .infos { display: flex; flex-wrap: wrap; gap: 4px 16px; padding: 8px 12px 4px;
          color: var(--secondary-text-color); font-size: 0.9em; }
        .info { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap;
          font-variant-numeric: tabular-nums; }
        .info ha-icon { --mdc-icon-size: 18px; }
        .info b { font-weight: 500; color: var(--primary-text-color); }
        a.help { margin-left: auto; width: 20px; height: 20px; box-sizing: border-box; border-radius: 50%;
          border: 1.5px solid var(--secondary-text-color); color: var(--secondary-text-color);
          display: inline-flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600;
          text-decoration: none; line-height: 1; }
        a.help:hover { color: var(--primary-color, #03a9f4); border-color: var(--primary-color, #03a9f4); }
        .info + .info { padding-left: 16px; border-left: 1px solid var(--divider-color, #ddd); }
        .g { border-left: 1px solid var(--divider-color, #ddd); }
        .empty { padding: 16px; color: var(--secondary-text-color); }
      </style>
      <ha-card${cfg.title ? ` header="${esc(cfg.title)}"` : ""}>
        ${this._infoRow(t)}
        ${rows.length ? `<table>${cfg.show_header ? head : ""}<tbody>${rows.join("")}</tbody></table>` : `<div class="empty">${t.empty}</div>`}
      </ha-card>`;

    const root = this.shadowRoot;
    root.querySelectorAll("a.dev").forEach((a) =>
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        history.pushState(null, "", a.getAttribute("href"));
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      })
    );
    root.querySelectorAll("button[data-press]").forEach((b) =>
      b.addEventListener("click", () =>
        this._hass.callService("button", "press", { entity_id: b.getAttribute("data-press") })
      )
    );
    root.querySelectorAll("select[data-set]").forEach((s) =>
      s.addEventListener("change", () => {
        if (s.value === "") return;
        this._hass.callService("number", "set_value", {
          entity_id: s.getAttribute("data-set"),
          value: Number(s.value),
        });
        s.blur();
        this._sig = "";
      })
    );
  }
}

class RollladenSteuerungCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this._config || !this._hass) return;
    const t = TEXTS[langOf(this._hass)];
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        ev.stopPropagation();
        const config = { ...this._config, ...ev.detail.value, type: `custom:${CARD_TYPE}` };
        this._config = config;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = { title: "", devices: [], show_times: true, show_seconds: false, show_clock: true, show_header: true, show_state: false, show_help: true, ...this._config };
    this._form.schema = [
      { name: "title", selector: { text: {} } },
      { name: "devices", selector: { device: { integration: PLATFORM, multiple: true } } },
      { name: "show_times", selector: { boolean: {} } },
      { name: "show_seconds", selector: { boolean: {} } },
      { name: "show_clock", selector: { boolean: {} } },
      { name: "show_header", selector: { boolean: {} } },
      { name: "show_state", selector: { boolean: {} } },
      { name: "show_help", selector: { boolean: {} } },
      { name: "info_outdoor", selector: { entity: {} } },
      { name: "info_brightness", selector: { entity: {} } },
      { name: "info_elevation", selector: { entity: {} } },
      { name: "info_azimuth", selector: { entity: {} } },
    ];
    this._form.computeLabel = (schema) => t.editor[schema.name] || schema.name;
  }
}

if (!customElements.get(CARD_TYPE)) customElements.define(CARD_TYPE, RollladenSteuerungCard);
if (!customElements.get(EDITOR_TYPE)) customElements.define(EDITOR_TYPE, RollladenSteuerungCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: "Rollladen Steuerung",
    description: "Tabelle zur manuellen Steuerung und \u00dcberwachung der Rollos: Status, H\u00f6he, Hoch/Stopp/Runter, Beschattung bzw. Lamellen.",
    preview: false,
  });
}
