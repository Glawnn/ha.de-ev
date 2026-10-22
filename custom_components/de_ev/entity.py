"""Shared entity helpers for the Dé EV Charger integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN
from .coordinator import DeEvCoordinator


class DeEvEntity(CoordinatorEntity[DeEvCoordinator]):
    """Base entity for a charger."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DeEvCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        device_id = str(entry.data[CONF_DEVICE_ID])
        snapshot = coordinator.data
        charger_info = snapshot.charger_info or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.title,
            manufacturer="Tuya",
            model=snapshot.profile,
            sw_version=charger_info.get("fv"),
        )
