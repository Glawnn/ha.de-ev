"""Tests for the bundled Lovelace card registration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.de_ev.frontend_resources import (
    CARD_FILENAME,
    DATA_MODULE_REGISTERED,
    DATA_STATIC_PATH_REGISTERED,
    FRONTEND_DIR,
    async_register_frontend,
)


async def test_frontend_static_path_is_registered_once(
    hass: HomeAssistant,
) -> None:
    """The card directory is served and registered only once."""
    assert await async_setup_component(hass, "http", {})
    assert (FRONTEND_DIR / CARD_FILENAME).is_file()

    await async_register_frontend(hass)
    await async_register_frontend(hass)

    assert hass.data[DATA_STATIC_PATH_REGISTERED] is True
    assert DATA_MODULE_REGISTERED not in hass.data
