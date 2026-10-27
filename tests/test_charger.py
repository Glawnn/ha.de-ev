"""Tests for the local charger client."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.de_ev import charger
from custom_components.de_ev.charger import (
    ChargerClient,
    ChargerError,
    ChargerSettings,
    ChargerUnreachable,
    _values_match,
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
        self.writes: list[tuple[str, Any]] = []
        self.write_error: Exception | None = None

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

    def set_value(self, dp: str, value: Any) -> dict[str, Any]:
        """Record the write and update the next status response."""
        if self.write_error is not None:
            raise self.write_error
        self.writes.append((dp, value))
        for response in self.responses:
            if isinstance(response, dict) and "dps" in response:
                response["dps"] = {**response["dps"], dp: value}
        return {"dps": {dp: value}}

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


SETTINGS = ChargerSettings(
    host="192.168.1.43",
    device_id="device-1",
    local_key="0123456789abcdef",
)


@pytest.fixture
def fake_device(monkeypatch: pytest.MonkeyPatch) -> list[FakeDevice]:
    """Patch tinytuya so every client uses a queue-backed FakeDevice."""
    created: list[FakeDevice] = []
    responses: list[Any] = [{"dps": dict(DPS)} for _ in range(10)]

    def make_device(**kwargs: Any) -> FakeDevice:
        device = FakeDevice(responses)
        created.append(device)
        return device

    monkeypatch.setattr(charger.tinytuya, "Device", make_device)
    monkeypatch.setattr(charger.time, "sleep", lambda _: None)
    monkeypatch.setattr(charger, "_probe", lambda *args, **kwargs: "unreachable")
    return created


def test_set_current_writes_the_setpoint(fake_device: list[FakeDevice]) -> None:
    """Changing the current goes through the write path."""
    client = ChargerClient(SETTINGS)

    dps = client.set_current(12)

    assert fake_device[0].writes == [("150", 12)]
    assert dps["150"] == 12


def test_set_current_skips_the_write_when_unchanged(
    fake_device: list[FakeDevice],
) -> None:
    """No write is sent when the setpoint already matches."""
    client = ChargerClient(SETTINGS)

    client.set_current(10)

    assert fake_device[0].writes == []


def test_set_charge_stops_and_skips_when_already_in_state(
    fake_device: list[FakeDevice],
) -> None:
    """Stopping writes DP 140 once, requesting the same state writes nothing."""
    client = ChargerClient(SETTINGS)

    client.set_charge(True)
    assert fake_device[0].writes == []

    client.set_charge(False)
    assert fake_device[0].writes == [("140", False)]


def test_write_reconnects_when_device_is_none(
    fake_device: list[FakeDevice],
) -> None:
    """A write after a dropped connection must reconnect, not crash."""
    client = ChargerClient(SETTINGS)
    assert client._device is None

    client._write("150", 12)

    assert len(fake_device) == 1
    assert fake_device[0].writes == [("150", 12)]


@pytest.mark.parametrize("amps", [5, 17])
def test_set_current_rejects_out_of_range(
    fake_device: list[FakeDevice], amps: int
) -> None:
    """Values outside the allowed range are refused before any write."""
    client = ChargerClient(SETTINGS)

    with pytest.raises(ChargerError, match="outside the allowed range"):
        client.set_current(amps)

    assert fake_device[0].writes == []


def test_write_failure_closes_the_device(fake_device: list[FakeDevice]) -> None:
    """A failing write is classified and drops the connection."""
    client = ChargerClient(SETTINGS)
    client.read_dps()
    fake_device[0].write_error = OSError("Device Unreachable")

    with pytest.raises(ChargerUnreachable):
        client._write("150", 12)

    assert client._device is None
    assert fake_device[0].closed is True


@pytest.mark.parametrize(
    ("current", "expected", "result"),
    [
        (True, True, True),
        (1, True, True),
        (0, False, True),
        ("on", True, False),
        ("true", True, True),
        ("FALSE", False, True),
        ("10", 10, True),
        (10.0, 10, True),
        ("abc", 10, False),
        (None, True, False),
        (" Charge ", "charge", True),
    ],
)
def test_values_match(current: Any, expected: Any, result: bool) -> None:
    """Confirmation compares values across the types Tuya may return."""
    assert _values_match(current, expected) is result
