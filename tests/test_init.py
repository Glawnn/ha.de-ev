"""Tests for the Dé EV Charger integration lifecycle."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.de_ev.charger import ChargerClient
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


@pytest.fixture(autouse=True)
def mock_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the network client with an in-memory charger."""
    monkeypatch.setattr(ChargerClient, "connect", lambda self: DPS)
    monkeypatch.setattr(ChargerClient, "status", lambda self: decode(DPS))
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)


async def test_setup_and_unload_entry(hass: HomeAssistant) -> None:
    """The config entry can be loaded and unloaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garage",
        data=ENTRY_DATA,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get("sensor.garage_status") is not None
    assert hass.states.get("sensor.garage_power").state == "2300.0"
    assert hass.states.get("binary_sensor.garage_charging").state == "on"
    assert hass.states.get("switch.garage_charging_session").state == "on"
    assert hass.states.get("number.garage_charging_current").state == "10"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
