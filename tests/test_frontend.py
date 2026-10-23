"""Tests for the bundled Lovelace card."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.de_ev.const import DOMAIN
from custom_components.de_ev.frontend_resources import (
    CARD_FILENAME,
    DATA_MODULE_REGISTERED,
    DATA_STATIC_PATH_REGISTERED,
    FRONTEND_DIR,
    async_register_frontend,
)


async def test_static_path_is_registered_once(hass: HomeAssistant) -> None:
    """The card directory is served once."""
    assert await async_setup_component(hass, "http", {})
    assert (FRONTEND_DIR / CARD_FILENAME).is_file()

    await async_register_frontend(hass)
    await async_register_frontend(hass)

    assert hass.data[DATA_STATIC_PATH_REGISTERED] is True
    assert DATA_MODULE_REGISTERED not in hass.data


async def test_module_is_registered_once(hass: HomeAssistant) -> None:
    """The card module is injected once when the frontend is available."""
    assert await async_setup_component(hass, "http", {})
    hass.data[DATA_EXTRA_MODULE_URL] = object()

    with patch(
        "custom_components.de_ev.frontend_resources.add_extra_js_url"
    ) as add_extra_js_url:
        await async_register_frontend(hass)
        await async_register_frontend(hass)

    add_extra_js_url.assert_called_once()
    url = add_extra_js_url.call_args.args[1]
    assert url.startswith(f"/{DOMAIN}/frontend/{CARD_FILENAME}?v=")
    assert hass.data[DATA_MODULE_REGISTERED] is True


async def test_missing_card_file_is_skipped(hass: HomeAssistant, tmp_path) -> None:
    """A missing card file does not break integration setup."""
    assert await async_setup_component(hass, "http", {})
    hass.data[DATA_EXTRA_MODULE_URL] = object()

    with (
        patch("custom_components.de_ev.frontend_resources.FRONTEND_DIR", tmp_path),
        patch(
            "custom_components.de_ev.frontend_resources.add_extra_js_url"
        ) as add_extra_js_url,
    ):
        await async_register_frontend(hass)

    add_extra_js_url.assert_not_called()
    assert DATA_MODULE_REGISTERED not in hass.data


async def test_setup_registers_frontend(hass: HomeAssistant) -> None:
    """The integration setup hook registers the frontend."""
    with patch("custom_components.de_ev.async_register_frontend") as register:
        assert await async_setup_component(hass, DOMAIN, {})

    register.assert_awaited_once()
