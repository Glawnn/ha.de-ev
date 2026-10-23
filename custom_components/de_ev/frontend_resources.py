"""Frontend resources for the Dé EV Charger integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "de-ev-charger-card.js"
EDITOR_FILENAME = "de-ev-charger-card-editor.js"
FRONTEND_DIR = Path(__file__).parent / "frontend"
FRONTEND_URL = f"/{DOMAIN}/frontend"
DATA_STATIC_PATH_REGISTERED = f"{DOMAIN}_frontend_static_path_registered"
DATA_MODULE_REGISTERED = f"{DOMAIN}_frontend_module_registered"
DATA_EDITOR_REGISTERED = f"{DOMAIN}_frontend_editor_registered"


async def _card_url(hass: HomeAssistant) -> str | None:
    card_path = FRONTEND_DIR / CARD_FILENAME
    try:
        cache_buster = int(card_path.stat().st_mtime)
    except OSError:
        _LOGGER.warning("Frontend card file is missing: %s", card_path)
        return None
    return f"{FRONTEND_URL}/{CARD_FILENAME}?v={cache_buster}"


async def _editor_url(hass: HomeAssistant) -> str | None:
    editor_path = FRONTEND_DIR / EDITOR_FILENAME
    try:
        cache_buster = int(editor_path.stat().st_mtime)
    except OSError:
        _LOGGER.warning("Frontend editor file is missing: %s", editor_path)
        return None
    return f"{FRONTEND_URL}/{EDITOR_FILENAME}?v={cache_buster}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the bundled Lovelace card and its editor once."""
    if hass.http is None:
        _LOGGER.debug("HTTP is not available; skipping frontend registration")
        return

    if not hass.data.get(DATA_STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[DATA_STATIC_PATH_REGISTERED] = True

    if hass.data.get(DATA_MODULE_REGISTERED) and hass.data.get(DATA_EDITOR_REGISTERED):
        return

    if DATA_EXTRA_MODULE_URL not in hass.data:
        _LOGGER.debug("Frontend is not loaded; card module URL not registered")
        return

    card_url = await _card_url(hass)
    if card_url:
        add_extra_js_url(hass, card_url)
        hass.data[DATA_MODULE_REGISTERED] = True

    editor_url = await _editor_url(hass)
    if editor_url:
        add_extra_js_url(hass, editor_url)
        hass.data[DATA_EDITOR_REGISTERED] = True
