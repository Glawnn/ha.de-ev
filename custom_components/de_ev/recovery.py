"""Find the charger again after its IP address changed."""

from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.core import HomeAssistant

from .const import CONF_DEVICE_ID, CONF_HOST, CONF_LOCAL_KEY, DOMAIN
from .discovery import async_find_charger

LOGGER = logging.getLogger(__name__)

FAILURES_BEFORE_DISCOVERY = 3
DISCOVERY_COOLDOWN = 600.0
DATA_RECOVERY = f"{DOMAIN}_recovery"


class HostRecovery:
    """Look for the charger on the network after repeated connection failures.

    One instance lives per config entry in ``hass.data``, so the failure count
    and the cooldown survive setup retries, when no coordinator exists yet. The
    search runs as a Home Assistant background task: a task tied to the config
    entry would be cancelled as soon as the setup fails.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._hass = hass
        self._entry_id = entry_id
        self._failures = 0
        self._last_search = -DISCOVERY_COOLDOWN
        self._task: asyncio.Task[None] | None = None

    def record_success(self) -> None:
        """Reset the failure count after the charger answered."""
        self._failures = 0

    def record_failure(self) -> None:
        """Count a failed connection and start a search when it is time."""
        self._failures += 1
        if self._failures < FAILURES_BEFORE_DISCOVERY:
            return
        if self._task is not None and not self._task.done():
            return
        if time.monotonic() - self._last_search < DISCOVERY_COOLDOWN:
            return
        self._last_search = time.monotonic()
        self._task = self._hass.async_create_background_task(
            self._async_search(), f"{DOMAIN}_rediscover"
        )

    async def _async_search(self) -> None:
        """Update the entry when the charger answers on a new address."""
        try:
            entry = self._hass.config_entries.async_get_entry(self._entry_id)
            if entry is None:
                return
            host = await async_find_charger(
                self._hass,
                str(entry.data[CONF_DEVICE_ID]),
                str(entry.data.get(CONF_LOCAL_KEY, "")),
            )
            entry = self._hass.config_entries.async_get_entry(self._entry_id)
            if entry is None:
                return
            current = str(entry.data.get(CONF_HOST, ""))
            if not host or host == current:
                LOGGER.debug("Charger not found at a new address")
                return
            LOGGER.warning(
                "Charger %s moved from %s to %s; updating the configuration",
                entry.data[CONF_DEVICE_ID],
                current,
                host,
            )
            self._hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_HOST: host}
            )
        except Exception:
            LOGGER.exception("Charger rediscovery failed")


def async_get_recovery(hass: HomeAssistant, entry_id: str) -> HostRecovery:
    """Return the recovery helper of a config entry, creating it if needed."""
    registry: dict[str, HostRecovery] = hass.data.setdefault(DATA_RECOVERY, {})
    if entry_id not in registry:
        registry[entry_id] = HostRecovery(hass, entry_id)
    return registry[entry_id]
