"""Tests for the charger discovery helpers."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant

from custom_components.de_ev import discovery
from custom_components.de_ev.charger import (
    ChargerAuthError,
    ChargerBusy,
    ChargerClient,
    ChargerUnreachable,
)

KEY = "0123456789abcdef"


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Fake the UDP announcements, the LAN scan and the per-host probe."""
    state: dict[str, Any] = {"udp": [], "lan": [], "accepts": set(), "probed": []}

    monkeypatch.setattr(discovery, "scan_udp", lambda timeout=8: state["udp"])

    async def scan_lan(**kwargs: Any) -> list[str]:
        return state["lan"]

    def probe_host(host: str, device_id: str, local_key: str) -> bool:
        state["probed"].append(host)
        return host in state["accepts"]

    monkeypatch.setattr(discovery, "scan_lan", scan_lan)
    monkeypatch.setattr(discovery, "probe_host", probe_host)
    return state


async def test_udp_announcement_wins(
    hass: HomeAssistant, network: dict[str, Any]
) -> None:
    """A UDP announcement for the device gives its address without scanning."""
    network["udp"] = [
        {"device_id": "other", "ip": "192.168.1.10"},
        {"device_id": "device-1", "ip": "192.168.1.77"},
    ]
    network["lan"] = ["192.168.1.99"]

    host = await discovery.async_find_charger(hass, "device-1", KEY)

    assert host == "192.168.1.77"
    assert network["probed"] == []


async def test_lan_scan_finds_the_host_that_accepts_the_key(
    hass: HomeAssistant, network: dict[str, Any]
) -> None:
    """Without an announcement, the host that accepts the key is returned."""
    network["lan"] = ["192.168.1.10", "192.168.1.20", "192.168.1.30"]
    network["accepts"] = {"192.168.1.20"}

    host = await discovery.async_find_charger(hass, "device-1", KEY)

    assert host == "192.168.1.20"


async def test_nothing_found_returns_an_empty_string(
    hass: HomeAssistant, network: dict[str, Any]
) -> None:
    """No announcement and no accepting host gives an empty address."""
    network["lan"] = ["192.168.1.10"]

    assert await discovery.async_find_charger(hass, "device-1", KEY) == ""


async def test_lan_scan_is_skipped_without_a_local_key(
    hass: HomeAssistant, network: dict[str, Any]
) -> None:
    """Probing needs the key; without it only UDP can find the charger."""
    network["lan"] = ["192.168.1.10"]
    network["accepts"] = {"192.168.1.10"}

    assert await discovery.async_find_charger(hass, "device-1", "") == ""
    assert network["probed"] == []


async def test_udp_failure_falls_back_to_the_lan_scan(
    hass: HomeAssistant,
    network: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An error during the UDP listen does not stop the search."""

    def broken(timeout: int = 8) -> list[dict[str, Any]]:
        raise OSError("bind failed")

    monkeypatch.setattr(discovery, "scan_udp", broken)
    network["lan"] = ["192.168.1.20"]
    network["accepts"] = {"192.168.1.20"}

    assert await discovery.async_find_charger(hass, "device-1", KEY) == "192.168.1.20"


@pytest.mark.parametrize(
    ("outcomes", "expected", "attempts"),
    [
        ([None], True, 1),
        ([ChargerAuthError("bad"), None], True, 2),
        ([ChargerAuthError("bad")] * 3, False, 3),
        ([ChargerBusy("refused")], False, 1),
        ([ChargerUnreachable("down")], False, 1),
    ],
)
def test_probe_host(
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[Exception | None],
    expected: bool,
    attempts: int,
) -> None:
    """The probe tries each protocol and stops on a network-level failure."""
    calls: list[str] = []

    def connect(self: ChargerClient) -> dict[str, Any]:
        calls.append(self.settings.version)
        outcome = outcomes[len(calls) - 1]
        if outcome is not None:
            raise outcome
        return {}

    monkeypatch.setattr(ChargerClient, "connect", connect)
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)

    assert discovery.probe_host("192.168.1.20", "device-1", KEY) is expected
    assert len(calls) == attempts
