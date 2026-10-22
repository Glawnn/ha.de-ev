"""Frontend resources for the Dé EV Charger integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "de-ev-charger-card.js"
FRONTEND_DIR = Path(__file__).parent / "frontend"
FRONTEND_URL = f"/{DOMAIN}/frontend"
DATA_STATIC_PATH_REGISTERED = f"{DOMAIN}_frontend_static_path_registered"
DATA_MODULE_REGISTERED = f"{DOMAIN}_frontend_module_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the bundled Lovelace card once."""
    if hass.http is None:
        LOGGER.debug("HTTP is not available, skipping frontend card registration")
        return

    if not hass.data.get(DATA_STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL, str(FRONTEND_DIR), cache_headers=False)]
        )
        hass.data[DATA_STATIC_PATH_REGISTERED] = True

    if hass.data.get(DATA_MODULE_REGISTERED):
        return
    if DATA_EXTRA_MODULE_URL not in hass.data:
        LOGGER.debug("Frontend is not loaded, card module URL not registered")
        return

    card_path = FRONTEND_DIR / CARD_FILENAME
    try:
        cache_buster = int(card_path.stat().st_mtime)
    except OSError:
        LOGGER.warning("Frontend card file is missing: %s", card_path)
        return

    add_extra_js_url(
        hass,
        f"{FRONTEND_URL}/{CARD_FILENAME}?v={VERSION}-{cache_buster}",
    )
    hass.data[DATA_MODULE_REGISTERED] = True
