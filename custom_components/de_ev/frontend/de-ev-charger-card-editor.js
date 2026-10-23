const CARD_TYPE = "de-ev-charger";

const POPUP_VARIANTS = ["centered", "stepper", "native"];
const CURRENT_CONTROLS = ["popup", "slider"];

const LABELS = {
  en: {
    editorTitle: "Dé EV Charger card",
    title: "Title",
    entity: "Entity",
    deviceId: "Device ID",
    popup: "Popup style",
    popupCentered: "Centered dialog (default)",
    popupStepper: "Stepper dialog",
    popupNative: "Home Assistant dialog",
    currentControl: "Current control",
    currentControlPopup: "Popup dialog",
    currentControlSlider: "Inline slider",
    status: "Status sensor",
    power: "Power sensor",
    energy: "Session energy sensor",
    duration: "Session duration sensor",
    chargeCurrent: "Charging current input",
    chargeSession: "Charging session input",
  },
  fr: {
    editorTitle: "Carte Borne VE Dé",
    title: "Titre",
    entity: "Entité",
    deviceId: "ID de l'appareil",
    popup: "Style de popup",
    popupCentered: "Dialogue centré (par défaut)",
    popupStepper: "Dialogue avec étape",
    popupNative: "Dialogue Home Assistant",
    currentControl: "Contrôle du courant",
    currentControlPopup: "Dialogue popup",
    currentControlSlider: "Curseur intégré",
    status: "Capteur de statut",
    power: "Capteur de puissance",
    energy: "Capteur d'énergie de session",
    duration: "Capteur de durée de session",
    chargeCurrent: "Entrée courant de charge",
    chargeSession: "Entrée session de charge",
  },
};

class DeEvChargerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = config || {};
  }

  _language() {
    return (this._hass?.language || "en").toLowerCase().startsWith("fr")
      ? "fr"
      : "en";
  }

  _t(key) {
    return LABELS[this._language()][key] || LABELS.en[key] || key;
  }

  _entities() {
    return Object.keys(this._hass.states || {}).sort();
  }

  _entitiesForMetric(metric) {
    const entities = this._entities();
    return entities.filter((e) => e.startsWith("sensor.") || e.startsWith("input_") || e.startsWith("switch."));
  }

  connectedCallback() {
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot) {
      this._render();
    }
  }

  _render() {
    const lang = this._language();
    const entities = this._entities();
    const entitiesMetrics = this._entitiesForMetric();

    const selectedPopup = this._config.popup || "centered";
    const selectedCurrentControl = this._config.current_control || "popup";

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; padding: 16px; font-family: system-ui, -apple-system, sans-serif; }
        ha-formfield { display: block; margin-bottom: 16px; }
        ha-select, ha-textfield, ha-entity-picker { width: 100%; display: block; }
        .section { margin-bottom: 24px; }
        .section-title { font-size: 1rem; font-weight: 600; margin-bottom: 12px; color: var(--primary-text-color); }
        .hint { font-size: 0.8rem; color: var(--secondary-text-color); margin-top: 4px; }
      </style>
      <div>
        <div class="section-title">${this._t("editorTitle")}</div>

        <div class="section">
          <div class="section-title">${this._t("title")}</div>
          <ha-textfield
            .label="${this._t("title")}"
            .value="${this._config.title || ""}"
            @input="${(ev) => this._set("title", ev.target.value)}"
          ></ha-textfield>
        </div>

        <div class="section">
          <div class="section-title">${this._t("deviceId")}</div>
          <ha-textfield
            .label="${this._t("deviceId")}"
            .value="${this._config.device_id || ""}"
            @input="${(ev) => this._set("device_id", ev.target.value)}"
          ></ha-textfield>
          <div class="hint">Laissez vide pour utiliser une entité.</div>
        </div>

        <div class="section">
          <div class="section-title">${this._t("entity")}</div>
          <ha-entity-picker
            .hass="${this._hass}"
            .value="${this._config.entity || ""}"
            .includeDomains="${["sensor", "input_boolean", "input_number", "switch"]}"
            @change="${(ev) => this._set("entity", ev.detail.value)}"
          ></ha-entity-picker>
        </div>

        <div class="section">
          <div class="section-title">${this._t("popup")}</div>
          <ha-select
            .label="${this._t("popup")}"
            .value="${selectedPopup}"
            @selected="${(ev) => this._set("popup", ev.target.value)}"
          >
            ${POPUP_VARIANTS.map((v) => `<md-list-item value="${v}" graphic="avatar"><span>${this._t(`popup${v.charAt(0).toUpperCase() + v.slice(1)}`)}</span></md-list-item>`).join("")}
          </ha-select>
        </div>

        <div class="section">
          <div class="section-title">${this._t("currentControl")}</div>
          <ha-select
            .label="${this._t("currentControl")}"
            .value="${selectedCurrentControl}"
            @selected="${(ev) => this._set("current_control", ev.target.value)}"
          >
            ${CURRENT_CONTROLS.map((v) => `<md-list-item value="${v}" graphic="avatar"><span>${this._t(`currentControl${v.charAt(0).toUpperCase() + v.slice(1)}`)}</span></md-list-item>`).join("")}
          </ha-select>
        </div>

        <div class="section">
          <div class="section-title">Entités (mapping)</div>
          ${[
            { key: "status", label: this._t("status"), domains: ["sensor"] },
            { key: "power", label: this._t("power"), domains: ["sensor"] },
            { key: "energy_session", label: this._t("energy"), domains: ["sensor"] },
            { key: "session_duration", label: this._t("duration"), domains: ["sensor"] },
            { key: "charge_current", label: this._t("chargeCurrent"), domains: ["input_number", "number"] },
            { key: "charge_session", label: this._t("chargeSession"), domains: ["input_boolean", "switch"] },
          ].map((item) => {
            const val = (this._config.entities && this._config.entities[item.key]) || "";
            return `
              <ha-formfield>
                <ha-entity-picker
                  .hass="${this._hass}"
                  .label="${item.label}"
                  .value="${val}"
                  .includeDomains="${JSON.stringify(item.domains)}"
                  @change="${(ev) => this._setEntity(item.key, ev.detail.value)}"
                ></ha-entity-picker>
              </ha-formfield>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  _set(key, value) {
    const config = { ...this._config };
    if (value === "") delete config[key];
    else config[key] = value;
    this._config = config;
    this._fireConfigChanged();
  }

  _setEntity(key, value) {
    const config = { ...this._config };
    const entities = { ...(config.entities || {}) };
    if (value === "") {
      delete entities[key];
      if (Object.keys(entities).length === 0) delete config.entities;
    } else {
      entities[key] = value;
      config.entities = entities;
    }
    this._config = config;
    this._fireConfigChanged();
  }

  _fireConfigChanged() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

customElements.define("de-ev-charger-card-editor", DeEvChargerCardEditor);
