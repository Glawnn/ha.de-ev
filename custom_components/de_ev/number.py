"""Number platform for the Dé EV Charger integration."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeEvConfigEntry
from .charger import ChargerError
from .const import DEFAULT_MIN_CURRENT
from .coordinator import DeEvCoordinator
from .entity import DeEvEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeEvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the charging current number."""
    async_add_entities([DeEvChargeCurrentNumber(entry.runtime_data.coordinator)])


class DeEvChargeCurrentNumber(DeEvEntity, NumberEntity):
    """Set the charging current setpoint."""

    _attr_translation_key = "charge_current"
    _attr_device_class = NumberDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_native_min_value = DEFAULT_MIN_CURRENT
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:current-ac"

    def __init__(self, coordinator: DeEvCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_charge_current"
        )

    @property
    def native_value(self) -> float | None:
        """Return the current setpoint."""
        return self.coordinator.data.current_target_a

    @property
    def native_max_value(self) -> float:
        """Return the charger hardware maximum."""
        snapshot = self.coordinator.data
        return max(float(snapshot.max_current_a), float(DEFAULT_MIN_CURRENT))

    async def async_set_native_value(self, value: float) -> None:
        """Set the charging current."""
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_current, int(value)
            )
        except ChargerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
