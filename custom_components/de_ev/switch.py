"""Switch platform for the Dé EV Charger integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeEvConfigEntry
from .charger import ChargerError
from .coordinator import DeEvCoordinator
from .entity import DeEvEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeEvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the charger switch."""
    async_add_entities([DeEvChargeSwitch(entry.runtime_data.coordinator)])


class DeEvChargeSwitch(DeEvEntity, SwitchEntity):
    """Start or stop a charging session."""

    _attr_translation_key = "charge_session"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: DeEvCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_charge_session"
        )

    @property
    def is_on(self) -> bool:
        """Return true when a charging session is active."""
        snapshot = self.coordinator.data
        if snapshot.do_charge is not None:
            return snapshot.do_charge
        return snapshot.charging

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start charging."""
        await self._set_charge(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop charging."""
        await self._set_charge(False)

    async def _set_charge(self, enabled: bool) -> None:
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_charge, enabled
            )
        except ChargerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
