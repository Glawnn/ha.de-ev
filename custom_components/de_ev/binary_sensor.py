"""Binary sensor platform for the Dé EV Charger integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeEvConfigEntry
from .coordinator import DeEvCoordinator
from .entity import DeEvEntity
from .profiles import Snapshot


@dataclass(frozen=True, kw_only=True)
class DeEvBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a charger binary sensor."""

    value_fn: Callable[[Snapshot], bool]


BINARY_SENSORS: tuple[DeEvBinarySensorDescription, ...] = (
    DeEvBinarySensorDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda data: data.charging,
    ),
    DeEvBinarySensorDescription(
        key="plugged",
        translation_key="plugged",
        device_class=BinarySensorDeviceClass.PLUG,
        value_fn=lambda data: data.plugged,
    ),
    DeEvBinarySensorDescription(
        key="fault",
        translation_key="fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.status == "fault",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeEvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up charger binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        DeEvBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class DeEvBinarySensor(DeEvEntity, BinarySensorEntity):
    """A binary sensor backed by the charger coordinator."""

    entity_description: DeEvBinarySensorDescription

    def __init__(
        self,
        coordinator: DeEvCoordinator,
        description: DeEvBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    @property
    def is_on(self) -> bool:
        """Return the current binary state."""
        return self.entity_description.value_fn(self.coordinator.data)
