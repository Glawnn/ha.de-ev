"""Tests for the recovery when the charger moved while Home Assistant was off."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.de_ev import recovery
from custom_components.de_ev.charger import (
    ChargerAuthError,
    ChargerClient,
    ChargerUnreachable,
)
from custom_components.de_ev.const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL,
    DOMAIN,
)
from custom_components.de_ev.profiles import decode
from custom_components.de_ev.recovery import (
    DATA_RECOVERY,
    FAILURES_BEFORE_DISCOVERY,
    async_get_recovery,
)

DPS: dict[str, Any] = {
    "102": '{"L1": [2300, 100, 23], "t": 250, "d": 600, "e": 12}',
    "109": "WORKING",
    "140": True,
    "150": 10,
    "152": 16,
}

OLD_HOST = "192.168.1.50"
NEW_HOST = "192.168.1.77"


class Network:
    """A charger that only answers on one address, plus a fake discovery."""

    def __init__(self) -> None:
        self.reachable_host = NEW_HOST
        self.found = NEW_HOST
        self.searches = 0

    def connect(self, client: ChargerClient) -> dict[str, Any]:
        """Answer only when the client uses the charger's real address."""
        if client.settings.host != self.reachable_host:
            raise ChargerUnreachable("no route")
        return DPS

    async def find(self, hass: HomeAssistant, device_id: str, key: str) -> str:
        """Pretend to scan the network."""
        self.searches += 1
        return self.found


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch) -> Network:
    """Replace the network client and the discovery with in-memory fakes."""
    fake = Network()
    monkeypatch.setattr(ChargerClient, "connect", lambda self: fake.connect(self))
    monkeypatch.setattr(ChargerClient, "status", lambda self: decode(DPS))
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)
    monkeypatch.setattr(recovery, "async_find_charger", fake.find)
    return fake


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garage",
        data={
            CONF_HOST: OLD_HOST,
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "3.5",
        },
    )
    entry.add_to_hass(hass)
    return entry


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Run one setup attempt, like Home Assistant does on each retry."""
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _retry(hass: HomeAssistant, entry: MockConfigEntry, times: int) -> None:
    for _ in range(times):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()


async def test_charger_is_found_when_it_moved_while_home_assistant_was_off(
    hass: HomeAssistant, network: Network
) -> None:
    """Setup keeps failing on the old address, then the new one is stored."""
    entry = _entry(hass)

    await _setup(hass, entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    await _retry(hass, entry, FAILURES_BEFORE_DISCOVERY - 1)

    assert network.searches == 1
    assert entry.data[CONF_HOST] == NEW_HOST

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=10))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert entry.state is ConfigEntryState.LOADED


async def test_no_search_before_the_threshold(
    hass: HomeAssistant, network: Network
) -> None:
    """A couple of failed setups must not trigger a network scan."""
    entry = _entry(hass)

    await _setup(hass, entry)
    await _retry(hass, entry, FAILURES_BEFORE_DISCOVERY - 2)

    assert network.searches == 0
    assert entry.data[CONF_HOST] == OLD_HOST


async def test_entry_is_unchanged_when_the_charger_is_not_found(
    hass: HomeAssistant, network: Network
) -> None:
    """An empty result keeps the configured host and keeps retrying."""
    network.found = ""
    entry = _entry(hass)

    await _setup(hass, entry)
    await _retry(hass, entry, FAILURES_BEFORE_DISCOVERY)

    assert network.searches == 1
    assert entry.data[CONF_HOST] == OLD_HOST
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_a_wrong_key_does_not_trigger_a_search(
    hass: HomeAssistant, network: Network, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rejected key is not an address problem and starts a reauth instead."""

    def connect(self: ChargerClient) -> dict[str, Any]:
        raise ChargerAuthError("bad key")

    monkeypatch.setattr(ChargerClient, "connect", connect)
    entry = _entry(hass)

    await _setup(hass, entry)
    await _retry(hass, entry, FAILURES_BEFORE_DISCOVERY)

    assert network.searches == 0


async def test_state_is_shared_between_setup_and_polling(
    hass: HomeAssistant, network: Network
) -> None:
    """The same helper serves the setup retries and the coordinator."""
    first = async_get_recovery(hass, "entry-1")

    assert async_get_recovery(hass, "entry-1") is first
    assert async_get_recovery(hass, "entry-2") is not first
    assert set(hass.data[DATA_RECOVERY]) == {"entry-1", "entry-2"}
