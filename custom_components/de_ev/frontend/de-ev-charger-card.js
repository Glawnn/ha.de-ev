const CARD_TYPE = "de-ev-charger";

const DEFAULT_METRICS = ["power", "energy_session", "session_duration", "current"];
const DEFAULT_CONTROLS = ["start_stop", "current"];

const METRICS = {
  status: { icon: "mdi:ev-station", labelKey: "status" },
  power: { icon: "mdi:flash", labelKey: "power" },
  voltage: { icon: "mdi:sine-wave", labelKey: "voltage" },
  current: { icon: "mdi:current-ac", labelKey: "current" },
  temperature: { icon: "mdi:thermometer", labelKey: "temperature" },
  energy_session: { icon: "mdi:lightning-bolt", labelKey: "energy_session" },
  session_duration: {
    icon: "mdi:timer-outline",
    labelKey: "session_duration",
    duration: true,
  },
  max_current: { icon: "mdi:current-ac", labelKey: "max_current" },
  work_state: { icon: "mdi:cog-outline", labelKey: "work_state" },
  last_session_energy: {
    icon: "mdi:history",
    labelKey: "last_session_energy",
  },
};

const LABELS = {
  en: {
    title: "EV Charger",
    status: "Status",
    power: "Power",
    voltage: "Voltage",
    current: "Current",
    temperature: "Temperature",
    energy_session: "Session energy",
    session_duration: "Session duration",
    max_current: "Maximum current",
    work_state: "Work state",
    last_session_energy: "Last session energy",
    start: "Start charging",
    stop: "Stop charging",
    set_current: "Charging current",
    unavailable: "Unavailable",
    action_failed: "Action failed",
  },
  fr: {
    title: "Borne VE",
    status: "État",
    power: "Puissance",
    voltage: "Tension",
    current: "Courant",
    temperature: "Température",
    energy_session: "Énergie de session",
    session_duration: "Durée de session",
    max_current: "Courant maximum",
    work_state: "État de travail",
    last_session_energy: "Énergie dernière session",
    start: "Démarrer la charge",
    stop: "Arrêter la charge",
    set_current: "Courant de charge",
    unavailable: "Indisponible",
    action_failed: "Action impossible",
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
  }
  ha-card {
    overflow: hidden;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 16px 8px;
  }
  .header-icon {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    border-radius: 14px;
    color: var(--primary-color);
    background: color-mix(in srgb, var(--primary-color) 14%, transparent);
    flex: 0 0 auto;
  }
  .header-icon ha-icon {
    --mdc-icon-size: 26px;
  }
  .title-block {
    min-width: 0;
    flex: 1 1 auto;
  }
  .title {
    font-size: 1.05rem;
    font-weight: 600;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .subtitle {
    margin-top: 2px;
    color: var(--secondary-text-color);
    font-size: 0.8rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .status {
    flex: 0 0 auto;
    border-radius: 999px;
    padding: 4px 10px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    font-size: 0.78rem;
    font-weight: 600;
    white-space: nowrap;
  }
  .status[data-state="charging"] {
    color: var(--success-color, #43a047);
  }
  .status[data-state="fault"] {
    color: var(--error-color, #db4437);
  }
  .status[data-state="plugged_in"],
  .status[data-state="waiting"],
  .status[data-state="paused"] {
    color: var(--warning-color, #ff9800);
  }
  .status[data-state="charged"] {
    color: var(--info-color, #039be5);
  }
  .metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(112px, 1fr));
    gap: 8px;
    padding: 8px 16px 4px;
  }
  .metric {
    display: grid;
    grid-template-columns: auto 1fr;
    column-gap: 8px;
    align-items: center;
    min-width: 0;
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--secondary-background-color);
  }
  .metric ha-icon {
    grid-row: span 2;
    color: var(--secondary-text-color);
    --mdc-icon-size: 20px;
  }
  .metric-value {
    font-size: 1rem;
    font-weight: 600;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .metric-value.unavailable {
    color: var(--secondary-text-color);
    font-weight: 400;
  }
  .metric ha-icon.unavailable {
    opacity: 0.5;
  }
  .metric-label {
    color: var(--secondary-text-color);
    font-size: 0.72rem;
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .controls {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 8px 16px 16px;
  }
  .action {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    min-height: 42px;
    padding: 10px 14px;
    border: none;
    border-radius: 12px;
    background: var(--primary-color);
    color: var(--text-primary-color);
    font: inherit;
    font-weight: 600;
    cursor: pointer;
  }
  .action.is-on {
    background: var(--error-color, #db4437);
  }
  .action:disabled {
    cursor: not-allowed;
    opacity: 0.55;
  }
  .action ha-icon {
    --mdc-icon-size: 20px;
  }
  .slider {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .slider[hidden] {
    display: none;
  }
  .slider-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    color: var(--secondary-text-color);
    font-size: 0.78rem;
  }
  .slider-value {
    color: var(--primary-text-color);
    font-size: 0.9rem;
    font-weight: 600;
  }
  .slider input {
    width: 100%;
    accent-color: var(--primary-color);
    margin: 0;
  }
  .error {
    padding: 0 16px 16px;
    color: var(--error-color, #db4437);
    font-size: 0.8rem;
  }
  .error[hidden] {
    display: none;
  }
  .compact .header {
    padding: 12px 12px 6px;
  }
  .compact .metrics {
    padding: 6px 12px 2px;
  }
  .compact .controls {
    padding: 6px 12px 12px;
  }
  .compact .error {
    padding: 0 12px 12px;
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
    this._metricEls = new Map();
    this._startButton = null;
    this._slider = null;
    this._sliderValue = null;
    this._errorEl = null;
  }

  static getStubConfig(hass, entities) {
    const candidates = entities || [];
    const entity =
      candidates.find(
        (candidate) =>
          candidate.startsWith("sensor.") && candidate.endsWith("_status")
      ) || candidates.find((candidate) => candidate.startsWith("sensor."));
    return entity ? { entity } : {};
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid configuration");
    }
    const metrics = config.metrics ?? DEFAULT_METRICS;
    const controls = config.controls ?? DEFAULT_CONTROLS;
    const entities = config.entities || {};

    if (!config.device_id && !config.entity && !Object.keys(entities).length) {
      throw new Error(
        "Define device_id, entity, or an entities mapping for the charger"
      );
    }
    if (!Array.isArray(metrics)) {
      throw new Error("metrics must be a list");
    }
    if (!Array.isArray(controls)) {
      throw new Error("controls must be a list");
    }

    this._config = {
      device_id: config.device_id,
      entity: config.entity,
      title: config.title,
      subtitle: config.subtitle,
      icon: config.icon,
      entities,
      metrics: metrics.map((metric) =>
        typeof metric === "string" ? { key: metric } : { ...metric }
      ),
      controls: [...controls],
      show_header: config.show_header !== false,
      compact: config.compact === true,
    };
    this._built = false;
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
    const metrics = this._config?.metrics?.length || 0;
    const controls = this._config?.controls?.length || 0;
    return 2 + Math.ceil(metrics / 2) + controls;
  }

  _t(key) {
    const language = this._language();
    return (
      LABELS[language][key] ||
      LABELS.en[key] ||
      key
    );
  }

  _language() {
    const language = (this._hass?.language || "en").toLowerCase();
    return language.startsWith("fr") ? "fr" : "en";
  }

  _render() {
    if (!this._config) {
      return;
    }
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <ha-card class="${this._config.compact ? "compact" : ""}">
        <div class="header">
          <div class="header-icon"><ha-icon></ha-icon></div>
          <div class="title-block">
            <div class="title"></div>
            <div class="subtitle"></div>
          </div>
          <div class="status" hidden></div>
        </div>
        <div class="metrics"></div>
        <div class="controls"></div>
        <div class="error" hidden></div>
      </ha-card>
    `;

    this._els = {
      header: this.shadowRoot.querySelector(".header"),
      icon: this.shadowRoot.querySelector(".header-icon ha-icon"),
      title: this.shadowRoot.querySelector(".title"),
      subtitle: this.shadowRoot.querySelector(".subtitle"),
      status: this.shadowRoot.querySelector(".status"),
      metrics: this.shadowRoot.querySelector(".metrics"),
      controls: this.shadowRoot.querySelector(".controls"),
      error: this.shadowRoot.querySelector(".error"),
    };
    this._errorEl = this._els.error;

    this._buildMetrics();
    this._buildControls();
    this._built = true;
    this._update();
  }

  _buildMetrics() {
    this._els.metrics.innerHTML = "";
    this._metricEls.clear();

    for (const [index, metric] of this._config.metrics.entries()) {
      const definition = this._metricDefinition(metric, index);
      if (!definition) {
        continue;
      }
      const existing = this._metricEls.get(definition.key);
      if (existing) {
        existing.definition = definition;
        continue;
      }
      const element = document.createElement("div");
      element.className = "metric";
      element.innerHTML = `
        <ha-icon></ha-icon>
        <div class="metric-value"></div>
        <div class="metric-label"></div>
      `;
      this._els.metrics.appendChild(element);
      this._metricEls.set(definition.key, {
        definition,
        element,
        icon: element.querySelector("ha-icon"),
        value: element.querySelector(".metric-value"),
        label: element.querySelector(".metric-label"),
      });
    }

    this._els.metrics.hidden = this._metricEls.size === 0;
  }

  _metricDefinition(metric, index) {
    const base = METRICS[metric.key] || {};
    if (!metric.key && !metric.entity) {
      return null;
    }
    return {
      key: metric.key || `metric_${index}`,
      entity: metric.entity,
      icon: metric.icon || base.icon || "mdi:gauge",
      label: metric.label,
      labelKey: metric.labelKey || base.labelKey || metric.key,
      duration: metric.duration ?? base.duration ?? false,
    };
  }

  _buildControls() {
    this._els.controls.innerHTML = "";
    this._startButton = null;
    this._slider = null;
    this._sliderValue = null;

    for (const control of this._config.controls) {
      if (control === "start_stop") {
        this._buildStartStop();
      } else if (control === "current") {
        this._buildCurrentSlider();
      }
    }

    this._els.controls.hidden = this._els.controls.childElementCount === 0;
  }

  _buildStartStop() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "action";
    button.innerHTML = `<ha-icon></ha-icon><span></span>`;
    button.addEventListener("click", () => this._toggleCharging());
    this._els.controls.appendChild(button);
    this._startButton = button;
  }

  _buildCurrentSlider() {
    const wrapper = document.createElement("div");
    wrapper.className = "slider";
    wrapper.innerHTML = `
      <div class="slider-head">
        <span></span>
        <span class="slider-value"></span>
      </div>
      <input type="range" />
    `;
    const input = wrapper.querySelector("input");
    input.addEventListener("input", () => {
      this._sliderValue.textContent = `${input.value} A`;
    });
    input.addEventListener("change", () => this._setCurrent());
    this._els.controls.appendChild(wrapper);
    this._slider = input;
    this._sliderValue = wrapper.querySelector(".slider-value");
    wrapper.querySelector(".slider-head span").textContent =
      this._t("set_current");
  }

  _update() {
    if (!this._hass || !this._config) {
      return;
    }
    this._entities = this._resolveEntities();
    this._updateHeader();
    this._updateMetrics();
    this._updateControls();
  }

  _resolveEntities() {
    const resolved = { ...this._config.entities };
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
            domain === "de_ev" && identifier === this._config.device_id
        )
      );
      return device?.id || this._config.device_id;
    }
    return null;
  }

  _keyFromUniqueId(uniqueId) {
    if (!uniqueId) {
      return null;
    }
    const keys = Object.keys(METRICS).sort((a, b) => b.length - a.length);
    return keys.find((key) => uniqueId.endsWith(`_${key}`)) || null;
  }

  _stateFor(key) {
    const entityId = this._entities[key];
    return entityId ? this._hass.states[entityId] : undefined;
  }

  _deviceName() {
    const deviceId = this._resolveDeviceId();
    const device = deviceId ? this._hass.devices?.[deviceId] : undefined;
    return device?.name_by_user || device?.name || null;
  }

  _updateHeader() {
    this._els.title.textContent =
      this._config.title || this._deviceName() || this._t("title");
    this._els.icon.setAttribute(
      "icon",
      this._config.icon || this._stateFor("status")?.attributes?.icon || "mdi:ev-station"
    );

    const status = this._stateFor("status");
    if (!status) {
      this._els.status.hidden = true;
    } else {
      this._els.status.hidden = false;
      this._els.status.textContent = this._statusLabel(status);
      this._els.status.dataset.state = status.state;
    }

    this._els.subtitle.textContent = this._config.subtitle || "";
    this._els.subtitle.hidden = !this._els.subtitle.textContent;
  }

  _statusLabel(stateObject) {
    if (this._hass.formatEntityState) {
      return this._hass.formatEntityState(stateObject);
    }
    const language = this._language();
    return (
      STATUS_LABELS[language][stateObject.state] ||
      STATUS_LABELS.en[stateObject.state] ||
      stateObject.state
    );
  }

  _updateMetrics() {
    for (const [key, elements] of this._metricEls) {
      const definition = elements.definition;
      const stateObject = definition.entity
        ? this._hass.states[definition.entity]
        : this._stateFor(key);

      elements.label.textContent =
        definition.label || this._t(definition.labelKey) || "";
      elements.icon.setAttribute(
        "icon",
        stateObject?.attributes?.icon || definition.icon
      );

      if (!stateObject) {
        elements.value.textContent = "—";
        elements.value.classList.add("unavailable");
        elements.icon.classList.add("unavailable");
        continue;
      }

      const unavailable =
        stateObject.state === "unavailable" || stateObject.state === "unknown";
      elements.value.textContent = definition.duration
        ? this._formatDuration(stateObject)
        : this._formatState(stateObject);
      elements.value.classList.toggle("unavailable", unavailable);
      elements.icon.classList.toggle("unavailable", unavailable);
    }
  }

  _formatState(stateObject) {
    if (this._hass.formatEntityState) {
      return this._hass.formatEntityState(stateObject);
    }
    const unit = stateObject.attributes.unit_of_measurement;
    return unit ? `${stateObject.state} ${unit}` : stateObject.state;
  }

  _formatDuration(stateObject) {
    const seconds = Number(stateObject.state);
    if (!Number.isFinite(seconds)) {
      return this._formatState(stateObject);
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remaining = Math.round(seconds % 60);
    if (hours > 0) {
      return `${hours} h ${String(minutes).padStart(2, "0")}`;
    }
    if (minutes > 0) {
      return `${minutes} min ${String(remaining).padStart(2, "0")} s`;
    }
    return `${remaining} s`;
  }

  _updateControls() {
    if (this._startButton) {
      const stateObject = this._stateFor("charge_session");
      const unavailable =
        !stateObject ||
        stateObject.state === "unavailable" ||
        stateObject.state === "unknown";
      const isOn = stateObject?.state === "on";

      this._startButton.disabled = unavailable;
      this._startButton.classList.toggle("is-on", isOn);
      this._startButton.querySelector("ha-icon").setAttribute(
        "icon",
        isOn ? "mdi:stop" : "mdi:play"
      );
      this._startButton.querySelector("span").textContent = this._t(
        isOn ? "stop" : "start"
      );
      this._startButton.hidden = !stateObject;
    }

    if (this._slider) {
      const stateObject = this._stateFor("charge_current");
      const wrapper = this._slider.closest(".slider");
      if (!stateObject) {
        wrapper.hidden = true;
      } else {
        const attributes = stateObject.attributes || {};
        const value = Number(stateObject.state);
        this._slider.min = attributes.min ?? 6;
        this._slider.max = attributes.max ?? 32;
        this._slider.step = attributes.step ?? 1;
        this._slider.disabled =
          stateObject.state === "unavailable" ||
          stateObject.state === "unknown";

        if (this.shadowRoot.activeElement !== this._slider) {
          this._slider.value = Number.isFinite(value)
            ? value
            : this._slider.min;
        }
        this._sliderValue.textContent = `${this._slider.value} A`;
        wrapper.hidden = false;
      }
    }

    this._els.controls.hidden = !this._els.controls.querySelector(
      ":scope > :not([hidden])"
    );
  }

  async _toggleCharging() {
    const stateObject = this._stateFor("charge_session");
    const entityId = this._entities.charge_session;
    if (!stateObject || !entityId) {
      return;
    }
    this._startButton.disabled = true;
    try {
      await this._hass.callService(
        "switch",
        stateObject.state === "on" ? "turn_off" : "turn_on",
        { entity_id: entityId }
      );
      this._startButton.disabled = false;
      this._showError(null);
    } catch (error) {
      console.error("de-ev-charger-card: switch action failed", error);
      this._showError(this._t("action_failed"));
      this._startButton.disabled = false;
    }
  }

  async _setCurrent() {
    const entityId = this._entities.charge_current;
    if (!entityId) {
      return;
    }
    const value = Number(this._slider.value);
    this._slider.disabled = true;
    try {
      await this._hass.callService("number", "set_value", {
        entity_id: entityId,
        value,
      });
      this._slider.disabled = false;
      this._showError(null);
    } catch (error) {
      console.error("de-ev-charger-card: current action failed", error);
      this._showError(this._t("action_failed"));
      this._slider.disabled = false;
    }
  }

  _showError(message) {
    if (!this._errorEl) {
      return;
    }
    this._errorEl.textContent = message || "";
    this._errorEl.hidden = !message;
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, DeEvChargerCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: "Dé EV Charger",
    description: "Status and controls for a Dé EV Charger.",
    preview: true,
  });
}
