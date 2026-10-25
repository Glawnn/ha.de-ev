"""Tests for the Dé EV Charger config flow."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import Event, HomeAssistant
from homeassistant.data_entry_flow import EVENT_DATA_ENTRY_FLOW_PROGRESSED
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.de_ev import config_flow
from custom_components.de_ev.charger import ChargerAuthError, ChargerClient
from custom_components.de_ev.cloud import CloudAuthError
from custom_components.de_ev.const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_AREA_ID,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_PROTOCOL,
    CONF_REGION,
    DEFAULT_PROTOCOL,
    DOMAIN,
)
from custom_components.de_ev.profiles import decode

DPS: dict[str, Any] = {
    "102": '{"L1": [2300, 100, 23], "t": 250, "d": 600, "e": 12}',
    "109": "WORKING",
    "140": True,
    "150": 10,
    "152": 16,
    "105": '{"c": 12, "d": 600}',
}

DEVICE = {
    "id": "device-1",
    "name": "Garage charger",
    "local_key": "0123456789abcdef",
    "ip": "192.168.1.50",
    "category": "dlq",
    "product_name": "EV charger",
    "online": True,
}


@pytest.fixture(autouse=True)
def mock_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid touching a real charger during config flow tests."""

    async def _validate(*args: Any, **kwargs: Any) -> tuple[str, Any]:
        return DEFAULT_PROTOCOL, decode(DPS)

    monkeypatch.setattr(config_flow, "_validate_connection", _validate)
    monkeypatch.setattr(config_flow, "get_device", lambda *args: {})
    monkeypatch.setattr(config_flow, "scan_udp", lambda *args, **kwargs: [])

    async def _no_scan(*args: Any, **kwargs: Any) -> list[str]:
        return []

    monkeypatch.setattr(config_flow, "scan_lan", _no_scan)
    monkeypatch.setattr(ChargerClient, "connect", lambda self: DPS)
    monkeypatch.setattr(ChargerClient, "status", lambda self: decode(DPS))
    monkeypatch.setattr(ChargerClient, "close", lambda self: None)


async def _unload_entries(hass: HomeAssistant) -> None:
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def _configure(
    hass: HomeAssistant,
    result: dict[str, Any],
    user_input: dict[str, Any] | None,
) -> dict[str, Any]:
    """Submit a step and finish any progress step."""
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input
    )
    if result["type"] is data_entry_flow.FlowResultType.SHOW_PROGRESS:
        await hass.async_block_till_done()
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {}
        )
    return result


async def _start_cloud(hass: HomeAssistant) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    assert result["step_id"] == "user"
    return await _configure(
        hass,
        result,
        {"next_step_id": "cloud"},
    )


async def test_cloud_flow_creates_entry(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud discovery lists devices and creates the entry."""
    monkeypatch.setattr(config_flow, "list_devices", lambda *args: [DEVICE])

    result = await _start_cloud(hass)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "cloud"

    result = await _configure(
        hass,
        result,
        {
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "access-id",
            CONF_ACCESS_SECRET: "access-secret",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "cloud_device"

    result = await _configure(
        hass,
        result,
        {CONF_DEVICE_ID: "device-1"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local"

    result = await _configure(
        hass,
        result,
        {
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "auto",
            CONF_AREA_ID: "",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garage charger"
    assert result["data"][CONF_DEVICE_ID] == "device-1"
    assert result["data"][CONF_HOST] == "192.168.1.50"
    assert result["data"][CONF_LOCAL_KEY] == "0123456789abcdef"
    assert result["data"][CONF_PROTOCOL] == DEFAULT_PROTOCOL
    assert result["data"][CONF_ACCESS_ID] == "access-id"
    await _unload_entries(hass)


async def test_cloud_flow_prompts_for_ip_when_missing(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud devices without a LAN IP ask for one explicitly."""
    monkeypatch.setattr(
        config_flow,
        "list_devices",
        lambda *args: [{**DEVICE, "ip": "", "wan_ip": "203.0.113.10"}],
    )

    result = await _start_cloud(hass)
    result = await _configure(
        hass,
        result,
        {
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "access-id",
            CONF_ACCESS_SECRET: "access-secret",
        },
    )
    result = await _configure(
        hass,
        result,
        {CONF_DEVICE_ID: "device-1"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "host"

    result = await _configure(
        hass,
        result,
        {CONF_HOST: "192.168.1.50"},
    )
    assert result["step_id"] == "local"

    result = await _configure(
        hass,
        result,
        {
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "auto",
            CONF_AREA_ID: "",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_HOST] == "192.168.1.50"
    await _unload_entries(hass)


async def test_cloud_auth_failure_is_reported(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud errors are shown on the form."""

    def _raise(*args: Any) -> list[dict[str, Any]]:
        raise CloudAuthError("bad credentials")

    monkeypatch.setattr(config_flow, "list_devices", _raise)

    result = await _start_cloud(hass)
    result = await _configure(
        hass,
        result,
        {
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "bad",
            CONF_ACCESS_SECRET: "bad",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "cloud"
    assert result["errors"]["base"] == "cloud_auth_failed"


async def test_local_flow_creates_entry(hass: HomeAssistant) -> None:
    """The manual local flow validates and creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await _configure(
        hass,
        result,
        {"next_step_id": "local"},
    )
    assert result["step_id"] == "local"

    result = await _configure(
        hass,
        result,
        {
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "3.5",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_ID] == "device-1"
    await _unload_entries(hass)


async def test_duplicate_device_is_aborted(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The same device cannot be added twice."""
    monkeypatch.setattr(config_flow, "list_devices", lambda *args: [DEVICE])
    MockConfigEntry(domain=DOMAIN, unique_id="device-1").add_to_hass(hass)

    result = await _start_cloud(hass)
    result = await _configure(
        hass,
        result,
        {
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "access-id",
            CONF_ACCESS_SECRET: "access-secret",
        },
    )
    result = await _configure(
        hass,
        result,
        {CONF_DEVICE_ID: "device-1"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_local_timeout_is_reported(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stuck local connection ends with an explicit timeout error."""

    async def _hang(*args: Any, **kwargs: Any) -> tuple[str, Any]:
        await asyncio.sleep(1)
        raise AssertionError("validation should have been cancelled")

    monkeypatch.setattr(config_flow, "_validate_connection", _hang)
    monkeypatch.setattr(config_flow, "LOCAL_VALIDATION_TIMEOUT", 0.05)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "local"},
    )
    result = await _configure(
        hass,
        result,
        {
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "3.5",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "local"
    assert result["errors"]["base"] == "timeout"


async def test_local_flow_aborts_when_device_already_configured(
    hass: HomeAssistant,
) -> None:
    """An already configured device aborts before the progress step starts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-1",
        data={
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: DEFAULT_PROTOCOL,
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"next_step_id": "local"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.50",
            CONF_DEVICE_ID: "device-1",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: "auto",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_cloud_progress_notifies_the_frontend(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finishing a progress step on the same form step wakes the frontend."""

    def _raise(*args: Any) -> list[dict[str, Any]]:
        raise CloudAuthError("bad credentials")

    monkeypatch.setattr(config_flow, "list_devices", _raise)
    events: list[Event] = []
    hass.bus.async_listen(
        EVENT_DATA_ENTRY_FLOW_PROGRESSED, lambda event: events.append(event)
    )

    result = await _start_cloud(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "bad",
            CONF_ACCESS_SECRET: "bad",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.SHOW_PROGRESS
    flow_id = result["flow_id"]
    await hass.async_block_till_done()

    assert any(
        event.data["flow_id"] == flow_id and event.data.get("refresh")
        for event in events
    )


def _cloud_entry() -> MockConfigEntry:
    """Build a cloud-backed entry with the local connection details."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-1",
        data={
            CONF_REGION: "eu",
            CONF_ACCESS_ID: "access-id",
            CONF_ACCESS_SECRET: "access-secret",
            CONF_DEVICE_ID: "device-1",
            CONF_HOST: "192.168.1.50",
            CONF_LOCAL_KEY: "0123456789abcdef",
            CONF_PROTOCOL: DEFAULT_PROTOCOL,
        },
    )


async def _start_reauth(
    hass: HomeAssistant, entry: MockConfigEntry
) -> dict[str, Any]:
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_REAUTH,
            "entry_id": entry.entry_id,
        },
        data=entry.data,
    )


async def _start_reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry
) -> dict[str, Any]:
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )


async def test_reauth_uses_the_cloud_key(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reauthentication succeeds without asking when the cloud has the new key."""
    entry = _cloud_entry()
    entry.add_to_hass(hass)
    cloud_key = "fedcba9876543210"
    monkeypatch.setattr(
        config_flow,
        "get_device",
        lambda *args: {**DEVICE, "local_key": cloud_key},
    )

    async def _validate(*args: Any, **kwargs: Any) -> tuple[str, Any]:
        assert args[3] == cloud_key
        return DEFAULT_PROTOCOL, decode(DPS)

    monkeypatch.setattr(config_flow, "_validate_connection", _validate)

    result = await _start_reauth(hass, entry)

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_LOCAL_KEY] == cloud_key


async def test_reauth_falls_back_to_the_manual_key(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reauthentication shows the form when Tuya Cloud has no key."""
    entry = _cloud_entry()
    entry.add_to_hass(hass)
    monkeypatch.setattr(config_flow, "get_device", lambda *args: {})

    result = await _start_reauth(hass, entry)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_key = "fedcba9876543210"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LOCAL_KEY: new_key}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_LOCAL_KEY] == new_key


async def test_reauth_reports_a_rejected_cloud_key(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A key returned by the cloud that the charger rejects is explained."""
    entry = _cloud_entry()
    entry.add_to_hass(hass)
    cloud_key = "badkey0000000000"
    monkeypatch.setattr(
        config_flow,
        "get_device",
        lambda *args: {**DEVICE, "local_key": cloud_key},
    )

    async def _validate(
        hass_: HomeAssistant,
        host: str,
        device_id: str,
        local_key: str,
        protocol: str,
    ) -> tuple[str, Any]:
        if local_key == cloud_key:
            raise ChargerAuthError("rejected")
        return DEFAULT_PROTOCOL, decode(DPS)

    monkeypatch.setattr(config_flow, "_validate_connection", _validate)

    result = await _start_reauth(hass, entry)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "cloud_key_invalid"

    new_key = "fedcba9876543210"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LOCAL_KEY: new_key}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert entry.data[CONF_LOCAL_KEY] == new_key


async def test_reauth_reports_an_unchanged_cloud_key(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cloud key identical to the stored key does not loop silently."""
    entry = _cloud_entry()
    entry.add_to_hass(hass)
    monkeypatch.setattr(
        config_flow,
        "get_device",
        lambda *args: {**DEVICE, "local_key": entry.data[CONF_LOCAL_KEY]},
    )

    result = await _start_reauth(hass, entry)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"]["base"] == "cloud_key_unchanged"

    new_key = "fedcba9876543210"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_LOCAL_KEY: new_key}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert entry.data[CONF_LOCAL_KEY] == new_key


async def test_reconfigure_prefills_the_cloud_key(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reconfiguration starts with the key currently stored in Tuya Cloud."""
    entry = _cloud_entry()
    entry.add_to_hass(hass)
    cloud_key = "fedcba9876543210"
    monkeypatch.setattr(
        config_flow,
        "get_device",
        lambda *args: {**DEVICE, "local_key": cloud_key},
    )

    result = await _start_reconfigure(hass, entry)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    schema = result["data_schema"].schema
    key_marker = next(
        key
        for key in schema
        if getattr(key, "schema", key) == CONF_LOCAL_KEY
    )
    assert key_marker.default() == cloud_key

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.50",
            CONF_LOCAL_KEY: cloud_key,
            CONF_PROTOCOL: "auto",
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_LOCAL_KEY] == cloud_key
