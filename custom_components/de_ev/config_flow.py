"""Config flow for the Dé EV Charger integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    AreaSelector,
    AreaSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .charger import (
    ChargerAuthError,
    ChargerBusy,
    ChargerClient,
    ChargerError,
    ChargerSettings,
    ChargerUnreachable,
)
from .cloud import CloudAuthError, CloudError, CloudNoDevices, list_devices
from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_AREA_ID,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_MAX_CURRENT,
    CONF_MIN_CURRENT,
    CONF_PROTOCOL,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAX_CURRENT,
    DEFAULT_MIN_CURRENT,
    DEFAULT_PROTOCOL,
    DEFAULT_REGION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_CURRENT_LIMIT,
    MAX_SCAN_INTERVAL,
    MIN_CURRENT_LIMIT,
    MIN_SCAN_INTERVAL,
    NAME,
    PROTOCOL_AUTO,
    PROTOCOLS,
    REGIONS,
)
from .discovery import scan_lan, scan_udp
from .profiles import Snapshot, decode

LOGGER = logging.getLogger(__name__)

REGION_LABELS = {
    "eu": "Europe",
    "us": "Americas",
    "cn": "China",
    "in": "India",
}
PROTOCOL_LABELS = {
    PROTOCOL_AUTO: "Auto",
    "3.5": "3.5",
    "3.4": "3.4",
    "3.3": "3.3",
}


def _protocol_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                {"value": value, "label": PROTOCOL_LABELS[value]}
                for value in (PROTOCOL_AUTO, *PROTOCOLS)
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _region_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                {"value": value, "label": REGION_LABELS[value]} for value in REGIONS
            ],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _secret_selector() -> TextSelector:
    return TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


async def _validate_connection(
    hass: HomeAssistant,
    host: str,
    device_id: str,
    local_key: str,
    protocol: str,
) -> tuple[str, Snapshot]:
    versions = PROTOCOLS if protocol == PROTOCOL_AUTO else (protocol,)
    last_error: ChargerError | None = None

    for version in versions:
        client = ChargerClient(
            ChargerSettings(
                host=host,
                device_id=device_id,
                local_key=local_key,
                version=version,
            )
        )
        try:
            dps = await hass.async_add_executor_job(client.connect)
            snapshot = decode(dps, max_current=DEFAULT_MAX_CURRENT)
            return version, snapshot
        except (ChargerBusy, ChargerUnreachable):
            raise
        except ChargerAuthError as err:
            last_error = err
        except ChargerError as err:
            last_error = err
        finally:
            await hass.async_add_executor_job(client.close)

    raise last_error or ChargerError("Unable to connect to the charger.")


def _probe_host(host: str, device_id: str, local_key: str) -> bool:
    client = ChargerClient(
        ChargerSettings(
            host=host,
            device_id=device_id,
            local_key=local_key,
            version=DEFAULT_PROTOCOL,
        )
    )
    try:
        client.connect()
        return True
    except ChargerError:
        return False
    finally:
        client.close()


class DeEvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Dé EV Charger configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud_data: dict[str, str] = {}
        self._devices: dict[str, dict[str, Any]] = {}
        self._selected: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose how to add the charger."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "local"],
        )

    def _cloud_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_REGION,
                    default=defaults.get(CONF_REGION, DEFAULT_REGION),
                ): _region_selector(),
                vol.Required(
                    CONF_ACCESS_ID,
                    default=defaults.get(CONF_ACCESS_ID, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_ACCESS_SECRET,
                    default=defaults.get(CONF_ACCESS_SECRET, ""),
                ): _secret_selector(),
            }
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect Tuya Cloud credentials and list devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._cloud_data = {
                CONF_REGION: str(user_input[CONF_REGION]),
                CONF_ACCESS_ID: str(user_input[CONF_ACCESS_ID]).strip(),
                CONF_ACCESS_SECRET: str(user_input[CONF_ACCESS_SECRET]).strip(),
            }
            try:
                devices = await asyncio.wait_for(
                    self.hass.async_add_executor_job(
                        list_devices,
                        self._cloud_data[CONF_REGION],
                        self._cloud_data[CONF_ACCESS_ID],
                        self._cloud_data[CONF_ACCESS_SECRET],
                    ),
                    timeout=45,
                )
            except TimeoutError:
                errors["base"] = "cloud_timeout"
            except CloudAuthError:
                errors["base"] = "cloud_auth_failed"
            except CloudNoDevices:
                errors["base"] = "cloud_no_devices"
            except CloudError:
                errors["base"] = "cloud_error"
            except Exception:
                LOGGER.exception("Unexpected Tuya Cloud error")
                errors["base"] = "cloud_error"
            else:
                self._devices = {device["id"]: device for device in devices}
                return await self.async_step_cloud_device()

        return self.async_show_form(
            step_id="cloud",
            data_schema=self._cloud_schema(self._cloud_data),
            errors=errors,
        )

    async def async_step_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the charger among the devices of the Tuya account."""
        options = []
        for device_id, device in self._devices.items():
            label = f"{device['name']} ({device_id})"
            if device.get("online") is True:
                label += " - online"
            elif device.get("online") is False:
                label += " - offline"
            options.append({"value": device_id, "label": label})

        if user_input is not None:
            device_id = str(user_input[CONF_DEVICE_ID])
            device = self._devices[device_id]
            self._selected = device
            self._defaults = {
                CONF_DEVICE_ID: device_id,
                CONF_HOST: str(device.get("ip") or ""),
                CONF_LOCAL_KEY: str(device.get("local_key") or ""),
                CONF_PROTOCOL: PROTOCOL_AUTO,
                CONF_NAME: str(device.get("name") or NAME),
            }

            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            if not self._defaults[CONF_HOST]:
                self._defaults[CONF_HOST] = await self._discover_host(
                    device_id,
                    self._defaults[CONF_LOCAL_KEY],
                )
            return await self.async_step_local()

        return self.async_show_form(
            step_id="cloud_device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def _discover_host(self, device_id: str, local_key: str) -> str:
        try:
            devices = await self.hass.async_add_executor_job(scan_udp, 8)
        except Exception:
            devices = []

        for device in devices:
            if device.get("device_id") == device_id and device.get("ip"):
                return str(device["ip"])

        if not local_key:
            return ""

        try:
            addresses = await scan_lan(port=6668, timeout=0.5, concurrency=96)
        except Exception:
            return ""

        for address in addresses[:24]:
            try:
                if await self.hass.async_add_executor_job(
                    _probe_host, address, device_id, local_key
                ):
                    return address
            except Exception:
                continue
        return ""

    def _local_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Optional(
                    CONF_NAME,
                    default=defaults.get(CONF_NAME, NAME),
                ): TextSelector(),
                vol.Required(
                    CONF_HOST,
                    default=defaults.get(CONF_HOST, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_DEVICE_ID,
                    default=defaults.get(CONF_DEVICE_ID, ""),
                ): TextSelector(),
                vol.Required(
                    CONF_LOCAL_KEY,
                    default=defaults.get(CONF_LOCAL_KEY, ""),
                ): _secret_selector(),
                vol.Required(
                    CONF_PROTOCOL,
                    default=defaults.get(CONF_PROTOCOL, PROTOCOL_AUTO),
                ): _protocol_selector(),
                vol.Optional(
                    CONF_AREA_ID,
                    default=defaults.get(CONF_AREA_ID, ""),
                ): AreaSelector(AreaSelectorConfig()),
            }
        )

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate the local connection and create the entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            device_id = str(user_input[CONF_DEVICE_ID]).strip()
            local_key = str(user_input[CONF_LOCAL_KEY]).strip()
            protocol = str(user_input[CONF_PROTOCOL])
            name = str(user_input.get(CONF_NAME) or NAME).strip()

            if not host or not device_id or not local_key:
                errors["base"] = "missing_config"
            else:
                try:
                    version, snapshot = await _validate_connection(
                        self.hass,
                        host,
                        device_id,
                        local_key,
                        protocol,
                    )
                except ChargerBusy:
                    errors["base"] = "port_busy"
                except ChargerUnreachable:
                    errors["base"] = "cannot_connect"
                except ChargerAuthError:
                    errors["base"] = "invalid_auth"
                except ChargerError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    LOGGER.exception("Unexpected charger connection error")
                    errors["base"] = "unknown"
                else:
                    if snapshot.profile == "unknown":
                        errors["base"] = "unsupported_device"
                    else:
                        await self.async_set_unique_id(device_id)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title=name or NAME,
                            data={
                                CONF_REGION: self._cloud_data.get(
                                    CONF_REGION, ""
                                ),
                                CONF_ACCESS_ID: self._cloud_data.get(
                                    CONF_ACCESS_ID, ""
                                ),
                                CONF_ACCESS_SECRET: self._cloud_data.get(
                                    CONF_ACCESS_SECRET, ""
                                ),
                                CONF_DEVICE_ID: device_id,
                                CONF_HOST: host,
                                CONF_LOCAL_KEY: local_key,
                                CONF_PROTOCOL: version,
                                CONF_AREA_ID: str(
                                    user_input.get(CONF_AREA_ID) or ""
                                ),
                            },
                        )

        return self.async_show_form(
            step_id="local",
            data_schema=self._local_schema(
                user_input if user_input is not None else self._defaults
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Handle a local key change."""
        self._defaults = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for a new local key and validate it."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            local_key = str(user_input[CONF_LOCAL_KEY]).strip()
            try:
                await _validate_connection(
                    self.hass,
                    str(entry.data[CONF_HOST]),
                    str(entry.data[CONF_DEVICE_ID]),
                    local_key,
                    str(entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)),
                )
            except ChargerBusy:
                errors["base"] = "port_busy"
            except ChargerUnreachable:
                errors["base"] = "cannot_connect"
            except (ChargerAuthError, ChargerError):
                errors["base"] = "invalid_auth"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data={**entry.data, CONF_LOCAL_KEY: local_key},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCAL_KEY): _secret_selector(),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Update the local connection settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            local_key = str(user_input[CONF_LOCAL_KEY]).strip()
            protocol = str(user_input[CONF_PROTOCOL])
            try:
                version, snapshot = await _validate_connection(
                    self.hass,
                    host,
                    str(entry.data[CONF_DEVICE_ID]),
                    local_key,
                    protocol,
                )
            except ChargerBusy:
                errors["base"] = "port_busy"
            except ChargerUnreachable:
                errors["base"] = "cannot_connect"
            except ChargerAuthError:
                errors["base"] = "invalid_auth"
            except ChargerError:
                errors["base"] = "cannot_connect"
            else:
                if snapshot.profile == "unknown":
                    errors["base"] = "unsupported_device"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data={
                            **entry.data,
                            CONF_HOST: host,
                            CONF_LOCAL_KEY: local_key,
                            CONF_PROTOCOL: version,
                        },
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=str(entry.data.get(CONF_HOST, "")),
                    ): TextSelector(),
                    vol.Required(
                        CONF_LOCAL_KEY,
                        default=str(entry.data.get(CONF_LOCAL_KEY, "")),
                    ): _secret_selector(),
                    vol.Required(
                        CONF_PROTOCOL,
                        default=str(
                            entry.data.get(CONF_PROTOCOL, DEFAULT_PROTOCOL)
                        ),
                    ): _protocol_selector(),
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return DeEvOptionsFlow()


class DeEvOptionsFlow(config_entries.OptionsFlow):
    """Configure polling and current limits."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                        ),
                    ),
                    vol.Required(
                        CONF_MIN_CURRENT,
                        default=options.get(
                            CONF_MIN_CURRENT, DEFAULT_MIN_CURRENT
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_CURRENT_LIMIT,
                            max=MAX_CURRENT_LIMIT,
                        ),
                    ),
                    vol.Required(
                        CONF_MAX_CURRENT,
                        default=options.get(
                            CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_CURRENT_LIMIT,
                            max=MAX_CURRENT_LIMIT,
                        ),
                    ),
                }
            ),
        )
