"""Sensor platform for the Dé EV Charger integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DeEvConfigEntry
from .coordinator import DeEvCoordinator
from .entity import DeEvEntity
from .profiles import STATUS_OPTIONS, Snapshot


@dataclass(frozen=True, kw_only=True)
class DeEvSensorDescription(SensorEntityDescription):
    """Describes a charger sensor."""

    value_fn: Callable[[Snapshot], Any]


SENSORS: tuple[DeEvSensorDescription, ...] = (
    DeEvSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUS_OPTIONS,
        value_fn=lambda data: data.status,
    ),
    DeEvSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.power_w,
    ),
    DeEvSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.voltage_v,
    ),
    DeEvSensorDescription(
        key="current",
        translation_key="current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.current_a,
    ),
    DeEvSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.temperature_c,
    ),
    DeEvSensorDescription(
        key="energy_session",
        translation_key="energy_session",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda data: data.energy_kwh,
    ),
    DeEvSensorDescription(
        key="session_duration",
        translation_key="session_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.session_duration_s,
    ),
    DeEvSensorDescription(
        key="max_current",
        translation_key="max_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.max_current_a,
    ),
    DeEvSensorDescription(
        key="work_state",
        translation_key="work_state",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.work_state,
    ),
    DeEvSensorDescription(
        key="last_session_energy",
        translation_key="last_session_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (data.last_session or {}).get("energy_kwh"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DeEvConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up charger sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        DeEvSensor(coordinator, description) for description in SENSORS
    )


class DeEvSensor(DeEvEntity, SensorEntity):
    """A sensor backed by the charger coordinator."""

    entity_description: DeEvSensorDescription

    def __init__(
        self,
        coordinator: DeEvCoordinator,
        description: DeEvSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
