"""Decode Tuya data points for supported EV charger profiles."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

DEPOW_STATUS: dict[str, tuple[str, str]] = {
    "SLEEP": ("sleep", "Sleeping"),
    "IDLE": ("idle", "Available"),
    "IDLEINS": ("plugged_in", "Vehicle detected"),
    "WORKING": ("charging", "Charging"),
    "WAIT": ("waiting", "Waiting"),
    "ERRORPAUSE": ("fault", "Fault"),
    "PAUSE": ("paused", "Paused"),
    "STOP": ("charged", "Charge complete"),
}

QCCDZ_STATUS: dict[str, tuple[str, str]] = {
    "not_plugged_in": ("idle", "Available"),
    "plugged_in_no_demand": ("plugged_in", "Vehicle detected"),
    "plugged_in_demand": ("waiting", "Waiting"),
    "plugged_in_charging": ("charging", "Charging"),
    "session_ending": ("charged", "Charge complete"),
    "fault": ("fault", "Fault"),
}

PILOT_STATUS: dict[str, str] = {
    "stop": "not_plugged_in",
    "charging": "plugged_in_charging",
    "charged": "session_ending",
    "waiting": "plugged_in_demand",
    "paused": "plugged_in_no_demand",
    "error": "fault",
}

PLUGGED_STATES = {"plugged_in", "waiting", "charging", "paused", "charged", "fault"}

STATUS_OPTIONS = [
    "unknown",
    "sleep",
    "idle",
    "plugged_in",
    "charging",
    "waiting",
    "fault",
    "paused",
    "charged",
]


@dataclass(slots=True)
class Snapshot:
    """Decoded charger state."""

    profile: str
    status: str
    status_label: str
    charging: bool
    plugged: bool
    power_w: float
    voltage_v: float
    current_a: float
    energy_kwh: float | None
    current_target_a: int | None
    max_current_a: int
    do_charge: bool | None
    temperature_c: float | None
    session_duration_s: int | None
    work_state: int | None
    nfc_enabled: bool | None
    product_variant: int | None
    schedule: dict[str, Any] | None
    last_session: dict[str, Any] | None
    charger_info: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Return the snapshot as a dictionary."""
        return asdict(self)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return round(number) if number is not None else None


def _bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "on", "yes"}:
            return True
        if lowered in {"false", "0", "off", "no"}:
            return False
    return None


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def current_shortcuts(dps: dict[str, Any]) -> list[int]:
    """Return the current values advertised by the Tuya app."""
    raw = dps.get("107")
    if raw is None:
        return []
    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return []
    if not isinstance(values, list):
        return []
    result: set[int] = set()
    for value in values:
        number = _integer(value)
        if number is not None and 6 <= number <= 32:
            result.add(number)
    return sorted(result)


def _last_session(raw: Any) -> dict[str, Any] | None:
    data = _json_object(raw)
    if not data:
        return None
    energy = _number(data.get("c"))
    duration = _integer(data.get("d"))
    return {
        "started_at": data.get("t"),
        "start": data.get("s"),
        "end": data.get("e"),
        "duration_s": duration,
        "energy_kwh": round(energy / 10.0, 2) if energy is not None else None,
    }


def _schedule(raw: Any) -> dict[str, Any] | None:
    data = _json_object(raw)
    if not data:
        return None
    mode = _integer(data.get("m"))
    return {
        "enabled": mode == 2,
        "mode": mode,
        "start": data.get("ss"),
        "end": data.get("se"),
    }


def detect_profile(dps: dict[str, Any]) -> str:
    """Detect the charger profile from its data points."""
    if "102" in dps:
        return "depow_v2"
    if any(key in dps for key in ("25", "35", "38", "48")):
        return "qccdz_v1"
    return "unknown"


def _empty(profile: str, label: str, max_current: int) -> Snapshot:
    return Snapshot(
        profile=profile,
        status="unknown",
        status_label=label,
        charging=False,
        plugged=False,
        power_w=0.0,
        voltage_v=0.0,
        current_a=0.0,
        energy_kwh=None,
        current_target_a=None,
        max_current_a=max_current,
        do_charge=None,
        temperature_c=None,
        session_duration_s=None,
        work_state=None,
        nfc_enabled=None,
        product_variant=None,
        schedule=None,
        last_session=None,
        charger_info=None,
    )


def decode(dps: dict[str, Any], *, max_current: int = 16) -> Snapshot:
    """Decode raw data points into a snapshot."""
    profile = detect_profile(dps)
    if profile == "depow_v2":
        return _decode_depow(dps, max_current)
    if profile == "qccdz_v1":
        return _decode_qccdz(dps, max_current)
    return _empty("unknown", "Unknown profile", max_current)


def _decode_depow(dps: dict[str, Any], max_current: int) -> Snapshot:
    raw_state = str(dps.get("109", "UNKNOWN")).strip().upper()
    status, label = DEPOW_STATUS.get(raw_state, ("unknown", raw_state or "Unknown"))
    do_charge = _bool(dps.get("140"))
    charging = do_charge is True or raw_state == "WORKING"

    metrics = _json_object(dps.get("102"))
    voltage = 0.0
    current = 0.0
    lines = metrics.get("L1")
    if isinstance(lines, list) and len(lines) >= 2:
        voltage = (_number(lines[0]) or 0.0) / 10.0
        current = (_number(lines[1]) or 0.0) / 10.0
    if not charging:
        current = 0.0

    energy = _number(metrics.get("e"))
    temperature = _number(metrics.get("t"))
    duration = _number(metrics.get("d"))
    target = _integer(dps.get("150"))
    hardware_max = _integer(dps.get("152"))
    max_a = hardware_max if hardware_max and hardware_max > 0 else max_current

    return Snapshot(
        profile="depow_v2",
        status=status,
        status_label=label,
        charging=charging,
        plugged=status in PLUGGED_STATES,
        power_w=round(voltage * current, 1),
        voltage_v=round(voltage, 1),
        current_a=round(current, 1),
        energy_kwh=round(energy / 10.0, 2) if energy is not None else None,
        current_target_a=target,
        max_current_a=max_a,
        do_charge=do_charge,
        temperature_c=round(temperature / 10.0, 1) if temperature is not None else None,
        session_duration_s=round(duration / 10.0) if duration is not None else None,
        work_state=_integer(dps.get("101")),
        nfc_enabled=_bool(dps.get("155")),
        product_variant=_integer(dps.get("157")),
        schedule=_schedule(dps.get("151")),
        last_session=_last_session(dps.get("105")),
        charger_info=_json_object(dps.get("106")) or None,
    )


def _decode_qccdz(dps: dict[str, Any], max_current: int) -> Snapshot:
    raw_state = str(dps.get("38", "")).strip().lower()
    if not raw_state:
        pilot = str(dps.get("13", "")).strip().lower()
        raw_state = PILOT_STATUS.get(pilot, "")
    status, label = QCCDZ_STATUS.get(raw_state, ("unknown", "Unknown"))
    charging = raw_state == "plugged_in_charging"

    voltage = (_number(dps.get("50")) or 0.0) / 10.0
    current = (_number(dps.get("49")) or 0.0) / 10.0 if charging else 0.0
    power = voltage * current if charging else 0.0
    if charging and power == 0.0:
        raw_power = _number(dps.get("48"))
        if raw_power:
            power = raw_power * 100.0
    energy = _number(dps.get("25"))
    target = _integer(dps.get("4"))
    do_charge: bool | None = None
    if "35" in dps:
        do_charge = str(dps.get("35", "")).strip().lower() == "charge"

    return Snapshot(
        profile="qccdz_v1",
        status=status,
        status_label=label,
        charging=charging,
        plugged=status in PLUGGED_STATES,
        power_w=round(power, 1),
        voltage_v=round(voltage, 1),
        current_a=round(current, 1),
        energy_kwh=round(energy / 100.0, 2) if energy is not None else None,
        current_target_a=target,
        max_current_a=max_current,
        do_charge=do_charge,
        temperature_c=_number(dps.get("24")),
        session_duration_s=None,
        work_state=None,
        nfc_enabled=None,
        product_variant=None,
        schedule=None,
        last_session=None,
        charger_info=None,
    )


def charge_command(profile: str, enabled: bool) -> tuple[str, object]:
    """Return the data point and value used to start or stop charging."""
    if profile == "qccdz_v1":
        return "35", "charge" if enabled else "disabled"
    if profile == "depow_v2":
        return "140", bool(enabled)
    raise ValueError(f"Unknown profile: {profile}")


def current_dp(profile: str) -> str:
    """Return the current setpoint data point for a profile."""
    if profile == "qccdz_v1":
        return "4"
    if profile == "depow_v2":
        return "150"
    raise ValueError(f"Unknown profile: {profile}")
