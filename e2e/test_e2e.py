"""End-to-end tests: real Home Assistant talking Tuya 3.3 to a fake charger."""

from __future__ import annotations

from typing import Any

import pytest

from .conftest import HA_URL, Charger, HomeAssistant, http

LOCAL_KEY = "0123456789abcdef"
ENTRY_INPUT = {
    "name": "Garage",
    "host": "fake-charger",
    "device_id": "e2e-device-1",
    "local_key": LOCAL_KEY,
    "protocol_version": "3.3",
}
STATUS = "sensor.garage_status"
POWER = "sensor.garage_power"
SWITCH = "switch.garage_charging_session"
NUMBER = "number.garage_charging_current"


def _add_entry(ha: HomeAssistant) -> str:
    """Create the config entry through the local config flow."""
    status, result = ha.request(
        "/api/config/config_entries/flow", {"handler": "de_ev"}
    )
    assert status == 200, result
    flow_id = result["flow_id"]
    status, result = ha.request(
        f"/api/config/config_entries/flow/{flow_id}", {"next_step_id": "local"}
    )
    assert status == 200, result
    status, result = ha.request(
        f"/api/config/config_entries/flow/{flow_id}", ENTRY_INPUT
    )
    assert status == 200, result
    for _ in range(40):
        if result["type"] != "progress":
            break
        status, result = ha.request(
            f"/api/config/config_entries/flow/{flow_id}", {}
        )
    assert result["type"] == "create_entry", result
    return result["result"]["entry_id"]


@pytest.fixture
def entry_id(ha: HomeAssistant, charger: Charger) -> Any:
    """Add the charger entry for one test and remove it afterwards."""
    entry = _add_entry(ha)
    assert ha.wait_for(STATUS, "charging") == "charging"
    yield entry
    ha.request(f"/api/config/config_entries/entry/{entry}", method="DELETE")


def test_config_flow_detects_the_charger(
    ha: HomeAssistant, charger: Charger, entry_id: str
) -> None:
    """The local flow validates against the fake charger and creates entities."""
    assert ha.state(STATUS) == "charging"
    assert ha.state(POWER) == "2300.0"
    assert ha.state(SWITCH) == "on"
    assert ha.state(NUMBER) == "10"


def test_stop_charging_writes_to_the_charger(
    ha: HomeAssistant, charger: Charger, entry_id: str
) -> None:
    """Turning the switch off reaches the charger (the write path)."""
    assert ha.call("switch", "turn_off", {"entity_id": SWITCH}) == 200

    state = charger.state()
    assert ["140", False] in state["writes"]
    assert state["dps"]["109"] == "IDLEINS"
    assert ha.wait_for(SWITCH, "off") == "off"
    assert ha.state(POWER) == "0.0"


def test_set_current_writes_to_the_charger(
    ha: HomeAssistant, charger: Charger, entry_id: str
) -> None:
    """Changing the current setpoint reaches the charger."""
    status = ha.call("number", "set_value", {"entity_id": NUMBER, "value": 12})

    assert status == 200
    assert ["150", 12] in charger.state()["writes"]
    assert ha.wait_for(NUMBER, "12") == "12"


def test_write_recovers_after_connection_loss(
    ha: HomeAssistant, charger: Charger, entry_id: str
) -> None:
    """A write fails while the charger is down and works again once it is back."""
    charger.stop()
    status = ha.call("number", "set_value", {"entity_id": NUMBER, "value": 14})
    assert status >= 400

    charger.start()
    status = ha.call("number", "set_value", {"entity_id": NUMBER, "value": 14})
    assert status == 200
    assert ["150", 14] in charger.state()["writes"]


def test_rejected_key_makes_the_entities_unavailable(
    ha: HomeAssistant, charger: Charger, entry_id: str
) -> None:
    """A key change on the charger is detected and recovered after restoring it."""
    charger.set_local_key("fedcba9876543210")
    assert ha.wait_for(STATUS, "unavailable") == "unavailable"

    charger.set_local_key(LOCAL_KEY)
    ha.request(f"/api/config/config_entries/entry/{entry_id}/reload", {})
    assert ha.wait_for(STATUS, "charging") == "charging"


def test_frontend_card_is_served(ha: HomeAssistant, entry_id: str) -> None:
    """The bundled Lovelace card is served by Home Assistant."""
    status, body = http(f"{HA_URL}/de_ev/frontend/de-ev-charger-card.js")

    assert status == 200
    assert "de-ev-charger" in body
