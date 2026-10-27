"""Tests for the coordinator and the recovery after a charger IP change."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.de_ev import recovery
from custom_components.de_ev.charger import (
    ChargerBusy,
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
from custom_components.de_ev.coordinator import DeEvCoordinator
from custom_components.de_ev.profiles import decode
from custom_components.de_ev.recovery import (
    DISCOVERY_COOLDOWN,
)
from custom_components.de_ev.recovery import (
    FAILURES_BEFORE_DISCOVERY as UNREACHABLE_BEFORE_DISCOVERY,
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


class Charger:
    """Controllable replacement for the network client and discovery."""

    def __init__(self) -> None:
        self.error: Exception | None = None
        self.found = NEW_HOST
        self.searches = 0

    def status(self) -> Any:
        """Return a snapshot or raise the configured error."""
        if self.error is not None:
            raise self.error
        return decode(DPS)

    async def find(self, hass: HomeAssistant, device_id: str, key: str) -> str:
        """Pretend to scan the network."""
        self.searches += 1
        return self.found


@pytest.fixture
def charger(monkeypatch: pytest.MonkeyPatch) -> Charger:
    """Replace the network client and the discovery with in-memory fakes."""
    fake = Charger()
    monkeypatch.setattr(ChargerClient, "connect", lambda self: DPS)
    monkeypatch.setattr(ChargerClient, "status", lambda client: fake.status())
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)
    monkeypatch.setattr(recovery, "async_find_charger", fake.find)
    return fake


@pytest.fixture
async def entry(hass: HomeAssistant, charger: Charger) -> MockConfigEntry:
    """Set up a loaded config entry."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        title="Garage",
        data={
            CONF_HOST: OLD_HOST,
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "3.5",
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    return config_entry


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry, times: int) -> None:
    for _ in range(times):
        coordinator: DeEvCoordinator = entry.runtime_data.coordinator
        await coordinator.async_refresh()
        await hass.async_block_till_done()


async def test_charger_is_found_again_after_an_ip_change(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """After repeated failures the new address is stored in the entry."""
    charger.error = ChargerUnreachable("no route")

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY)

    assert charger.searches == 1
    assert entry.data[CONF_HOST] == NEW_HOST
    assert entry.data[CONF_DEVICE_ID] == "device-1"


async def test_no_search_before_the_threshold(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """A couple of failed polls must not trigger a network scan."""
    charger.error = ChargerUnreachable("no route")

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY - 1)

    assert charger.searches == 0
    assert entry.data[CONF_HOST] == OLD_HOST


async def test_a_successful_poll_resets_the_counter(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """Failures must be consecutive to start a search."""
    charger.error = ChargerUnreachable("no route")
    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY - 1)
    charger.error = None
    await _refresh(hass, entry, 1)
    charger.error = ChargerUnreachable("no route")
    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY - 1)

    assert charger.searches == 0


async def test_busy_port_also_counts(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """The old address may now belong to another device that refuses 6668."""
    charger.error = ChargerBusy("refused")

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY)

    assert entry.data[CONF_HOST] == NEW_HOST


async def test_entry_is_unchanged_when_the_charger_is_not_found(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """An empty result keeps the configured host."""
    charger.error = ChargerUnreachable("no route")
    charger.found = ""

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY)

    assert charger.searches == 1
    assert entry.data[CONF_HOST] == OLD_HOST


async def test_entry_is_unchanged_when_the_host_is_the_same(
    hass: HomeAssistant, entry: MockConfigEntry, charger: Charger
) -> None:
    """Finding the charger at the same address changes nothing."""
    charger.error = ChargerUnreachable("no route")
    charger.found = OLD_HOST

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY)

    assert entry.data[CONF_HOST] == OLD_HOST


async def test_searches_are_rate_limited(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    charger: Charger,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A charger that stays offline does not trigger a scan on every poll."""
    charger.error = ChargerUnreachable("no route")
    charger.found = ""
    clock = [1000.0]
    monkeypatch.setattr(recovery.time, "monotonic", lambda: clock[0])

    await _refresh(hass, entry, UNREACHABLE_BEFORE_DISCOVERY + 5)
    assert charger.searches == 1

    clock[0] += DISCOVERY_COOLDOWN + 1
    await _refresh(hass, entry, 1)
    assert charger.searches == 2
