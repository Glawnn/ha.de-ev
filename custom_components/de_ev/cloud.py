"""Tuya Cloud device discovery."""

from __future__ import annotations

from typing import Any

import tinytuya

REGIONS = {"eu", "us", "cn", "in"}


class CloudError(RuntimeError):
    """Generic Tuya Cloud error."""


class CloudAuthError(CloudError):
    """Tuya Cloud rejected the credentials or project permissions."""


class CloudNoDevices(CloudError):
    """The Tuya project has no linked devices."""


def _fetch(
    region: str,
    api_key: str,
    api_secret: str,
    *,
    new_sign_algorithm: bool,
) -> Any:
    cloud = tinytuya.Cloud(
        apiRegion=region,
        apiKey=api_key,
        apiSecret=api_secret,
        new_sign_algorithm=new_sign_algorithm,
    )
    return cloud.getdevices(verbose=False)


def _error_message(result: dict[str, Any]) -> str:
    return f"{result.get('Error', 'unknown error')} (code {result.get('Err', '?')})"


def list_devices(region: str, api_key: str, api_secret: str) -> list[dict[str, Any]]:
    """Return the devices visible to a Tuya Cloud project."""
    if region not in REGIONS:
        raise CloudError(f"Invalid Tuya region: {region}")
    if not api_key.strip() or not api_secret.strip():
        raise CloudAuthError("Access ID and Access Secret are required.")

    key = api_key.strip()
    secret = api_secret.strip()

    result = _fetch(region, key, secret, new_sign_algorithm=True)
    if isinstance(result, dict) and "Error" in result:
        retry = _fetch(region, key, secret, new_sign_algorithm=False)
        if isinstance(retry, dict) and "Error" in retry:
            raise CloudAuthError(
                "Tuya Cloud rejected the request: "
                f"{_error_message(retry)}. Check that the Smart Home Basic "
                "Service API is authorized and that the Smart Life account is "
                "linked to the project."
            )
        result = retry

    if isinstance(result, dict):
        if "Error" in result:
            raise CloudAuthError(f"Tuya Cloud: {_error_message(result)}")
        result = result.get("result") or result.get("devices") or []
    if not isinstance(result, list):
        raise CloudError("Unexpected Tuya Cloud response.")

    devices: list[dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        device_id = item.get("id") or item.get("devId") or ""
        if not device_id:
            continue
        devices.append(
            {
                "id": device_id,
                "name": item.get("name") or item.get("customName") or device_id,
                "local_key": (
                    item.get("local_key")
                    or item.get("localKey")
                    or item.get("key")
                    or ""
                ),
                "ip": item.get("ip") or "",
                "category": item.get("category") or "",
                "product_name": item.get("product_name")
                or item.get("productName")
                or "",
                "online": item.get("online") if "online" in item else None,
            }
        )

    if not devices:
        raise CloudNoDevices("No devices are linked to this Tuya project.")

    devices.sort(
        key=lambda device: (device["online"] is not True, device["name"].lower())
    )
    return devices
