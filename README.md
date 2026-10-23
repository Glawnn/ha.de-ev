# Dé EV Charger

Home Assistant integration for the **Dé Pow EV Charger**, a Tuya-based 3.5 kW
EV charger. Tuya Cloud is used only for the initial setup; day-to-day control
and monitoring happen entirely on your local network.

[![GitHub release](https://img.shields.io/github/v/release/Glawnn/ha.de-ev?style=for-the-badge)](https://github.com/Glawnn/ha.de-ev/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Glawnn/ha.de-ev/ci.yml?branch=main&style=for-the-badge)](https://github.com/Glawnn/ha.de-ev/actions/workflows/ci.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/Glawnn/ha.de-ev/validate.yml?branch=main&style=for-the-badge)](https://github.com/Glawnn/ha.de-ev/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/Glawnn/ha.de-ev?style=for-the-badge)](LICENSE)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.10%2B-blue?style=for-the-badge)](https://www.home-assistant.io/)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Glawnn&repository=ha.de-ev&category=integration)
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=de_ev)

## Overview

This custom integration turns a Dé Pow EV Charger into a native Home Assistant
device:

- one-time cloud-assisted discovery to retrieve the charger identity and local
  key;
- permanent local control over the Tuya LAN protocol (port `6668`);
- charging session control, current setpoint, live measurements and session
  energy;
- compatibility with the Home Assistant Energy dashboard.

The integration never sends charging commands through Tuya Cloud. If the cloud
is unavailable after setup, local control keeps working.

## Features

- Start and stop charging from Home Assistant.
- Set the charging current from **6 A to 16 A** in 1 A steps, bounded by the
  charger hardware maximum.
- Live sensors: status, power, voltage, current and temperature.
- Session sensors: session energy, session duration and last session energy.
- Binary sensors: charging, vehicle plugged and fault.
- Config flow with cloud discovery or fully local configuration.
- Automatic Tuya protocol detection (`3.5`, then `3.4` and `3.3`).
- Reauthentication when the local key changes and reconfiguration of the IP
  address.
- Diagnostics support with secrets redacted.

## Supported hardware

| Item | Value |
|---|---|
| Charger | Dé Pow EV Charger |
| Rated power | 3.5 kW |
| Validated firmware | `1.9.7` |
| Tuya profile | `depow_v2` |
| Local protocol | `3.5` (fallback `3.4` / `3.3`) |
| Local port | `6668` |

Other Tuya EV chargers may work, but their data-point mapping is not guaranteed.
If your model is not detected, open an issue with the model name and the
available data points.

## Requirements

- Home Assistant **2026.10** or newer.
- The charger and Home Assistant on the same local network.
- A Tuya / Smart Life account with the charger already paired.
- A Tuya IoT Cloud project linked to that account (cloud setup), **or** the
  charger IP, Device ID and local key (local setup).
- Only one local TCP client can talk to the charger at a time. Close the Smart
  Life or Tuya mobile app while the integration is connected.

## Installation

### HACS / Marketplace

1. Open **HACS → Integrations** (or **Settings → Marketplace** on Home
   Assistant 2026.11 and newer).
2. Open the menu and choose **Custom repositories**.
3. Add `https://github.com/Glawnn/ha.de-ev` with category **Integration**.
4. Install **Dé EV Charger**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration** and search for
   **Dé EV Charger**.

You can also use the button above to add the repository directly if My Home
Assistant is configured.

### Manual installation

1. Copy `custom_components/de_ev` to `/config/custom_components/de_ev`.
2. Restart Home Assistant.
3. Add the integration from **Settings → Devices & services**.

The integration requires `tinytuya>=1.20.0`; Home Assistant installs it
automatically when the integration is loaded.

## Configuration

### Option 1 — Tuya Cloud (recommended)

The cloud is used once to list your chargers and retrieve their local keys. The
integration then switches to local communication.

1. Create an account on [Tuya IoT Platform](https://iot.tuya.com/).
2. Create a **Cloud project** and note its **Access ID / Client ID** and
   **Access Secret / Client Secret**.
3. Link your Smart Life account to the project (**Devices → Link Tuya App
   Account**).
4. In Home Assistant, add **Dé EV Charger** and choose **Tuya Cloud**.
5. Select the data center region, then enter the Access ID and Access Secret.
6. Pick your charger from the list.

If the charger LAN IP cannot be discovered automatically, Home Assistant asks
for it. You can find it in your router's device list or in the Smart Life app.

The integration tests the local connection and detects the Tuya protocol before
creating the entry. This can take up to 30 seconds.

### Option 2 — Local connection

Choose **Local connection** and provide:

| Field | Description |
|---|---|
| Name | Name shown in Home Assistant |
| IP address | Local IP address of the charger |
| Device ID | Tuya device ID |
| Local key | 16-character Tuya local key |
| Protocol version | `Auto` tries `3.5`, `3.4` and `3.3` |
| Area | Optional Home Assistant area |

The local key changes when the charger is re-paired with the mobile app. If the
key is rejected later, Home Assistant starts a reauthentication flow.

### Options

After setup, open the integration options to adjust:

- **Polling interval** — 10 to 300 seconds, default 30.
- **Minimum current** — default 6 A.
- **Maximum current** — default 16 A.

The effective current range is also limited by the charger hardware maximum.

## Entities

Entity IDs depend on the device name and can be renamed in Home Assistant. The
following entities are created:

### Controls

| Entity | Type | Description |
|---|---|---|
| Charging session | `switch` | Start or stop a charging session |
| Charging current | `number` | Current setpoint in A, 6–16 A |

### Sensors

| Entity | Unit | Description |
|---|---|---|
| Status | — | Charger state (available, plugged in, charging, fault, etc.) |
| Power | W | Instantaneous charging power |
| Voltage | V | Supply voltage |
| Current | A | Instantaneous charging current |
| Temperature | °C | Charger temperature |
| Session energy | kWh | Energy delivered during the current session |
| Session duration | s | Current session duration |
| Maximum current | A | Charger hardware maximum |
| Work state | — | Raw charger work state |
| Last session energy | kWh | Energy of the previous session |

### Binary sensors

| Entity | Description |
|---|---|
| Charging | A charging session is active |
| Vehicle plugged | A vehicle is connected |
| Fault | The charger reports a fault |

## Dashboard card

The integration bundles a Lovelace card showing the charger status,
instantaneous power, session energy and duration, the current setpoint, and
start/stop controls. After restarting Home Assistant, add it with:

```yaml
type: custom:de-ev-charger
device_id: <charger-device-id>
title: Garage
```

Alternatively, point to any entity belonging to the charger:

```yaml
type: custom:de-ev-charger
entity: sensor.garage_status
```

The card finds the other charger entities automatically from the device
registry, and explicit `entities:` overrides are optional for custom or test
setups. Tapping the current value opens the current adjustment dialog. The
`popup` option selects its style:

| Value | Description |
|---|---|
| `centered` | Centered dialog with slider and presets (default) |
| `stepper` | Centered dialog with `-` / `+` buttons |
| `native` | Home Assistant's standard more-info dialog |

```yaml
type: custom:de-ev-charger
entity: sensor.garage_status
popup: centered
```

Set `current_control: slider` to place the current slider directly in the card
instead of opening a dialog. The slider range follows the charger's `min`, `max`
and `step` attributes.

For a virtual or test setup, point the controls to input helpers:

```yaml
type: custom:de-ev-charger
title: Test charger
entities:
  status: sensor.demo_charger_status
  power: sensor.demo_charger_power
  energy_session: sensor.demo_charger_energy_session
  session_duration: sensor.demo_charger_session_duration
  charge_current: input_number.demo_charger_current
  charge_session: input_boolean.demo_charger_session
```

The card uses the Home Assistant language for its labels (French and English are
bundled). The card also includes a visual editor in the Lovelace UI for the
basic configuration fields.

## Energy dashboard

The **Session energy** sensor uses the Home Assistant `energy` device class with
`total_increasing` state class, so it can be added to the Energy dashboard:

1. Open **Settings → Dashboards → Energy**.
2. Under **Individual devices**, choose **Add device**.
3. Select the charger's **Session energy** sensor.

The sensor resets at the start of each charging session. Home Assistant treats
the drop as a new metering cycle and keeps long-term statistics.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Port 6668 is already used` | Smart Life or Tuya app is connected | Close the mobile app, then retry |
| `The charger rejected the local key` | Charger was re-paired or key is wrong | Re-run the integration, or enter the current key |
| `Cannot reach the charger` | Wrong IP, charger offline, or different network | Check the IP and that the charger is powered |
| Setup times out | Protocol mismatch or blocked port | Try protocol `3.4` or `3.3`; check your firewall |
| Charger not found in cloud | Smart Life account not linked to the Tuya project | Link the account in the Tuya IoT Platform |
| Values look wrong | Unsupported model/profile | Open an issue with the model and data points |

Diagnostics are available from the integration page and redact the Access
Secret, local key and other sensitive values.

## Safety

- Do not change the current setpoint above what your electrical installation,
  breaker and cable can safely handle.
- A 16 A setpoint requires a dedicated, correctly sized circuit. When in doubt,
  keep the limit lower or consult a qualified electrician.
- This integration does not replace the charger's built-in protections or your
  home's circuit breakers.
- Do not expose the charger directly to the Internet.

## Support

- [Report an issue or request a feature](https://github.com/Glawnn/ha.de-ev/issues)
- [Technical specification](docs.md)

When reporting a problem, include:

- the integration version and Home Assistant version;
- the charger model and firmware;
- relevant Home Assistant logs with debug logging enabled;
- diagnostics from the integration page.

## Development

Developer setup, tests, the reusable Home Assistant sandbox and the release
process are documented in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Disclaimer

This is an unofficial community integration. It is not affiliated with, endorsed
by or supported by Dé, Tuya or Home Assistant. Use it at your own risk,
especially when controlling high-current electrical equipment.
