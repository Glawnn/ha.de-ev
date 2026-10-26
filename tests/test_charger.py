"""Tests for the local charger client."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.de_ev import charger
from custom_components.de_ev.charger import (
    ChargerClient,
    ChargerSettings,
    ChargerUnreachable,
)

DPS: dict[str, Any] = {
    "102": '{"L1": [2300, 100, 23], "t": 250, "d": 600, "e": 12}',
    "109": "WORKING",
    "140": True,
    "150": 10,
    "152": 16,
}


class FakeDevice:
    """Minimal tinytuya.Device replacement."""

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.closed = False

    def set_socketTimeout(self, timeout: int) -> None:
        """Ignore the socket timeout."""

    def set_socketRetryLimit(self, limit: int) -> None:
        """Ignore the retry limit."""

    def set_socketRetryDelay(self, delay: int) -> None:
        """Ignore the retry delay."""

    def status(self) -> Any:
        """Return the next queued response or raise it."""
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self) -> None:
        """Mark the device as closed."""
        self.closed = True


def test_client_reconnects_after_a_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed poll must not leave the client permanently disconnected."""
    responses: list[Any] = [OSError("Device Unreachable"), {"dps": DPS}]
    created: list[FakeDevice] = []

    def make_device(**kwargs: Any) -> FakeDevice:
        device = FakeDevice(responses)
        created.append(device)
        return device

    monkeypatch.setattr(charger.tinytuya, "Device", make_device)
    monkeypatch.setattr(charger, "_probe", lambda *args, **kwargs: "unreachable")

    client = ChargerClient(
        ChargerSettings(
            host="192.168.1.43",
            device_id="device-1",
            local_key="0123456789abcdef",
        )
    )

    with pytest.raises(ChargerUnreachable):
        client.connect()
    assert client._device is None

    snapshot = client.status()
    assert snapshot.power_w == 2300.0
    assert len(created) == 2
    assert created[0].closed is True
