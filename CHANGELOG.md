# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0](https://github.com/Glawnn/ha.de-ev/compare/v0.2.0...v0.3.0) (2026-10-23)


### Features

* add dedicated charger card ([#6](https://github.com/Glawnn/ha.de-ev/issues/6)) ([21daf28](https://github.com/Glawnn/ha.de-ev/commit/21daf28aef5f8a806940034e05df14f7df7e4442))

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
