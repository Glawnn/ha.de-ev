"""Data coordinator for the Dé EV Charger integration."""

from __future__ import annotations

import logging
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
from .const import DOMAIN
from .profiles import Snapshot
from .recovery import async_get_recovery

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
        self._recovery = async_get_recovery(hass, entry.entry_id)

    async def _async_update_data(self) -> Snapshot:
        try:
            snapshot = await self.hass.async_add_executor_job(self.client.status)
        except ChargerAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ChargerUnreachable, ChargerBusy) as err:
            self._recovery.record_failure()
            raise UpdateFailed(str(err)) from err
        except ChargerError as err:
            raise UpdateFailed(str(err)) from err
        self._recovery.record_success()
        return snapshot
