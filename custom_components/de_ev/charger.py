"""Local Tuya charger client with serialized reads and writes."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any

import tinytuya

from .const import DEFAULT_MAX_CURRENT, DEFAULT_MIN_CURRENT, DEFAULT_PROTOCOL
from .profiles import Snapshot, charge_command, current_dp, decode


class ChargerError(RuntimeError):
    """Generic charger communication error."""


class ChargerBusy(ChargerError):
    """The local Tuya port is held by another client."""


class ChargerUnreachable(ChargerError):
    """The charger cannot be reached on the network."""


class ChargerAuthError(ChargerError):
    """The charger replied but the local key or protocol is invalid."""


@dataclass(slots=True)
class ChargerSettings:
    """Connection settings for a charger."""

    host: str
    device_id: str
    local_key: str
    version: str = DEFAULT_PROTOCOL
    min_current: int = DEFAULT_MIN_CURRENT
    max_current: int = DEFAULT_MAX_CURRENT


def _probe(host: str, port: int = 6668, timeout: float = 3.0) -> str:
    if not host:
        return "unreachable"
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "open"
    except ConnectionRefusedError:
        return "refused"
    except OSError:
        return "unreachable"


def _values_match(current: Any, expected: Any) -> bool:
    if isinstance(expected, bool):
        if isinstance(current, bool):
            return current is expected
        if isinstance(current, (int, float)):
            return bool(current) is expected
        if isinstance(current, str):
            return current.strip().lower() in (
                {"true", "1"} if expected else {"false", "0"}
            )
        return False
    if isinstance(expected, (int, float)):
        try:
            return float(current) == float(expected)
        except (TypeError, ValueError):
            return False
    return str(current).strip().lower() == str(expected).strip().lower()


class ChargerClient:
    """Synchronous Tuya client; call it from an executor in Home Assistant."""

    def __init__(self, settings: ChargerSettings) -> None:
        self.settings = settings
        self._device: tinytuya.Device | None = None
        self._lock = threading.RLock()

    def _connect_locked(self) -> None:
        """Create the local Tuya client. The caller must hold the lock."""
        self._close_locked()
        device = tinytuya.Device(
            dev_id=self.settings.device_id,
            address=self.settings.host,
            local_key=self.settings.local_key,
            version=float(self.settings.version),
            persist=False,
        )
        device.set_socketTimeout(5)
        device.set_socketRetryLimit(1)
        device.set_socketRetryDelay(1)
        self._device = device

    def connect(self) -> dict[str, Any]:
        """Open the local connection and return the first data point set."""
        with self._lock:
            self._connect_locked()
        try:
            return self.read_dps()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Close the local connection."""
        with self._lock:
            self._close_locked()

    def _close_locked(self) -> None:
        device, self._device = self._device, None
        if device is not None:
            with contextlib.suppress(Exception):
                device.close()

    def _ensure_device_locked(self) -> tinytuya.Device:
        """Return a connected client, reconnecting after a transient failure."""
        if self._device is None:
            try:
                self._connect_locked()
            except Exception as err:
                raise self._classify(err) from err
        return self._device

    def read_dps(self) -> dict[str, Any]:
        """Read the current data points."""
        with self._lock:
            device = self._ensure_device_locked()
            try:
                payload = device.status()
            except Exception as err:
                self._close_locked()
                raise self._classify(err) from err

            if not isinstance(payload, dict):
                raise ChargerError(f"Unexpected Tuya response: {payload!r}")
            if "Error" in payload:
                self._close_locked()
                raise self._classify(payload["Error"])

            dps = payload.get("dps")
            if not isinstance(dps, dict) or not dps:
                self._close_locked()
                raise ChargerError(
                    "Response without data points: invalid local key or protocol "
                    f"{self.settings.version}?"
                )
            return dps

    def status(self) -> Snapshot:
        """Read and decode the charger state."""
        return decode(self.read_dps(), max_current=self.settings.max_current)

    def set_charge(self, enabled: bool) -> dict[str, Any]:
        """Start or stop a charging session."""
        with self._lock:
            dps = self.read_dps()
            snapshot = decode(dps, max_current=self.settings.max_current)
            if snapshot.profile == "unknown":
                raise ChargerError(
                    "Unknown charger profile: charging cannot be controlled."
                )

            if snapshot.do_charge is not None:
                already = snapshot.do_charge is bool(enabled)
            else:
                already = snapshot.charging is bool(enabled)
            if already:
                return dps

            dp, value = charge_command(snapshot.profile, bool(enabled))
            return self._write_and_verify(dp, value)

    def set_current(self, amps: int) -> dict[str, Any]:
        """Set the charging current setpoint."""
        with self._lock:
            amps = int(amps)
            dps = self.read_dps()
            snapshot = decode(dps, max_current=self.settings.max_current)
            if snapshot.profile == "unknown":
                raise ChargerError(
                    "Unknown charger profile: current cannot be controlled."
                )

            hardware_max = min(self.settings.max_current, snapshot.max_current_a)
            if amps < self.settings.min_current or amps > hardware_max:
                raise ChargerError(
                    f"Current {amps} A is outside the allowed range "
                    f"({self.settings.min_current}-{hardware_max} A)."
                )
            if snapshot.current_target_a == amps:
                return dps

            return self._write_and_verify(current_dp(snapshot.profile), amps)

    def _write_and_verify(
        self,
        dp: str,
        value: Any,
        *,
        retries: int = 6,
        delay: float = 0.8,
    ) -> dict[str, Any]:
        with self._lock:
            self._write(dp, value)
            saw_dp = False
            for _ in range(retries):
                time.sleep(delay)
                dps = self.read_dps()
                if dp not in dps:
                    continue
                saw_dp = True
                if _values_match(dps[dp], value):
                    return dps
            if not saw_dp:
                return self.read_dps()
            raise ChargerError(f"The charger did not confirm DP {dp}.")

    def _write(self, dp: str, value: Any) -> None:
        with self._lock:
            device = self._ensure_device_locked()
            try:
                response = device.set_value(dp, value)
            except Exception as err:
                self._close_locked()
                raise self._classify(err) from err
            if isinstance(response, dict) and "Error" in response:
                self._close_locked()
                raise self._classify(response["Error"])

    def _classify(self, err: Any) -> ChargerError:
        text = str(err)
        probe = _probe(self.settings.host)
        if probe == "refused":
            return ChargerBusy(
                "Port 6668 refused: another local client holds the connection "
                "(Smart Life, Tuya app...). Close the other app and retry."
            )
        if probe == "unreachable":
            return ChargerUnreachable(
                f"Charger unreachable on {self.settings.host}:6668 ({text}). "
                "Check the IP and that the charger is on the same network."
            )
        return ChargerAuthError(
            f"TCP connection accepted but the exchange failed ({text}): invalid "
            f"local key or protocol {self.settings.version}?"
        )
