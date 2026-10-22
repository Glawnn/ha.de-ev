"""Local Tuya device discovery."""

from __future__ import annotations

import asyncio
import contextlib
import io
import ipaddress
import socket
from typing import Any

import tinytuya


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "ip": raw.get("ip") or raw.get("IP"),
        "device_id": raw.get("gwId") or raw.get("id") or raw.get("devId"),
        "version": str(raw.get("version") or ""),
        "product_key": raw.get("productKey") or "",
        "mac": raw.get("mac") or "",
    }


def scan_udp(timeout: int = 8) -> list[dict[str, Any]]:
    """Listen for Tuya UDP announcements."""
    devices: list[dict[str, Any]] = []

    with contextlib.redirect_stdout(io.StringIO()):
        try:
            found = tinytuya.deviceScan(
                verbose=False,
                maxretry=timeout,
                color=False,
                poll=False,
            )
        except Exception:
            found = {}

    if isinstance(found, dict):
        items = list(found.values())
    elif isinstance(found, list):
        items = found
    else:
        items = []

    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        entry = _normalize(item)
        key = entry["device_id"] or entry["ip"] or ""
        if not key or key in seen:
            continue
        seen.add(key)
        devices.append(entry)

    devices.sort(key=lambda device: (device["ip"] or "", device["device_id"] or ""))
    return devices


def local_ipv4() -> str:
    """Return the local IPv4 address of the default route."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return ""
    finally:
        sock.close()


def local_networks() -> list[ipaddress.IPv4Network]:
    """Return the private IPv4 networks attached to this host."""
    networks: set[ipaddress.IPv4Network] = set()
    try:
        import psutil  # noqa: PLC0415 - optional, bundled with Home Assistant
    except ImportError:
        psutil = None

    if psutil is not None:
        for addresses in psutil.net_if_addrs().values():
            for address in addresses:
                if address.family != socket.AF_INET or not address.netmask:
                    continue
                try:
                    network = ipaddress.ip_network(
                        f"{address.address}/{address.netmask}", strict=False
                    )
                except ValueError:
                    continue
                if (
                    network.version == 4
                    and network.is_private
                    and not network.is_loopback
                    and not network.is_link_local
                ):
                    prefix = 24 if network.prefixlen < 24 else network.prefixlen
                    networks.add(
                        ipaddress.ip_network(
                            f"{address.address}/{prefix}", strict=False
                        )
                    )

    address = local_ipv4()
    if address and not address.startswith("127."):
        with contextlib.suppress(ValueError):
            networks.add(ipaddress.ip_network(address + "/24", strict=False))

    return sorted(networks, key=lambda network: str(network))


async def _port_open(
    host: str,
    port: int,
    timeout: float,
    semaphore: asyncio.Semaphore,
) -> str | None:
    async with semaphore:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
        except (OSError, TimeoutError):
            return None
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()
        return host


async def scan_lan(
    port: int = 6668,
    timeout: float = 0.7,
    concurrency: int = 96,
) -> list[str]:
    """Scan the local IPv4 networks for open Tuya TCP ports."""
    networks = local_networks()
    if not networks:
        return []
    hosts = {host for network in networks for host in network.hosts()}
    semaphore = asyncio.Semaphore(concurrency)
    results = await asyncio.gather(
        *(_port_open(str(host), port, timeout, semaphore) for host in hosts)
    )
    found = [item for item in results if item]
    return sorted(found, key=lambda ip: tuple(int(part) for part in ip.split(".")))
