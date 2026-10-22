"""Dé EV Charger integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry, ConfigEntryError
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .charger import (
    ChargerAuthError,
    ChargerClient,
    ChargerError,
    ChargerSettings,
)
from .const import (
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_MAX_CURRENT,
    CONF_MIN_CURRENT,
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MIN_CURRENT,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import DeEvCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
]


@dataclass(slots=True)
class DeEvRuntimeData:
    """Runtime objects stored on the config entry."""

    client: ChargerClient
    coordinator: DeEvCoordinator


type DeEvConfigEntry = ConfigEntry[DeEvRuntimeData]


def _settings_from_entry(entry: DeEvConfigEntry) -> ChargerSettings:
    return ChargerSettings(
        host=str(entry.data.get(CONF_HOST, "")).strip(),
        device_id=str(entry.data.get(CONF_DEVICE_ID, "")).strip(),
        local_key=str(entry.data.get(CONF_LOCAL_KEY, "")).strip(),
        version=str(entry.data.get(CONF_PROTOCOL, "3.5")),
        min_current=int(entry.options.get(CONF_MIN_CURRENT, DEFAULT_MIN_CURRENT)),
        max_current=int(entry.options.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)),
    )


async def async_setup_entry(hass: HomeAssistant, entry: DeEvConfigEntry) -> bool:
    """Set up Dé EV Charger from a config entry."""
    settings = _settings_from_entry(entry)
    if not settings.host or not settings.device_id or not settings.local_key:
        raise ConfigEntryError(
            "The charger entry is incomplete. Remove it and add the charger again."
        )

    client = ChargerClient(settings)
    try:
        await hass.async_add_executor_job(client.connect)
    except ChargerAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except ChargerError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = DeEvCoordinator(
        hass,
        entry,
        client,
        update_interval=int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = DeEvRuntimeData(client=client, coordinator=coordinator)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DeEvConfigEntry) -> bool:
    """Unload a Dé EV Charger config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await hass.async_add_executor_job(entry.runtime_data.client.close)
        entry.runtime_data = None
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: DeEvConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
