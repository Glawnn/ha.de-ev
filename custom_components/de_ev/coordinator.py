"""Data coordinator for the Dé EV Charger integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .charger import (
    ChargerAuthError,
    ChargerBusy,
    ChargerClient,
    ChargerError,
    ChargerUnreachable,
)
from .const import CONF_DEVICE_ID, CONF_HOST, CONF_LOCAL_KEY, DOMAIN
from .discovery import async_find_charger
from .profiles import Snapshot

LOGGER = logging.getLogger(__name__)

UNREACHABLE_BEFORE_DISCOVERY = 3
DISCOVERY_COOLDOWN = 600.0


class DeEvCoordinator(DataUpdateCoordinator[Snapshot]):
    """Poll the charger over the local network."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: ChargerClient,
        update_interval: int,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
            config_entry=entry,
        )
        self.client = client
        self._unreachable_count = 0
        self._last_discovery = -DISCOVERY_COOLDOWN
        self._discovering = False

    async def _async_update_data(self) -> Snapshot:
        try:
            snapshot = await self.hass.async_add_executor_job(self.client.status)
        except ChargerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ChargerUnreachable, ChargerBusy) as err:
            self._unreachable_count += 1
            self._maybe_start_discovery()
            raise UpdateFailed(str(err)) from err
        except ChargerError as err:
            raise UpdateFailed(str(err)) from err
        self._unreachable_count = 0
        return snapshot

    def _maybe_start_discovery(self) -> None:
        """Look for the charger on the network after repeated failures."""
        if self._discovering or self.config_entry is None:
            return
        if self._unreachable_count < UNREACHABLE_BEFORE_DISCOVERY:
            return
        if time.monotonic() - self._last_discovery < DISCOVERY_COOLDOWN:
            return
        self._discovering = True
        self._last_discovery = time.monotonic()
        self.config_entry.async_create_background_task(
            self.hass, self._async_rediscover(), f"{DOMAIN}_rediscover"
        )

    async def _async_rediscover(self) -> None:
        """Update the entry when the charger answers on a new address."""
        entry = self.config_entry
        try:
            host = await async_find_charger(
                self.hass,
                str(entry.data[CONF_DEVICE_ID]),
                str(entry.data.get(CONF_LOCAL_KEY, "")),
            )
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
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_HOST: host}
            )
        except Exception:
            LOGGER.exception("Charger rediscovery failed")
        finally:
            self._discovering = False
