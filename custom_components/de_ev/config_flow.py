"""Config flow for the Dé EV Charger integration."""

from __future__ import annotations

import asyncio
import ipaddress
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
from .cloud import CloudAuthError, CloudError, CloudNoDevices, get_device, list_devices
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
LOCAL_VALIDATION_TIMEOUT = 45

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
        LOGGER.info(
            "Testing charger %s at %s with Tuya protocol %s",
            device_id,
            host,
            version,
        )
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
            LOGGER.info(
                "Charger %s answered at %s with protocol %s",
                device_id,
                host,
                version,
            )
            return version, snapshot
        except (ChargerBusy, ChargerUnreachable) as err:
            LOGGER.warning("Charger %s at %s: %s", device_id, host, err)
            raise
        except ChargerAuthError as err:
            LOGGER.warning(
                "Charger %s at %s rejected the local key with protocol %s",
                device_id,
                host,
                version,
            )
            last_error = err
        except ChargerError as err:
            LOGGER.warning(
                "Charger %s at %s failed with protocol %s: %s",
                device_id,
                host,
                version,
                err,
            )
            last_error = err
        finally:
            task = asyncio.current_task()
            if task is not None and task.cancelling():
                # A stuck socket must not block the flow timeout: close later.
                async def _close_later(target: ChargerClient = client) -> None:
                    await hass.async_add_executor_job(target.close)

                hass.async_create_task(_close_later(), eager_start=False)
            else:
                await hass.async_add_executor_job(client.close)

    raise last_error or ChargerError("Unable to connect to the charger.")


def _probe_host(host: str, device_id: str, local_key: str) -> bool:
    """Return True when the host accepts this device ID and local key."""
    for version in PROTOCOLS:
        client = ChargerClient(
            ChargerSettings(
                host=host,
                device_id=device_id,
                local_key=local_key,
                version=version,
            )
        )
        try:
            client.connect()
            return True
        except (ChargerBusy, ChargerUnreachable):
            return False
        except ChargerError:
            continue
        finally:
            client.close()
    return False


class DeEvConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Dé EV Charger configuration flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._cloud_data: dict[str, str] = {}
        self._devices: dict[str, dict[str, Any]] = {}
        self._selected: dict[str, Any] = {}
        self._defaults: dict[str, Any] = {}
        self._cloud_task: asyncio.Task[list[dict[str, Any]]] | None = None
        self._cloud_error: str | None = None
        self._discover_task: asyncio.Task[str] | None = None
        self._local_task: asyncio.Task[tuple[str, Snapshot]] | None = None
        self._local_result: tuple[str, Snapshot] | None = None
        self._local_error: str | None = None
        self._local_input: dict[str, Any] = {}

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

    async def async_step_cloud_done(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show the cloud form after the progress step (distinct step id)."""
        return await self.async_step_cloud()

    async def _async_list_cloud_devices(self) -> list[dict[str, Any]]:
        """Fetch the devices of the Tuya project."""
        LOGGER.info(
            "Fetching Tuya Cloud devices (region %s)",
            self._cloud_data[CONF_REGION],
        )
        return await asyncio.wait_for(
            self.hass.async_add_executor_job(
                list_devices,
                self._cloud_data[CONF_REGION],
                self._cloud_data[CONF_ACCESS_ID],
                self._cloud_data[CONF_ACCESS_SECRET],
            ),
            timeout=45,
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Collect Tuya Cloud credentials and list devices."""
        errors: dict[str, str] = {}

        if self._cloud_error is not None:
            errors["base"] = self._cloud_error
            self._cloud_error = None

        if user_input:
            self._cloud_data = {
                CONF_REGION: str(user_input[CONF_REGION]),
                CONF_ACCESS_ID: str(user_input[CONF_ACCESS_ID]).strip(),
                CONF_ACCESS_SECRET: str(user_input[CONF_ACCESS_SECRET]).strip(),
            }
            self._cloud_task = self.hass.async_create_task(
                self._async_list_cloud_devices(), eager_start=False
            )

        if self._cloud_task is not None:
            if not self._cloud_task.done():
                return self.async_show_progress(
                    step_id="cloud",
                    progress_action="cloud_devices",
                    progress_task=self._cloud_task,
                )
            task, self._cloud_task = self._cloud_task, None
            try:
                devices = task.result()
            except TimeoutError:
                LOGGER.warning("Tuya Cloud did not answer within 45 seconds")
                self._cloud_error = "cloud_timeout"
            except CloudAuthError:
                LOGGER.warning("Tuya Cloud rejected the provided credentials")
                self._cloud_error = "cloud_auth_failed"
            except CloudNoDevices:
                LOGGER.warning("Tuya Cloud project has no linked devices")
                self._cloud_error = "cloud_no_devices"
            except CloudError:
                LOGGER.warning("Unexpected Tuya Cloud error", exc_info=True)
                self._cloud_error = "cloud_error"
            except Exception:
                LOGGER.exception("Unexpected Tuya Cloud error")
                self._cloud_error = "cloud_error"
            else:
                self._devices = {device["id"]: device for device in devices}
                return self.async_show_progress_done(
                    next_step_id="cloud_device"
                )
            return self.async_show_progress_done(next_step_id="cloud_done")

        return self.async_show_form(
            step_id="cloud",
            data_schema=self._cloud_schema(self._cloud_data),
            errors=errors,
        )

    def _device_label(self, device_id: str, device: dict[str, Any]) -> str:
        """Build a readable device label, including its online state."""
        label = f"{device['name']} ({device_id})"
        french = self.hass.config.language.startswith("fr")
        if device.get("online") is True:
            label += " - en ligne" if french else " - online"
        elif device.get("online") is False:
            label += " - hors ligne" if french else " - offline"
        return label

    async def _async_prepare_device(self, device_id: str) -> str:
        """Read the device detail and try to locate it on the LAN."""
        try:
            details = await asyncio.wait_for(
                self.hass.async_add_executor_job(
                    get_device,
                    self._cloud_data[CONF_REGION],
                    self._cloud_data[CONF_ACCESS_ID],
                    self._cloud_data[CONF_ACCESS_SECRET],
                    device_id,
                ),
                timeout=20,
            )
        except TimeoutError:
            LOGGER.warning("Tuya Cloud device detail timed out for %s", device_id)
            details = {}
        except Exception:
            LOGGER.exception("Unexpected Tuya Cloud device detail error")
            details = {}

        if details:
            self._selected.update(details)
            if details.get("ip"):
                self._defaults[CONF_HOST] = str(details["ip"])
            if details.get("local_key"):
                self._defaults[CONF_LOCAL_KEY] = str(details["local_key"])
            if details.get("name"):
                self._defaults[CONF_NAME] = str(details["name"])

        if self._defaults.get(CONF_HOST):
            return str(self._defaults[CONF_HOST])

        host = await self._discover_host(
            device_id,
            str(self._defaults.get(CONF_LOCAL_KEY) or ""),
        )
        self._defaults[CONF_HOST] = host
        return host

    async def async_step_cloud_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the charger among the devices of the Tuya account."""
        options = [
            {"value": device_id, "label": self._device_label(device_id, device)}
            for device_id, device in self._devices.items()
        ]

        if user_input:
            device_id = str(user_input[CONF_DEVICE_ID])
            device = self._devices.get(device_id)
            if device is None:
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
                    errors={"base": "unknown"},
                )
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

            self._discover_task = self.hass.async_create_task(
                self._async_prepare_device(device_id), eager_start=False
            )

        if self._discover_task is not None:
            if not self._discover_task.done():
                return self.async_show_progress(
                    step_id="cloud_device",
                    progress_action="identify_charger",
                    progress_task=self._discover_task,
                )
            task, self._discover_task = self._discover_task, None
            try:
                host = task.result()
            except Exception:
                LOGGER.exception("Unexpected error while locating the charger")
                host = ""
            self._defaults[CONF_HOST] = host
            if host:
                return self.async_show_progress_done(next_step_id="local_done")
            return self.async_show_progress_done(next_step_id="host")

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
        """Find the LAN address of a known Tuya device."""
        try:
            devices = await self.hass.async_add_executor_job(scan_udp, 8)
        except Exception:
            LOGGER.exception("Tuya UDP discovery failed")
            devices = []

        LOGGER.debug("Tuya UDP discovery found %d device(s)", len(devices))
        for device in devices:
            if device.get("device_id") == device_id and device.get("ip"):
                LOGGER.debug(
                    "Charger %s announced itself at %s", device_id, device["ip"]
                )
                return str(device["ip"])

        if not local_key:
            LOGGER.debug("No local key available, skipping the LAN scan")
            return ""

        try:
            addresses = await scan_lan(port=6668, timeout=0.5, concurrency=96)
        except Exception:
            LOGGER.exception("LAN scan failed")
            return ""

        LOGGER.debug(
            "LAN scan found %d host(s) with port 6668 open", len(addresses)
        )
        if not addresses:
            return ""

        host = await self._probe_hosts(addresses, device_id, local_key)
        if host:
            LOGGER.debug("Charger %s authenticated at %s", device_id, host)
        else:
            LOGGER.debug(
                "No host among %d candidate(s) accepted device %s",
                len(addresses),
                device_id,
            )
        return host

    async def _probe_hosts(
        self, addresses: list[str], device_id: str, local_key: str
    ) -> str:
        """Probe candidate hosts in parallel; the right one accepts the key."""
        semaphore = asyncio.Semaphore(8)

        async def probe(address: str) -> str:
            async with semaphore:
                try:
                    if await self.hass.async_add_executor_job(
                        _probe_host, address, device_id, local_key
                    ):
                        return address
                except Exception:
                    LOGGER.debug("Probe failed for %s", address, exc_info=True)
                return ""

        tasks = [
            self.hass.async_create_task(probe(address), eager_start=False)
            for address in addresses
        ]
        for finished in asyncio.as_completed(tasks):
            address = await finished
            if address:
                for task in tasks:
                    task.cancel()
                return address
        return ""

    async def async_step_host(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for the local IP when it cannot be discovered."""
        errors: dict[str, str] = {}

        if user_input:
            host = str(user_input[CONF_HOST]).strip()
            if not host:
                errors["base"] = "missing_config"
            else:
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    errors["base"] = "invalid_host"
                else:
                    self._defaults[CONF_HOST] = host
                    return await self.async_step_local()

        return self.async_show_form(
            step_id="host",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self._defaults.get(CONF_HOST, ""),
                    ): TextSelector()
                }
            ),
            errors=errors,
            description_placeholders={
                "name": str(
                    self._selected.get("name")
                    or self._defaults.get(CONF_NAME)
                    or NAME
                )
            },
        )

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

    async def _async_validate_local(self) -> tuple[str, Snapshot]:
        """Validate the local connection with a hard deadline."""
        host = str(self._local_input[CONF_HOST]).strip()
        device_id = str(self._local_input[CONF_DEVICE_ID]).strip()
        LOGGER.info("Starting local validation of charger %s at %s", device_id, host)
        try:
            result = await asyncio.wait_for(
                _validate_connection(
                    self.hass,
                    host,
                    device_id,
                    str(self._local_input[CONF_LOCAL_KEY]).strip(),
                    str(self._local_input[CONF_PROTOCOL]),
                ),
                timeout=LOCAL_VALIDATION_TIMEOUT,
            )
        except TimeoutError:
            LOGGER.warning(
                "Local validation of charger %s at %s timed out after %ss",
                device_id,
                host,
                LOCAL_VALIDATION_TIMEOUT,
            )
            raise
        LOGGER.info(
            "Local validation succeeded for charger %s at %s", device_id, host
        )
        return result

    async def async_step_local_done(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Continue the local step after the progress step (distinct step id)."""
        return await self.async_step_local()

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate the local connection and create the entry."""
        errors: dict[str, str] = {}

        if user_input:
            self._local_input = dict(user_input)
            self._local_result = None
            self._local_error = None
            host = str(user_input[CONF_HOST]).strip()
            device_id = str(user_input[CONF_DEVICE_ID]).strip()
            local_key = str(user_input[CONF_LOCAL_KEY]).strip()
            if not host or not device_id or not local_key:
                errors["base"] = "missing_config"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                self._local_task = self.hass.async_create_task(
                    self._async_validate_local(), eager_start=False
                )

        if self._local_task is not None:
            if not self._local_task.done():
                return self.async_show_progress(
                    step_id="local",
                    progress_action="test_connection",
                    progress_task=self._local_task,
                    description_placeholders={
                        "host": str(self._local_input.get(CONF_HOST, ""))
                    },
                )
            task, self._local_task = self._local_task, None
            try:
                self._local_result = task.result()
            except TimeoutError:
                self._local_error = "timeout"
            except ChargerBusy:
                self._local_error = "port_busy"
            except ChargerUnreachable:
                self._local_error = "cannot_connect"
            except ChargerAuthError:
                self._local_error = "invalid_auth"
            except ChargerError:
                self._local_error = "cannot_connect"
            except Exception:
                LOGGER.exception("Unexpected charger connection error")
                self._local_error = "unknown"
            return self.async_show_progress_done(next_step_id="local_done")

        if self._local_error is not None:
            errors["base"] = self._local_error
            self._local_error = None

        if self._local_result is not None:
            version, snapshot = self._local_result
            self._local_result = None
            if snapshot.profile == "unknown":
                errors["base"] = "unsupported_device"
            else:
                data = self._local_input
                device_id = str(data[CONF_DEVICE_ID]).strip()
                return self.async_create_entry(
                    title=str(data.get(CONF_NAME) or NAME).strip() or NAME,
                    data={
                        CONF_REGION: self._cloud_data.get(CONF_REGION, ""),
                        CONF_ACCESS_ID: self._cloud_data.get(
                            CONF_ACCESS_ID, ""
                        ),
                        CONF_ACCESS_SECRET: self._cloud_data.get(
                            CONF_ACCESS_SECRET, ""
                        ),
                        CONF_DEVICE_ID: device_id,
                        CONF_HOST: str(data[CONF_HOST]).strip(),
                        CONF_LOCAL_KEY: str(data[CONF_LOCAL_KEY]).strip(),
                        CONF_PROTOCOL: version,
                        CONF_AREA_ID: str(data.get(CONF_AREA_ID) or ""),
                    },
                )

        return self.async_show_form(
            step_id="local",
            data_schema=self._local_schema(
                self._local_input if self._local_input else self._defaults
            ),
            errors=errors,
            description_placeholders={
                "host": str(
                    self._local_input.get(CONF_HOST)
                    or self._defaults.get(CONF_HOST)
                    or ""
                )
            },
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
