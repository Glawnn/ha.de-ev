"""Diagnostics support for the Dé EV Charger integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import DeEvConfigEntry
from .const import CONF_ACCESS_SECRET, CONF_LOCAL_KEY

REDACTED = "**REDACTED**"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: DeEvConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics with secrets redacted."""
    data = dict(entry.data)
    for key in (CONF_ACCESS_SECRET, CONF_LOCAL_KEY):
        if key in data:
            data[key] = REDACTED

    coordinator = entry.runtime_data.coordinator if entry.runtime_data else None
    snapshot = coordinator.data.to_dict() if coordinator and coordinator.data else None
    return {
        "entry": {
            "title": entry.title,
            "data": data,
            "options": dict(entry.options),
        },
        "snapshot": snapshot,
    }
