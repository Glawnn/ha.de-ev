const CARD_TYPE = "de-ev-charger";
const CARD_NAME = "Dé EV Charger";
const POPUP_VARIANTS = ["centered", "stepper", "native"];
const CURRENT_CONTROLS = ["popup", "slider"];
const CURRENT_PRESETS = [6, 8, 10, 13, 16, 20, 24, 32];

const LABELS = {
  en: {
    title: "EV Charger",
    power: "Instantaneous power",
    energy: "Energy",
    duration: "Duration",
    current: "Current",
    charging_current: "Charging current",
    adjust_current: "Current adjustment",
    start: "Start",
    stop: "Stop",
    cancel: "Cancel",
    apply: "Apply",
    close: "Close",
    unavailable: "Unavailable",
    unknown: "Unknown",
  },
  fr: {
    title: "Borne VE",
    power: "Puissance instantanée",
    energy: "Énergie",
    duration: "Durée",
    current: "Courant",
    charging_current: "Courant de charge",
    adjust_current: "Réglage du courant",
    start: "Démarrer",
    stop: "Arrêter",
    cancel: "Annuler",
    apply: "Appliquer",
    close: "Fermer",
    unavailable: "Indisponible",
    unknown: "Inconnu",
  },
};

const STATUS_LABELS = {
  en: {
    unknown: "Unknown",
    sleep: "Sleeping",
    idle: "Available",
    plugged_in: "Vehicle detected",
    charging: "Charging",
    waiting: "Waiting",
    fault: "Fault",
    paused: "Paused",
    charged: "Charge complete",
  },
  fr: {
    unknown: "Inconnu",
    sleep: "En veille",
    idle: "Disponible",
    plugged_in: "Véhicule détecté",
    charging: "En charge",
    waiting: "En attente",
    fault: "Défaut",
    paused: "En pause",
    charged: "Charge terminée",
  },
};

const STYLES = `
  :host {
    display: block;
    container-type: inline-size;
  }
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  ha-card {
    overflow: hidden;
    background: var(--ha-card-background, var(--card-background-color));
    color: var(--primary-text-color);
  }
  .split {
    display: grid;
    grid-template-columns: minmax(0, .95fr) minmax(0, 1.05fr);
    min-height: 190px;
  }
  .hero {
    display: flex;
    flex-direction: column;
    min-width: 0;
    padding: 18px;
    border-right: 1px solid var(--divider-color);
    background: var(--secondary-background-color);
    background: linear-gradient(
      160deg,
      color-mix(in srgb, var(--success-color) 16%, var(--ha-card-background, var(--card-background-color))),
      var(--ha-card-background, var(--card-background-color))
    );
  }
  .hero-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }
  .heading {
    min-width: 0;
  }
  .title {
    overflow: hidden;
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.2;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .subtitle {
    margin-top: 2px;
    overflow: hidden;
    color: var(--secondary-text-color);
    font-size: .75rem;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .status {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: 6px;
    color: var(--secondary-text-color);
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .04em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--disabled-text-color, #8a8a8a);
  }
  .status[data-state="charging"] .status-dot {
    background: var(--success-color);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--success-color) 18%, transparent);
  }
  .status[data-state="fault"] .status-dot {
    background: var(--error-color);
  }
  .status[data-state="paused"] .status-dot,
  .status[data-state="waiting"] .status-dot {
    background: var(--warning-color, #f5a623);
  }
  .power {
    display: flex;
    align-items: baseline;
    gap: 6px;
    min-width: 0;
    margin-top: 22px;
  }
  .power-value {
    overflow: hidden;
    font-size: 2.3rem;
    font-weight: 600;
    letter-spacing: -.05em;
    line-height: 1;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .power-unit {
    color: var(--secondary-text-color);
    font-size: .8rem;
    font-weight: 500;
  }
  .power-label {
    margin-top: 4px;
    color: var(--secondary-text-color);
    font-size: .64rem;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .details {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 12px;
    min-width: 0;
    padding: 16px 18px;
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
  .detail {
    min-width: 0;
    padding-bottom: 9px;
    border-bottom: 1px solid var(--divider-color);
  }
  .detail-label {
    display: block;
    color: var(--secondary-text-color);
    font-size: .64rem;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .detail-value {
    display: block;
    margin-top: 3px;
    overflow: hidden;
    font-size: 1rem;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .controls {
    display: flex;
    gap: 8px;
    min-width: 0;
  }
  .inline-control {
    display: flex;
    flex-direction: column;
    gap: 7px;
    min-width: 0;
  }
  .inline-head {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }
  .inline-head .session-button {
    padding: 6px 10px;
    font-size: .7rem;
  }
  .inline-control .range {
    margin-top: 2px;
  }
  .current-control {
    display: flex;
    flex: 1;
    align-items: center;
    gap: 6px;
    min-width: 0;
    padding: 8px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font: inherit;
    text-align: left;
    cursor: pointer;
  }
  .current-control:hover {
    border-color: var(--primary-color);
  }
  .current-control:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  .current-control[disabled] {
    cursor: default;
    opacity: .55;
  }
  .current-caption {
    color: var(--secondary-text-color);
    font-size: .64rem;
    letter-spacing: .08em;
    text-transform: uppercase;
  }
  .current-value {
    margin-left: auto;
    font-size: .8rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .chev {
    flex: 0 0 auto;
    width: 7px;
    height: 7px;
    margin-left: 1px;
    border-right: 1.5px solid currentColor;
    border-bottom: 1.5px solid currentColor;
    opacity: .55;
    transform: rotate(-45deg);
  }
  .session-button {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    padding: 8px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 10px;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
    font-size: .75rem;
    font-weight: 600;
    white-space: nowrap;
    cursor: pointer;
  }
  .session-button[data-on="true"] {
    border-color: color-mix(in srgb, var(--error-color) 40%, var(--divider-color));
    background: color-mix(in srgb, var(--error-color) 10%, var(--ha-card-background, var(--card-background-color)));
    color: var(--error-color);
  }
  .session-button[data-on="false"] {
    border-color: color-mix(in srgb, var(--success-color) 40%, var(--divider-color));
    background: color-mix(in srgb, var(--success-color) 10%, var(--ha-card-background, var(--card-background-color)));
    color: var(--success-color);
  }
  .session-button[disabled] {
    cursor: default;
    opacity: .55;
  }
  dialog.popup {
    max-width: none;
    max-height: none;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--primary-text-color);
  }
  dialog.popup::backdrop {
    background: rgba(0, 0, 0, .5);
    backdrop-filter: blur(3px);
  }
  dialog.center {
    position: fixed;
    inset: 0;
    width: min(380px, calc(100vw - 32px));
    margin: auto;
  }
  dialog.center.wide {
    width: min(440px, calc(100vw - 24px));
  }
  .popup-card {
    width: 100%;
    max-height: calc(100dvh - 24px);
    overflow: auto;
    padding: 18px;
    border: 1px solid var(--divider-color);
    border-radius: 20px;
    background: var(--ha-card-background, var(--card-background-color));
    box-shadow: 0 20px 60px rgba(0, 0, 0, .35);
  }
  dialog.center .popup-card {
    max-height: calc(100dvh - 32px);
  }
  .popup-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }
  .popup-kicker {
    color: var(--secondary-text-color);
    font-size: .64rem;
    letter-spacing: .1em;
    text-transform: uppercase;
  }
  .popup-title {
    margin-top: 2px;
    font-size: 1.05rem;
    font-weight: 600;
  }
  .icon-button {
    display: grid;
    flex: 0 0 auto;
    place-items: center;
    width: 32px;
    height: 32px;
    padding: 0;
    border: 0;
    border-radius: 50%;
    background: transparent;
    color: var(--secondary-text-color);
    font-family: inherit;
    font-size: 1.35rem;
    font-weight: 400;
    line-height: 1;
    cursor: pointer;
  }
  .icon-button:hover {
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
  }
  .current-big {
    display: flex;
    align-items: baseline;
    justify-content: center;
    gap: 6px;
    margin: 20px 0 16px;
  }
  .current-number {
    font-size: 3rem;
    font-weight: 600;
    letter-spacing: -.05em;
    line-height: 1;
  }
  .current-unit {
    color: var(--secondary-text-color);
    font-size: .9rem;
  }
  .range-wrap {
    display: grid;
    gap: 6px;
  }
  .range {
    width: 100%;
    height: 6px;
    border-radius: 999px;
    outline: none;
    background: linear-gradient(
      to right,
      var(--primary-color) 0 var(--fill, 0%),
      var(--secondary-background-color) var(--fill, 0%) 100%
    );
    cursor: pointer;
    appearance: none;
  }
  .range::-webkit-slider-thumb {
    width: 22px;
    height: 22px;
    border: 3px solid var(--ha-card-background, var(--card-background-color));
    border-radius: 50%;
    background: var(--primary-color);
    box-shadow: 0 1px 5px rgba(0, 0, 0, .3);
    appearance: none;
  }
  .range::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border: 3px solid var(--ha-card-background, var(--card-background-color));
    border-radius: 50%;
    background: var(--primary-color);
  }
  .range-labels {
    display: flex;
    justify-content: space-between;
    color: var(--secondary-text-color);
    font-size: .64rem;
  }
  .range:disabled {
    cursor: default;
    opacity: .55;
  }
  .presets {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 16px 0;
  }
  .preset {
    padding: 6px 10px;
    border: 1px solid var(--divider-color);
    border-radius: 999px;
    background: transparent;
    color: var(--primary-text-color);
    font-family: inherit;
    font-size: .7rem;
    font-weight: 600;
    cursor: pointer;
  }
  .preset:hover {
    border-color: var(--primary-color);
  }
  .preset.active {
    border-color: var(--primary-color);
    background: var(--primary-color);
    color: var(--text-primary-color);
  }
  .popup-actions {
    display: flex;
    gap: 8px;
  }
  .popup-actions button {
    flex: 1;
    padding: 10px 12px;
    border-radius: 10px;
    font-family: inherit;
    font-size: .8rem;
    font-weight: 600;
    cursor: pointer;
  }
  .popup-actions button[disabled] {
    cursor: default;
    opacity: .55;
  }
  .popup-actions .ghost {
    border: 1px solid var(--divider-color);
    background: transparent;
    color: var(--primary-text-color);
  }
  .popup-actions .primary {
    border: 1px solid var(--primary-color);
    background: var(--primary-color);
    color: var(--text-primary-color);
  }
  .popup-error {
    margin-top: 10px;
    color: var(--error-color);
    font-size: .75rem;
  }
  .stepper-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
    margin: 18px 0 14px;
  }
  .stepper-row .current-big {
    margin: 0;
  }
  .round {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border: 1px solid var(--divider-color);
    border-radius: 50%;
    background: var(--secondary-background-color);
    color: var(--primary-text-color);
    font-family: inherit;
    font-size: 1.25rem;
    font-weight: 500;
    line-height: 1;
    cursor: pointer;
  }
  .round:hover {
    border-color: var(--primary-color);
  }
  .range-track {
    height: 6px;
    overflow: hidden;
    border-radius: 999px;
    background: var(--secondary-background-color);
  }
  .range-track span {
    display: block;
    width: 0;
    height: 100%;
    border-radius: inherit;
    background: var(--primary-color);
  }
  @container (max-width: 430px) {
    .split {
      grid-template-columns: 1fr;
    }
    .hero {
      border-right: 0;
      border-bottom: 1px solid var(--divider-color);
    }
    .power {
      margin-top: 16px;
    }
    .details {
      gap: 10px;
    }
  }
`;

class DeEvChargerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._entities = {};
    this._built = false;
    this._pendingSession = false;
    this._range = { min: 6, max: 32, step: 1 };
    this._draftCurrent = null;
    this._dirty = false;
    this._inlineEditing = false;
  }

  static getStubConfig(hass, entities) {
    const candidates = entities || [];
    const entity =
      candidates.find(
        (candidate) =>
          candidate.startsWith("sensor.") && candidate.endsWith("_status"),
      ) || candidates.find((candidate) => candidate.startsWith("sensor."));
    return entity ? { entity } : {};
  }

  static getConfigElement() {
    return document.createElement("de-ev-charger-card-editor");
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid configuration");
    }
    if (!config.device_id && !config.entity && !config.entities) {
      throw new Error("Define device_id, entity, or entities for the charger");
    }
    if (
      config.entities !== undefined &&
      (typeof config.entities !== "object" ||
        config.entities === null ||
        Array.isArray(config.entities))
    ) {
      throw new Error("entities must be a mapping of metric names to entity IDs");
    }
    const popup = config.popup === "sheet" ? "centered" : config.popup || "centered";
    if (!POPUP_VARIANTS.includes(popup)) {
      throw new Error(`popup must be one of: ${POPUP_VARIANTS.join(", ")}`);
    }
    const currentControl = config.current_control || "popup";
    if (!CURRENT_CONTROLS.includes(currentControl)) {
      throw new Error(`current_control must be one of: ${CURRENT_CONTROLS.join(", ")}`);
    }
    this._closePopup();
    this._config = {
      device_id: config.device_id,
      entity: config.entity,
      title: config.title,
      entities: config.entities || {},
      popup,
      current_control: currentControl,
    };
    this._built = false;
    this._inlineEditing = false;
    if (this.shadowRoot && this._hass) {
      this._render();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) {
      return;
    }
    if (!this._built) {
      this._render();
      return;
    }
    this._update();
  }

  getCardSize() {
    return 4;
  }

  _language() {
    return (this._hass?.language || "en").toLowerCase().startsWith("fr")
      ? "fr"
      : "en";
  }

  _t(key) {
    return LABELS[this._language()][key] || LABELS.en[key] || key;
  }

  _statusLabel(state) {
    if (!state || state === "unavailable") {
      return this._t("unavailable");
    }
    const language = this._language();
    return (
      STATUS_LABELS[language][state] ||
      STATUS_LABELS.en[state] ||
      state ||
      this._t("unknown")
    );
  }

  _resolveEntities() {
    const resolved = { ...(this._config?.entities || {}) };
    if (!this._hass || !this._config) {
      return resolved;
    }
    if (this._config.entity && !resolved.status) {
      resolved.status = this._config.entity;
    }
    const registry = this._hass.entities;
    if (!registry) {
      return resolved;
    }
    const deviceId = this._resolveDeviceId();
    if (!deviceId) {
      return resolved;
    }
    for (const [entityId, entry] of Object.entries(registry)) {
      if (entry.device_id !== deviceId || entry.platform !== "de_ev") {
        continue;
      }
      const key =
        entry.translation_key || this._keyFromUniqueId(entry.unique_id);
      if (key && !(key in resolved)) {
        resolved[key] = entityId;
      }
    }
    return resolved;
  }

  _resolveDeviceId() {
    if (this._config.device_id && this._hass.devices?.[this._config.device_id]) {
      return this._config.device_id;
    }
    if (this._config.entity) {
      const entry = this._hass.entities?.[this._config.entity];
      if (entry?.device_id) {
        return entry.device_id;
      }
    }
    if (this._config.device_id) {
      const device = Object.values(this._hass.devices || {}).find((candidate) =>
        (candidate.identifiers || []).some(
          ([domain, identifier]) =>
            domain === "de_ev" && identifier === this._config.device_id,
        ),
      );
      return device?.id || this._config.device_id;
    }
    return null;
  }

  _keyFromUniqueId(uniqueId) {
    if (!uniqueId) {
      return null;
    }
    const keys = [
      "charge_current",
      "charge_session",
      "energy_session",
      "session_duration",
      "status",
      "power",
    ];
    return keys.find((key) => uniqueId.endsWith(`_${key}`)) || null;
  }

  _stateFor(key) {
    const entityId = this._entities?.[key];
    return entityId && this._hass?.states ? this._hass.states[entityId] : undefined;
  }

  _deviceName() {
    if (!this._hass) {
      return null;
    }
    const deviceId = this._resolveDeviceId();
    const device = deviceId ? this._hass.devices?.[deviceId] : undefined;
    return device?.name_by_user || device?.name || null;
  }

  _isUnavailable(state) {
    return (
      !state || state.state === "unavailable" || state.state === "unknown"
    );
  }

  _powerParts(state) {
    if (this._isUnavailable(state)) {
      return { value: this._t("unavailable"), unit: "" };
    }
    const value = Number(state.state);
    if (!Number.isFinite(value)) {
      return { value: state.state, unit: "" };
    }
    const unit = state.attributes?.unit_of_measurement || "W";
    if (unit === "kW") {
      return { value: value.toFixed(2), unit: "kW" };
    }
    if (unit === "W") {
      return Math.abs(value) >= 1000
        ? { value: (value / 1000).toFixed(2), unit: "kW" }
        : { value: String(Math.round(value)), unit: "W" };
    }
    return { value: String(value), unit };
  }

  _formatEnergy(state) {
    if (this._isUnavailable(state)) {
      return this._t("unavailable");
    }
    const value = Number(state.state);
    if (!Number.isFinite(value)) {
      return state.state;
    }
    const unit = state.attributes?.unit_of_measurement || "kWh";
    if (unit === "Wh") {
      return `${(value / 1000).toFixed(2)} kWh`;
    }
    if (unit === "kWh") {
      return `${value.toFixed(2)} kWh`;
    }
    return `${value} ${unit}`;
  }

  _formatDuration(state) {
    if (this._isUnavailable(state)) {
      return this._t("unavailable");
    }
    const value = Number(state.state);
    if (!Number.isFinite(value)) {
      return state.state;
    }
    const total = Math.max(0, Math.round(value));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    if (hours > 0) {
      return `${hours} h ${String(minutes).padStart(2, "0")} min`;
    }
    return `${minutes} min ${String(seconds).padStart(2, "0")} s`;
  }

  _formatCurrent(state) {
    if (this._isUnavailable(state)) {
      return this._t("unavailable");
    }
    const value = Number(state.state);
    if (!Number.isFinite(value)) {
      return state.state;
    }
    const unit = state.attributes?.unit_of_measurement || "A";
    const formatted = Number.isInteger(value) ? String(value) : value.toFixed(1);
    return `${formatted} ${unit}`;
  }

  _currentRange(state) {
    const attributes = state?.attributes || {};
    const min = Number(attributes.min);
    const max = Number(attributes.max);
    const step = Number(attributes.step);
    return {
      min: Number.isFinite(min) ? min : 6,
      max: Number.isFinite(max) ? max : 32,
      step: Number.isFinite(step) && step > 0 ? step : 1,
    };
  }

  _clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  _fillRange(element, value, range) {
    const span = range.max - range.min;
    const percent = span > 0 ? ((value - range.min) / span) * 100 : 0;
    element.style.setProperty("--fill", `${percent}%`);
  }

  _formatCurrentValue(value) {
    const unit =
      this._stateFor("charge_current")?.attributes?.unit_of_measurement || "A";
    return `${Number.isInteger(value) ? value : value.toFixed(1)} ${unit}`;
  }

  _canControlCurrent() {
    return !this._isUnavailable(this._stateFor("charge_current"));
  }

  _canControlSession() {
    return !this._isUnavailable(this._stateFor("charge_session"));
  }

  _sessionOn() {
    return this._stateFor("charge_session")?.state === "on";
  }

  _render() {
    if (!this._config) {
      return;
    }
    this._entities = this._resolveEntities();
    const controls =
      this._config.current_control === "slider"
        ? `
          <div class="inline-control">
            <div class="inline-head">
              <span class="current-caption"></span>
              <span class="current-value"></span>
              <button class="session-button" type="button"></button>
            </div>
            <input class="range inline-range" type="range">
            <div class="range-labels"><span class="range-min"></span><span class="range-max"></span></div>
          </div>
        `
        : `
          <div class="controls">
            <button class="current-control" type="button">
              <span class="current-caption"></span>
              <span class="current-value"></span>
              <span class="chev" aria-hidden="true"></span>
            </button>
            <button class="session-button" type="button"></button>
          </div>
        `;
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card>
        <div class="split">
          <section class="hero">
            <div class="hero-head">
              <div class="heading">
                <div class="title"></div>
                <div class="subtitle"></div>
              </div>
              <div class="status"><span class="status-dot"></span><span class="status-text"></span></div>
            </div>
            <div class="power">
              <span class="power-value"></span>
              <span class="power-unit"></span>
            </div>
            <div class="power-label"></div>
          </section>
          <section class="details">
            <div class="stats">
              <div class="detail">
                <span class="detail-label"></span>
                <span class="detail-value energy"></span>
              </div>
              <div class="detail">
                <span class="detail-label"></span>
                <span class="detail-value duration"></span>
              </div>
            </div>
            ${controls}
          </section>
        </div>
      </ha-card>
      ${this._config.current_control === "popup" ? '<dialog class="popup" aria-labelledby="de-ev-popup-title"></dialog>' : ""}
    `;
    this._titleEl = this.shadowRoot.querySelector(".title");
    this._subtitleEl = this.shadowRoot.querySelector(".subtitle");
    this._statusEl = this.shadowRoot.querySelector(".status");
    this._statusTextEl = this.shadowRoot.querySelector(".status-text");
    this._powerValueEl = this.shadowRoot.querySelector(".power-value");
    this._powerUnitEl = this.shadowRoot.querySelector(".power-unit");
    this._powerLabelEl = this.shadowRoot.querySelector(".power-label");
    this._energyEl = this.shadowRoot.querySelector(".energy");
    this._durationEl = this.shadowRoot.querySelector(".duration");
    this._detailLabels = this.shadowRoot.querySelectorAll(".detail-label");
    this._currentCaptionEl = this.shadowRoot.querySelector(".current-caption");
    this._currentValueEl = this.shadowRoot.querySelector(".current-value");
    this._currentButton = this.shadowRoot.querySelector(".current-control");
    this._inlineRangeEl = this.shadowRoot.querySelector(".inline-range");
    this._inlineMinEl = this.shadowRoot.querySelector(".range-min");
    this._inlineMaxEl = this.shadowRoot.querySelector(".range-max");
    this._sessionButton = this.shadowRoot.querySelector(".session-button");
    this._dialog = this.shadowRoot.querySelector(".popup");
    if (this._dialog) {
      this._dialog.addEventListener("close", () => {
        this._draftCurrent = null;
        this._dirty = false;
      });
      this._dialog.addEventListener("click", (event) => {
        if (event.target === this._dialog) {
          this._dialog.close();
        }
      });
    }
    if (this._currentButton) {
      this._currentButton.addEventListener("click", () => this._openPopup());
    }
    if (this._inlineRangeEl) {
      this._inlineRangeEl.addEventListener("input", () => this._onInlineInput());
      this._inlineRangeEl.addEventListener("change", () => this._onInlineChange());
      this._inlineRangeEl.addEventListener("pointerdown", () => {
        this._inlineEditing = true;
      });
      this._inlineRangeEl.addEventListener("blur", () => {
        if (this._inlineEditing) {
          this._inlineEditing = false;
          this._update();
        }
      });
    }
    if (this._sessionButton) {
      this._sessionButton.addEventListener("click", () => this._toggleSession());
    }
    this._built = true;
    this._update();
  }

  _update() {
    if (!this._built) {
      return;
    }
    const deviceName = this._deviceName();
    const title = this._config.title || deviceName || this._t("title");
    this._titleEl.textContent = title;
    this._subtitleEl.textContent =
      this._config.title && deviceName ? deviceName : "";
    this._subtitleEl.style.display = this._subtitleEl.textContent ? "" : "none";

    const status = this._stateFor("status");
    const statusState = status?.state || "unavailable";
    this._statusEl.dataset.state = statusState;
    this._statusTextEl.textContent = this._statusLabel(statusState);

    const power = this._powerParts(this._stateFor("power"));
    this._powerValueEl.textContent = power.value;
    this._powerUnitEl.textContent = power.unit;
    this._powerUnitEl.style.display = power.unit ? "" : "none";
    this._powerLabelEl.textContent = this._t("power");

    this._detailLabels[0].textContent = this._t("energy");
    this._detailLabels[1].textContent = this._t("duration");
    this._energyEl.textContent = this._formatEnergy(
      this._stateFor("energy_session"),
    );
    this._durationEl.textContent = this._formatDuration(
      this._stateFor("session_duration"),
    );

    const currentState = this._stateFor("charge_current");
    const canControlCurrent = this._canControlCurrent();
    this._currentCaptionEl.textContent = this._t("current");
    if (this._config.current_control === "slider") {
      const range = this._currentRange(currentState);
      const stateValue = Number(currentState?.state);
      const value = this._clamp(
        Number.isFinite(stateValue) ? stateValue : range.min,
        range.min,
        range.max,
      );
      this._inlineRangeEl.min = String(range.min);
      this._inlineRangeEl.max = String(range.max);
      this._inlineRangeEl.step = String(range.step);
      this._inlineRangeEl.disabled = !canControlCurrent;
      this._inlineRangeEl.setAttribute(
        "aria-label",
        this._t("charging_current"),
      );
      this._inlineRangeEl.title = canControlCurrent
        ? this._t("charging_current")
        : this._t("unavailable");
      this._inlineMinEl.textContent = `${range.min} A`;
      this._inlineMaxEl.textContent = `${range.max} A`;
      if (!this._inlineEditing) {
        this._inlineRangeEl.value = String(value);
        this._currentValueEl.textContent = this._formatCurrent(currentState);
        this._fillRange(this._inlineRangeEl, value, range);
      }
    } else {
      this._currentValueEl.textContent = this._formatCurrent(currentState);
      this._currentButton.disabled = !canControlCurrent;
      this._currentButton.setAttribute(
        "aria-label",
        `${this._t("charging_current")}: ${this._formatCurrent(currentState)}`,
      );
      this._currentButton.title = canControlCurrent
        ? this._t("charging_current")
        : this._t("unavailable");
    }

    const canControlSession = this._canControlSession();
    const sessionOn = this._sessionOn();
    this._sessionButton.disabled = !canControlSession || this._pendingSession;
    this._sessionButton.textContent = sessionOn
      ? this._t("stop")
      : this._t("start");
    this._sessionButton.dataset.on = sessionOn ? "true" : "false";
    this._sessionButton.setAttribute(
      "aria-label",
      sessionOn ? this._t("stop") : this._t("start"),
    );
  }

  _onInlineInput() {
    if (!this._inlineRangeEl || !this._canControlCurrent()) {
      return;
    }
    this._inlineEditing = true;
    const value = Number(this._inlineRangeEl.value);
    this._currentValueEl.textContent = this._formatCurrentValue(value);
    this._fillRange(
      this._inlineRangeEl,
      value,
      this._currentRange(this._stateFor("charge_current")),
    );
  }

  async _onInlineChange() {
    if (!this._inlineRangeEl) {
      return;
    }
    this._inlineEditing = false;
    await this._setCurrentValue(Number(this._inlineRangeEl.value));
  }

  async _setCurrentValue(value) {
    const entityId = this._entities?.charge_current;
    if (!entityId || !this._hass) {
      return;
    }
    const current = Number(this._stateFor("charge_current")?.state);
    if (Number.isFinite(current) && current === value) {
      return;
    }
    const domain = entityId.split(".")[0];
    const serviceDomain = domain === "input_number" ? "input_number" : "number";
    try {
      await this._hass.callService(serviceDomain, "set_value", {
        entity_id: entityId,
        value,
      });
    } catch (err) {
      this._inlineEditing = false;
      this._update();
      if (this._inlineRangeEl) {
        this._inlineRangeEl.title = err?.message || String(err);
      }
    }
  }

  _openPopup() {
    const entityId = this._entities?.charge_current;
    if (!entityId || !this._canControlCurrent()) {
      return;
    }
    if (this._config.popup === "native") {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", {
          detail: { entityId },
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    const state = this._stateFor("charge_current");
    if (!state) {
      return;
    }
    this._range = this._currentRange(state);
    const current = Number(state.state);
    this._draftCurrent = this._clamp(
      Number.isFinite(current) ? current : this._range.min,
      this._range.min,
      this._range.max,
    );
    this._dirty = false;
    this._renderPopup();
    if (!this._dialog?.open) {
      this._dialog?.showModal();
    }
    this._syncPopupValue();
    this._dialog?.querySelector(".range")?.focus();
  }

  _renderPopup() {
    const { min, max, step } = this._range;
    const variant = this._config.popup;
    const presets = CURRENT_PRESETS.filter(
      (value) => value >= min && value <= max,
    );
    const presetMarkup = presets
      .map(
        (value) =>
          `<button class="preset" type="button" data-value="${value}">${value} A</button>`,
      )
      .join("");
    const actions = `
      <div class="popup-actions">
        <button class="ghost" type="button" data-action="close">${this._t("cancel")}</button>
        <button class="primary" type="button" data-action="apply">${this._t("apply")}</button>
      </div>
      <div class="popup-error" hidden></div>
    `;
    const header = `
      <div class="popup-head">
        <div>
          <div class="popup-kicker">${this._t("adjust_current")}</div>
          <div class="popup-title" id="de-ev-popup-title">${this._t("charging_current")}</div>
        </div>
        <button class="icon-button" type="button" data-action="close" aria-label="${this._t("close")}">×</button>
      </div>
    `;
    if (variant === "stepper") {
      this._dialog.className = "popup center";
      this._dialog.innerHTML = `
        <div class="popup-card">
          ${header}
          <div class="stepper-row">
            <button class="round" type="button" data-action="step" data-step="-1" aria-label="-${step} A">−</button>
            <div class="current-big">
              <span class="current-number">${this._draftCurrent}</span>
              <span class="current-unit">A</span>
            </div>
            <button class="round" type="button" data-action="step" data-step="1" aria-label="+${step} A">+</button>
          </div>
          <div class="range-track"><span></span></div>
          <div class="range-labels"><span>${min} A</span><span>${max} A</span></div>
          <div class="presets">${presetMarkup}</div>
          ${actions}
        </div>
      `;
    } else {
      this._dialog.className = "popup center wide";
      this._dialog.innerHTML = `
        <div class="popup-card">
          ${header}
          <div class="current-big">
            <span class="current-number">${this._draftCurrent}</span>
            <span class="current-unit">A</span>
          </div>
          <div class="range-wrap">
            <input class="range" type="range" min="${min}" max="${max}" step="${step}" value="${this._draftCurrent}" aria-label="${this._t("charging_current")}">
            <div class="range-labels"><span>${min} A</span><span>${max} A</span></div>
          </div>
          <div class="presets">${presetMarkup}</div>
          ${actions}
        </div>
      `;
    }
    this._rangeEl = this._dialog.querySelector(".range");
    this._rangeFillEl = this._dialog.querySelector(".range-track span");
    this._currentNumberEl = this._dialog.querySelector(".current-number");
    this._dialog.querySelectorAll("[data-action='close']").forEach((button) => {
      button.addEventListener("click", () => this._dialog.close());
    });
    this._dialog
      .querySelector("[data-action='apply']")
      .addEventListener("click", () => this._applyCurrent());
    this._rangeEl?.addEventListener("input", () => {
      this._dirty = true;
      this._draftCurrent = Number(this._rangeEl.value);
      this._syncPopupValue();
    });
    this._dialog.querySelectorAll(".preset").forEach((button) => {
      button.addEventListener("click", () => {
        this._dirty = true;
        this._draftCurrent = Number(button.dataset.value);
        if (this._rangeEl) {
          this._rangeEl.value = String(this._draftCurrent);
        }
        this._syncPopupValue();
      });
    });
    this._dialog.querySelectorAll("[data-action='step']").forEach((button) => {
      button.addEventListener("click", () => {
        this._dirty = true;
        const delta = Number(button.dataset.step) * this._range.step;
        this._draftCurrent = this._clamp(
          this._draftCurrent + delta,
          this._range.min,
          this._range.max,
        );
        this._syncPopupValue();
      });
    });
  }

  _syncPopupValue() {
    if (!this._dialog?.open || this._draftCurrent === null) {
      return;
    }
    this._currentNumberEl.textContent = String(this._draftCurrent);
    if (this._rangeEl) {
      this._rangeEl.value = String(this._draftCurrent);
    }
    const percent =
      ((this._draftCurrent - this._range.min) /
        (this._range.max - this._range.min)) *
      100;
    this._dialog.style.setProperty("--fill", `${percent}%`);
    if (this._rangeFillEl) {
      this._rangeFillEl.style.width = `${percent}%`;
    }
    this._dialog.querySelectorAll(".preset").forEach((button) => {
      button.classList.toggle(
        "active",
        Number(button.dataset.value) === this._draftCurrent,
      );
    });
  }

  async _applyCurrent() {
    const entityId = this._entities?.charge_current;
    if (!entityId || this._draftCurrent === null || !this._dialog || !this._hass) {
      return;
    }
    const apply = this._dialog.querySelector("[data-action='apply']");
    const errorEl = this._dialog.querySelector(".popup-error");
    if (!apply || !errorEl) {
      return;
    }
    apply.disabled = true;
    errorEl.hidden = true;
    const domain = entityId.split(".")[0];
    const serviceDomain = domain === "input_number" ? "input_number" : "number";
    try {
      await this._hass.callService(serviceDomain, "set_value", {
        entity_id: entityId,
        value: this._draftCurrent,
      });
      this._dialog.close();
    } catch (err) {
      errorEl.textContent = err?.message || String(err);
      errorEl.hidden = false;
      apply.disabled = false;
    }
  }

  async _toggleSession() {
    const entityId = this._entities.charge_session;
    if (!entityId || !this._canControlSession() || this._pendingSession) {
      return;
    }
    const domain = entityId.split(".")[0];
    const serviceDomain = domain === "input_boolean" ? "input_boolean" : "switch";
    const service = this._sessionOn() ? "turn_off" : "turn_on";
    this._pendingSession = true;
    this._update();
    try {
      await this._hass.callService(serviceDomain, service, {
        entity_id: entityId,
      });
    } finally {
      this._pendingSession = false;
      this._update();
    }
  }

  _closePopup() {
    if (this._dialog?.open) {
      this._dialog.close();
    }
  }
}

function registerCard() {
  if (!customElements.get(CARD_TYPE)) {
    customElements.define(CARD_TYPE, DeEvChargerCard);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
    window.customCards.push({
      type: CARD_TYPE,
      name: CARD_NAME,
      description:
        "Charging status, power, session energy and current control for a Dé EV Charger.",
      preview: true,
      documentationURL: "https://github.com/Glawnn/ha.de-ev",
    });
  }
}

let attempts = 0;

function ensureCardRegistered() {
  registerCard();
  if (attempts++ < 500) {
    window.setTimeout(ensureCardRegistered, 10);
  }
}

ensureCardRegistered();
