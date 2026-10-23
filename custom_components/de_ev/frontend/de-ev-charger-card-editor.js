const POPUP_VARIANTS = ["centered", "stepper", "native"];
const CURRENT_CONTROLS = ["popup", "slider"];

const LABELS = {
  en: {
    editorTitle: "Dé EV Charger card",
    title: "Title",
    entity: "Entity",
    deviceId: "Device ID",
    deviceIdHint: "Leave empty when selecting an entity.",
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
    entityMapping: "Entity mapping",
  },
  fr: {
    editorTitle: "Carte Borne VE Dé",
    title: "Titre",
    entity: "Entité",
    deviceId: "ID de l'appareil",
    deviceIdHint: "Laissez vide si vous sélectionnez une entité.",
    popup: "Style de popup",
    popupCentered: "Dialogue centré (par défaut)",
    popupStepper: "Dialogue avec étapes",
    popupNative: "Dialogue Home Assistant",
    currentControl: "Contrôle du courant",
    currentControlPopup: "Dialogue popup",
    currentControlSlider: "Curseur intégré",
    status: "Capteur de statut",
    power: "Capteur de puissance",
    energy: "Capteur d'énergie de session",
    duration: "Capteur de durée de session",
    chargeCurrent: "Entrée du courant de charge",
    chargeSession: "Entrée de session de charge",
    entityMapping: "Association des entités",
  },
};

const ENTITY_FIELDS = [
  { key: "status", label: "status", domains: ["sensor"] },
  { key: "power", label: "power", domains: ["sensor"] },
  { key: "energy_session", label: "energy", domains: ["sensor"] },
  { key: "session_duration", label: "duration", domains: ["sensor"] },
  {
    key: "charge_current",
    label: "chargeCurrent",
    domains: ["input_number", "number"],
  },
  {
    key: "charge_session",
    label: "chargeSession",
    domains: ["input_boolean", "switch"],
  },
];

class DeEvChargerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _language() {
    return (this._hass?.language || "en").toLowerCase().startsWith("fr")
      ? "fr"
      : "en";
  }

  _t(key) {
    return LABELS[this._language()][key] || LABELS.en[key] || key;
  }

  _section(title) {
    const section = document.createElement("section");
    section.className = "section";
    const heading = document.createElement("div");
    heading.className = "section-title";
    heading.textContent = title;
    section.append(heading);
    return section;
  }

  _textField(key, label, value, hint) {
    const section = this._section(label);
    const field = document.createElement("ha-textfield");
    field.label = label;
    field.value = value || "";
    field.addEventListener("input", (event) => {
      this._set(key, event.target.value);
    });
    section.append(field);
    if (hint) {
      const helper = document.createElement("div");
      helper.className = "hint";
      helper.textContent = hint;
      section.append(helper);
    }
    return section;
  }

  _entityField(label, value, domains, onChange) {
    const section = this._section(label);
    const picker = document.createElement("ha-entity-picker");
    picker.hass = this._hass;
    picker.label = label;
    picker.value = value || "";
    picker.includeDomains = domains;
    const update = (event) => onChange(event.detail?.value ?? picker.value ?? "");
    picker.addEventListener("value-changed", update);
    picker.addEventListener("change", update);
    section.append(picker);
    return section;
  }

  _selectField(configKey, label, values, translationPrefix = configKey) {
    const section = this._section(label);
    const select = document.createElement("select");
    select.setAttribute("aria-label", label);
    for (const value of values) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = this._t(
        `${translationPrefix}${value.charAt(0).toUpperCase()}${value.slice(1)}`,
      );
      select.append(option);
    }
    select.value = this._config[configKey] || values[0];
    select.addEventListener("change", () =>
      this._set(configKey, select.value),
    );
    section.append(select);
    return section;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
          color: var(--primary-text-color);
          font-family: system-ui, -apple-system, sans-serif;
        }
        .section { margin-bottom: 20px; }
        .section-title {
          margin-bottom: 10px;
          font-size: .95rem;
          font-weight: 600;
        }
        ha-textfield, ha-entity-picker, select { display: block; width: 100%; }
        select {
          min-height: 48px;
          padding: 0 12px;
          border: 1px solid var(--outline-color, var(--divider-color));
          border-radius: 8px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }
        .hint {
          margin-top: 6px;
          color: var(--secondary-text-color);
          font-size: .8rem;
        }
      </style>
    `;

    const content = document.createElement("div");
    const heading = document.createElement("div");
    heading.className = "section-title";
    heading.textContent = this._t("editorTitle");
    content.append(heading);

    content.append(
      this._textField("title", this._t("title"), this._config.title),
      this._textField(
        "device_id",
        this._t("deviceId"),
        this._config.device_id,
        this._t("deviceIdHint"),
      ),
      this._entityField(
        this._t("entity"),
        this._config.entity,
        ["sensor", "input_boolean", "input_number", "switch"],
        (value) => this._set("entity", value),
      ),
      this._selectField("popup", this._t("popup"), POPUP_VARIANTS),
      this._selectField(
        "current_control",
        this._t("currentControl"),
        CURRENT_CONTROLS,
        "currentControl",
      ),
    );

    const mapping = this._section(this._t("entityMapping"));
    for (const field of ENTITY_FIELDS) {
      const value = this._config.entities?.[field.key] || "";
      mapping.append(
        this._entityField(this._t(field.label), value, field.domains, (entity) =>
          this._setEntity(field.key, entity),
        ),
      );
    }
    content.append(mapping);
    this.shadowRoot.append(content);
  }

  _set(key, value) {
    const config = { ...this._config };
    if (value === "") delete config[key];
    else config[key] = value;
    this._config = config;
    this._fireConfigChanged();
  }

  _setEntity(key, value) {
    const previous = this._config.entities?.[key] || "";
    if (previous === value) {
      return;
    }
    const config = { ...this._config };
    const entities = { ...(config.entities || {}) };
    if (value === "") {
      delete entities[key];
      if (Object.keys(entities).length === 0) delete config.entities;
      else config.entities = entities;
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
      }),
    );
  }
}

customElements.define("de-ev-charger-card-editor", DeEvChargerCardEditor);
