"""Tests for the bundled Lovelace card."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.de_ev.const import DOMAIN
from custom_components.de_ev.frontend_resources import (
    CARD_FILENAME,
    DATA_EDITOR_REGISTERED,
    DATA_MODULE_REGISTERED,
    DATA_STATIC_PATH_REGISTERED,
    EDITOR_FILENAME,
    FRONTEND_DIR,
    async_register_frontend,
)


async def test_registration_is_skipped_without_http(hass: HomeAssistant) -> None:
    """Frontend registration does nothing when the HTTP stack is unavailable."""
    hass.data[DATA_EXTRA_MODULE_URL] = object()

    assert await async_register_frontend(hass) is False

    assert DATA_STATIC_PATH_REGISTERED not in hass.data
    assert DATA_MODULE_REGISTERED not in hass.data
    assert DATA_EDITOR_REGISTERED not in hass.data


async def test_static_path_is_registered_once(hass: HomeAssistant) -> None:
    """The card directory is served once."""
    assert await async_setup_component(hass, "http", {})
    assert (FRONTEND_DIR / CARD_FILENAME).is_file()

    assert await async_register_frontend(hass) is False
    assert await async_register_frontend(hass) is False

    assert hass.data[DATA_STATIC_PATH_REGISTERED] is True
    assert DATA_MODULE_REGISTERED not in hass.data


async def test_module_and_editor_are_registered_once(hass: HomeAssistant) -> None:
    """The card module and editor are injected once."""
    assert await async_setup_component(hass, "http", {})
    hass.data[DATA_EXTRA_MODULE_URL] = object()

    with patch(
        "custom_components.de_ev.frontend_resources.add_extra_js_url"
    ) as add_extra_js_url:
        assert await async_register_frontend(hass) is True
        assert await async_register_frontend(hass) is True

    assert add_extra_js_url.call_count == 2
    card_url = add_extra_js_url.call_args_list[0].args[1]
    editor_url = add_extra_js_url.call_args_list[1].args[1]
    assert card_url.startswith(f"/{DOMAIN}/frontend/{CARD_FILENAME}?v=")
    assert editor_url.startswith(f"/{DOMAIN}/frontend/{EDITOR_FILENAME}?v=")
    assert hass.data[DATA_MODULE_REGISTERED] is True
    assert hass.data[DATA_EDITOR_REGISTERED] is True


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
        assert await async_register_frontend(hass) is False

    add_extra_js_url.assert_not_called()
    assert DATA_MODULE_REGISTERED not in hass.data
    assert DATA_EDITOR_REGISTERED not in hass.data


async def test_setup_registers_frontend(hass: HomeAssistant) -> None:
    """The integration setup hook registers the frontend."""
    with patch("custom_components.de_ev.async_register_frontend") as register:
        assert await async_setup_component(hass, DOMAIN, {})

    register.assert_awaited_once()


async def test_setup_defers_frontend_until_started(hass: HomeAssistant) -> None:
    """Frontend registration is retried once Home Assistant has started."""
    register = AsyncMock(return_value=False)
    with (
        patch("custom_components.de_ev.async_register_frontend", register),
        patch("custom_components.de_ev.async_at_started") as at_started,
    ):
        assert await async_setup_component(hass, DOMAIN, {})

    register.assert_awaited_once()
    at_started.assert_called_once_with(hass, register)
