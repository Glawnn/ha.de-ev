"""Constants for the Dé EV Charger integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "de_ev"
NAME: Final = "Dé EV Charger"
VERSION: Final = "0.2.0"

CONF_REGION: Final = "region"
CONF_ACCESS_ID: Final = "access_id"
CONF_ACCESS_SECRET: Final = "access_secret"
CONF_DEVICE_ID: Final = "device_id"
CONF_HOST: Final = "host"
CONF_LOCAL_KEY: Final = "local_key"
CONF_PROTOCOL: Final = "protocol_version"
CONF_AREA_ID: Final = "area_id"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_MIN_CURRENT: Final = "min_current"
CONF_MAX_CURRENT: Final = "max_current"

REGIONS: Final = ("eu", "us", "cn", "in")
DEFAULT_REGION: Final = "eu"
PROTOCOLS: Final = ("3.5", "3.4", "3.3")
DEFAULT_PROTOCOL: Final = "3.5"
PROTOCOL_AUTO: Final = "auto"

DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 300
DEFAULT_MIN_CURRENT: Final = 6
DEFAULT_MAX_CURRENT: Final = 16
MIN_CURRENT_LIMIT: Final = 6
MAX_CURRENT_LIMIT: Final = 32
