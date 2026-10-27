"""Tests for the switch and number controls."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.de_ev.charger import ChargerClient, ChargerError
from custom_components.de_ev.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL,
    DOMAIN,
)
from custom_components.de_ev.profiles import decode

DPS: dict[str, Any] = {
    "102": '{"L1": [2300, 100, 23], "t": 250, "d": 600, "e": 12}',
    "109": "WORKING",
    "140": True,
    "150": 10,
    "152": 16,
}

ENTRY_DATA = {
    CONF_HOST: "192.168.1.50",
    CONF_DEVICE_ID: "device-1",
    CONF_LOCAL_KEY: "0123456789abcdef",
    CONF_PROTOCOL: "3.5",
}

SWITCH = "switch.garage_charging_session"
NUMBER = "number.garage_charging_current"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Replace the network client with mocks for reads and writes."""
    mocks = {"set_charge": MagicMock(), "set_current": MagicMock()}
    monkeypatch.setattr(ChargerClient, "connect", lambda self: DPS)
    monkeypatch.setattr(ChargerClient, "status", lambda self: decode(DPS))
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)
    monkeypatch.setattr(
        ChargerClient, "set_charge", lambda self, enabled: mocks["set_charge"](enabled)
    )
    monkeypatch.setattr(
        ChargerClient, "set_current", lambda self, amps: mocks["set_current"](amps)
    )
    return mocks


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant, client: dict[str, MagicMock]
) -> MockConfigEntry:
    """Set up a config entry with the mocked client."""
    entry = MockConfigEntry(domain=DOMAIN, title="Garage", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


@pytest.mark.usefixtures("loaded_entry")
async def test_switch_turn_off_calls_client(
    hass: HomeAssistant, client: dict[str, MagicMock]
) -> None:
    """Turning the switch off stops the charging session."""
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": SWITCH}, blocking=True
    )

    client["set_charge"].assert_called_once_with(False)


@pytest.mark.usefixtures("loaded_entry")
async def test_switch_error_becomes_ha_error(
    hass: HomeAssistant, client: dict[str, MagicMock]
) -> None:
    """A charger error is surfaced as a Home Assistant error."""
    client["set_charge"].side_effect = ChargerError("boom")

    with pytest.raises(HomeAssistantError, match="boom"):
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": SWITCH}, blocking=True
        )


@pytest.mark.usefixtures("loaded_entry")
async def test_number_set_value_calls_client(
    hass: HomeAssistant, client: dict[str, MagicMock]
) -> None:
    """Setting the number writes the new current setpoint."""
    await hass.services.async_call(
        "number", "set_value", {"entity_id": NUMBER, "value": 12}, blocking=True
    )

    client["set_current"].assert_called_once_with(12)


@pytest.mark.usefixtures("loaded_entry")
async def test_number_error_becomes_ha_error(
    hass: HomeAssistant, client: dict[str, MagicMock]
) -> None:
    """A charger error is surfaced as a Home Assistant error."""
    client["set_current"].side_effect = ChargerError("boom")

    with pytest.raises(HomeAssistantError, match="boom"):
        await hass.services.async_call(
            "number", "set_value", {"entity_id": NUMBER, "value": 12}, blocking=True
        )
