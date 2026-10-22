"""Data coordinator for the Dé EV Charger integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .charger import ChargerAuthError, ChargerClient, ChargerError
from .const import DOMAIN
from .profiles import Snapshot

LOGGER = logging.getLogger(__name__)


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

    async def _async_update_data(self) -> Snapshot:
        try:
            return await self.hass.async_add_executor_job(self.client.status)
        except ChargerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ChargerError as err:
            raise UpdateFailed(str(err)) from err
