"""Tests for the Tuya data point decoding."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.de_ev.profiles import (
    charge_command,
    current_dp,
    decode,
    detect_profile,
)

DEPOW_DPS: dict[str, Any] = {
    "102": '{"L1": [2300, 100, 23], "t": 250, "d": 600, "e": 12}',
    "109": "WORKING",
    "140": True,
    "150": 10,
    "152": 16,
}

QCCDZ_DPS: dict[str, Any] = {
    "38": "plugged_in_charging",
    "50": 2300,
    "49": 100,
    "4": 10,
    "35": "charge",
    "25": 150,
}


def test_decode_depow_charging() -> None:
    """A charging depow charger exposes its live measurements."""
    snapshot = decode(DEPOW_DPS)

    assert snapshot.profile == "depow_v2"
    assert snapshot.status == "charging"
    assert snapshot.charging is True
    assert snapshot.plugged is True
    assert snapshot.voltage_v == 230.0
    assert snapshot.current_a == 10.0
    assert snapshot.power_w == 2300.0
    assert snapshot.energy_kwh == 1.2
    assert snapshot.temperature_c == 25.0
    assert snapshot.session_duration_s == 60
    assert snapshot.current_target_a == 10
    assert snapshot.max_current_a == 16


def test_decode_depow_idle_forces_zero_current() -> None:
    """An idle charger reports no current even if stale measurements remain."""
    dps = {**DEPOW_DPS, "109": "IDLE", "140": False}

    snapshot = decode(dps)

    assert snapshot.status == "idle"
    assert snapshot.charging is False
    assert snapshot.plugged is False
    assert snapshot.current_a == 0.0
    assert snapshot.power_w == 0.0


def test_decode_qccdz_charging() -> None:
    """A charging qccdz charger is decoded with its own scaling."""
    snapshot = decode(QCCDZ_DPS)

    assert snapshot.profile == "qccdz_v1"
    assert snapshot.status == "charging"
    assert snapshot.charging is True
    assert snapshot.voltage_v == 230.0
    assert snapshot.current_a == 10.0
    assert snapshot.power_w == 2300.0
    assert snapshot.energy_kwh == 1.5
    assert snapshot.current_target_a == 10
    assert snapshot.do_charge is True


def test_decode_qccdz_falls_back_to_pilot_state() -> None:
    """Without DP 38 the state is derived from the pilot DP 13."""
    snapshot = decode({"13": "charging", "35": "disabled"})

    assert snapshot.profile == "qccdz_v1"
    assert snapshot.status == "charging"
    assert snapshot.do_charge is False


def test_decode_unknown_profile() -> None:
    """Unrecognised data points never raise and expose an unknown snapshot."""
    snapshot = decode({}, max_current=10)

    assert snapshot.profile == "unknown"
    assert snapshot.status == "unknown"
    assert snapshot.charging is False
    assert snapshot.max_current_a == 10


@pytest.mark.parametrize(
    ("dps", "profile"),
    [
        ({"102": "{}"}, "depow_v2"),
        ({"38": "fault"}, "qccdz_v1"),
        ({"35": "charge"}, "qccdz_v1"),
        ({"999": 1}, "unknown"),
        ({}, "unknown"),
    ],
)
def test_detect_profile(dps: dict[str, Any], profile: str) -> None:
    """The profile is inferred from which data points are present."""
    assert detect_profile(dps) == profile


@pytest.mark.parametrize(
    ("profile", "enabled", "expected"),
    [
        ("depow_v2", True, ("140", True)),
        ("depow_v2", False, ("140", False)),
        ("qccdz_v1", True, ("35", "charge")),
        ("qccdz_v1", False, ("35", "disabled")),
    ],
)
def test_charge_command(
    profile: str, enabled: bool, expected: tuple[str, object]
) -> None:
    """Start and stop map to the right data point and value per profile."""
    assert charge_command(profile, enabled) == expected


@pytest.mark.parametrize(
    ("profile", "dp"), [("depow_v2", "150"), ("qccdz_v1", "4")]
)
def test_current_dp(profile: str, dp: str) -> None:
    """Each profile has its own current setpoint data point."""
    assert current_dp(profile) == dp


def test_unknown_profile_raises() -> None:
    """Commands cannot be built for an unknown profile."""
    with pytest.raises(ValueError):
        charge_command("unknown", True)
    with pytest.raises(ValueError):
        current_dp("unknown")
