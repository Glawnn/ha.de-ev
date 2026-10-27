"""Fixtures for the end-to-end tests: Home Assistant + a fake Tuya charger."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

E2E_DIR = Path(__file__).parent
HA_PORT = int(os.environ.get("E2E_HA_PORT", "18123"))
CONTROL_PORT = int(os.environ.get("E2E_CONTROL_PORT", "18080"))
HA_URL = f"http://127.0.0.1:{HA_PORT}"
CONTROL_URL = f"http://127.0.0.1:{CONTROL_PORT}"
CLIENT_ID = f"{HA_URL}/"
COMPOSE = ["docker", "compose", "-f", str(E2E_DIR / "docker-compose.yml")]
BOOT_TIMEOUT = 300


def pytest_configure(config: pytest.Config) -> None:
    """Register the e2e marker."""
    config.addinivalue_line("markers", "e2e: end-to-end test against Docker")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test in this directory as e2e."""
    for item in items:
        item.add_marker(pytest.mark.e2e)


def http(
    url: str,
    payload: Any = None,
    *,
    token: str | None = None,
    form: bool = False,
    method: str | None = None,
    timeout: float = 60,
) -> tuple[int, Any]:
    """Send a request and return the status code and the decoded body."""
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        if form:
            data = urllib.parse.urlencode(payload).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url, data=data, headers=headers, method=method or ("POST" if data else "GET")
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as err:
        body = err.read()
        status = err.code
    try:
        return status, json.loads(body) if body else None
    except ValueError:
        return status, body.decode(errors="replace")


class Charger:
    """Control API of the fake charger container."""

    def state(self) -> dict[str, Any]:
        """Return the charger state and the writes it received."""
        return http(f"{CONTROL_URL}/state")[1]

    def reset(self) -> None:
        """Restore the initial state."""
        http(f"{CONTROL_URL}/reset", {})

    def stop(self) -> None:
        """Refuse connections and close the open ones."""
        http(f"{CONTROL_URL}/stop", {})

    def start(self) -> None:
        """Accept connections again."""
        http(f"{CONTROL_URL}/start", {})

    def set_local_key(self, key: str) -> None:
        """Change the key the charger accepts."""
        http(f"{CONTROL_URL}/local_key", {"local_key": key})


class HomeAssistant:
    """Authenticated client for the Home Assistant REST API."""

    def __init__(self, token: str) -> None:
        self.token = token

    def request(self, path: str, payload: Any = None, **kwargs: Any) -> tuple[int, Any]:
        """Call the REST API."""
        return http(f"{HA_URL}{path}", payload, token=self.token, **kwargs)

    def state(self, entity_id: str) -> str | None:
        """Return the state of an entity, or None when it does not exist."""
        status, body = self.request(f"/api/states/{entity_id}")
        return body["state"] if status == 200 else None

    def call(self, domain: str, service: str, data: dict[str, Any]) -> int:
        """Call a service and return the HTTP status."""
        return self.request(f"/api/services/{domain}/{service}", data)[0]

    def refresh(self, entity_id: str) -> None:
        """Force an immediate coordinator refresh."""
        self.call("homeassistant", "update_entity", {"entity_id": entity_id})

    def wait_for(
        self,
        entity_id: str,
        expected: str,
        *,
        timeout: float = 30,
        refresh: bool = True,
    ) -> str | None:
        """Wait until an entity reaches a state and return the last state seen."""
        deadline = time.monotonic() + timeout
        last = self.state(entity_id)
        while time.monotonic() < deadline:
            if refresh:
                self.refresh(entity_id)
            last = self.state(entity_id)
            if last == expected:
                return last
            time.sleep(1)
        return last


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*COMPOSE, *args],
        check=check,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "E2E_HA_PORT": str(HA_PORT),
            "E2E_CONTROL_PORT": str(CONTROL_PORT),
        },
    )


def _wait_for_ha() -> None:
    deadline = time.monotonic() + BOOT_TIMEOUT
    while time.monotonic() < deadline:
        try:
            status, _ = http(f"{HA_URL}/api/onboarding", timeout=5)
        except OSError:
            status = 0
        if status == 200:
            return
        time.sleep(3)
    raise RuntimeError("Home Assistant did not become ready in time")


def _onboard() -> str:
    """Create the owner account and return an access token."""
    status, body = http(
        f"{HA_URL}/api/onboarding/users",
        {
            "client_id": CLIENT_ID,
            "name": "E2E",
            "username": "e2e",
            "password": "e2e-password-1234",
            "language": "en",
        },
    )
    assert status == 200, (status, body)
    status, body = http(
        f"{HA_URL}/auth/token",
        {
            "grant_type": "authorization_code",
            "code": body["auth_code"],
            "client_id": CLIENT_ID,
        },
        form=True,
    )
    assert status == 200, (status, body)
    return body["access_token"]


@pytest.fixture(autouse=True)
def _allow_network(socket_enabled: None) -> None:
    """Undo the socket guard installed by pytest-homeassistant-custom-component."""


@pytest.fixture(scope="session")
def stack() -> Iterator[None]:
    """Start the Docker stack for the whole session."""
    _compose("down", "-v", "--remove-orphans", check=False)
    started = _compose("up", "-d", "--build", check=False)
    try:
        assert started.returncode == 0, started.stderr
        _wait_for_ha()
        yield
    finally:
        logs = _compose("logs", "--no-color", check=False).stdout
        (E2E_DIR / "e2e.log").write_text(logs)
        _compose("down", "-v", "--remove-orphans", check=False)


@pytest.fixture(scope="session")
def ha(stack: None) -> HomeAssistant:
    """Return an authenticated Home Assistant client."""
    return HomeAssistant(_onboard())


@pytest.fixture
def charger(stack: None) -> Iterator[Charger]:
    """Return the fake charger, reset before and after each test."""
    fake = Charger()
    fake.reset()
    yield fake
    fake.reset()
