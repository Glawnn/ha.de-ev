# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.4.0](https://github.com/Glawnn/ha.de-ev/compare/v0.3.1...v0.4.0) (2026-10-27)


### Features

* find the charger again after an IP change ([2624aeb](https://github.com/Glawnn/ha.de-ev/commit/2624aeb54844f1f5ba23b87fe4526a97d5016632))
* find the charger again after an IP change ([9f067f5](https://github.com/Glawnn/ha.de-ev/commit/9f067f577c324bdab37c1c2cadb42b5e0e0fc834))


### Bug Fixes

* also find the charger again when setup fails after an IP change ([6bef82f](https://github.com/Glawnn/ha.de-ev/commit/6bef82fc37dbf995a5aa66cba20a7423eedc06cc))
* also find the charger again when setup fails after an IP change ([d2a9cb0](https://github.com/Glawnn/ha.de-ev/commit/d2a9cb0e4c865eb5403441469360f1a4a378b91e))
* **charger:** use renamed _ensure_device_locked in _write ([9579f34](https://github.com/Glawnn/ha.de-ev/commit/9579f3483eacca572d222da457a2d4ce50b1867a))
* **charger:** use renamed _ensure_device_locked in _write ([f19f580](https://github.com/Glawnn/ha.de-ev/commit/f19f580c5a35e6b6461a0dafb83bdfa254ec2ee0))

## [0.3.1](https://github.com/Glawnn/ha.de-ev/compare/v0.3.0...v0.3.1) (2026-10-26)


### Bug Fixes

* reconnect charger after network loss and register card reliably ([7c8de7f](https://github.com/Glawnn/ha.de-ev/commit/7c8de7fe3198d29085aca8409f246fad5abe4c2e))
* reconnexion borne après coupure réseau et enregistrement carte fiable ([2175757](https://github.com/Glawnn/ha.de-ev/commit/217575769db6658f556be7b2aba090ef3932926c))

## [0.3.0](https://github.com/Glawnn/ha.de-ev/compare/v0.2.0...v0.3.0) (2026-10-25)


### Features

* add dedicated charger card ([#6](https://github.com/Glawnn/ha.de-ev/issues/6)) ([21daf28](https://github.com/Glawnn/ha.de-ev/commit/21daf28aef5f8a806940034e05df14f7df7e4442))


### Bug Fixes

* **config-flow:** refresh the local key from Tuya Cloud ([#8](https://github.com/Glawnn/ha.de-ev/issues/8)) ([b7546b2](https://github.com/Glawnn/ha.de-ev/commit/b7546b20cca0ff54b627b06d45519035e3685c40))

## [0.2.0] - 2026-10-23

### Added

- Cloud-assisted setup through a Tuya IoT project, with automatic charger
  discovery and local key retrieval.
- Fully local setup with IP address, Device ID and local key.
- Automatic Tuya protocol detection (`3.5`, `3.4`, `3.3`).
- Local control: charging session switch and charging current setpoint.
- Sensors for status, power, voltage, current, temperature, session energy,
  session duration, maximum current, work state and last session energy.
- Binary sensors for charging, vehicle plugged and fault.
- Energy dashboard support through a `total_increasing` session energy sensor.
- Options for polling interval and current limits.
- Reauthentication and reconfiguration flows.
- English and French translations.
