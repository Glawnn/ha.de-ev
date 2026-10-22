#!/usr/bin/env python3
"""Best-effort Home Assistant onboarding for the local dev environment.

This script is intentionally dependency-free (standard library only). It waits
for Home Assistant, then walks the onboarding API to create the owner account.

If the API changes or the instance is already onboarded, the script exits
cleanly and the UI can still be used to finish the setup.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from typing import Any

HA_URL = os.environ.get("HA_URL", "http://127.0.0.1:8123").rstrip("/")
CLIENT_ID = f"{HA_URL}/"

USERNAME = os.environ.get("HA_DEV_USER", "dev")
PASSWORD = os.environ.get("HA_DEV_PASSWORD") or secrets.token_urlsafe(12)
NAME = os.environ.get("HA_DEV_NAME", "Dev")
LANGUAGE = os.environ.get("HA_LANGUAGE", "fr")
TIMEZONE = os.environ.get("HA_TIMEZONE", "Europe/Paris")
COUNTRY = os.environ.get("HA_COUNTRY", "FR")
CURRENCY = os.environ.get("HA_CURRENCY", "EUR")
LATITUDE = float(os.environ.get("HA_LATITUDE", "48.8566"))
LONGITUDE = float(os.environ.get("HA_LONGITUDE", "2.3522"))
ELEVATION = int(os.environ.get("HA_ELEVATION", "35"))
TIMEOUT = int(os.environ.get("HA_ONBOARD_TIMEOUT", "180"))


def request(path: str, payload: dict[str, Any] | None = None) -> tuple[int | None, Any]:
    """Send a JSON request to Home Assistant."""
    url = f"{HA_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
    )
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = {"message": body}
        return err.code, parsed
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        return None, {"message": str(err)}


def wait_for_ha() -> bool:
    """Wait until Home Assistant serves its manifest."""
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        status, _ = request("/manifest.json")
        if status == 200:
            return True
        time.sleep(2)
    return False


def main() -> int:
    if not wait_for_ha():
        print(f"Home Assistant injoignable sur {HA_URL}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/users",
        {
            "client_id": CLIENT_ID,
            "name": NAME,
            "username": USERNAME,
            "password": PASSWORD,
            "language": LANGUAGE,
        },
    )
    if status in (200, 201):
        print(f"Compte propriétaire créé : {USERNAME}")
    elif status in (400, 403, 409):
        print("Onboarding déjà effectué ou compte déjà existant.")
        print(f"Home Assistant : {HA_URL}")
        return 0
    else:
        print(f"Échec de l'onboarding utilisateur ({status}) : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/core_config",
        {
            "client_id": CLIENT_ID,
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "elevation": ELEVATION,
            "unit_system": "metric",
            "time_zone": TIMEZONE,
            "currency": CURRENCY,
            "country": COUNTRY,
            "language": LANGUAGE,
        },
    )
    if status not in (200, 201):
        print(f"Échec de la configuration de base ({status}) : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/analytics",
        {"client_id": CLIENT_ID, "analytics": False},
    )
    if status not in (200, 201):
        print(f"Échec de l'étape analytics ({status}) : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/integration",
        {"client_id": CLIENT_ID, "user_input": {}},
    )
    if status not in (200, 201):
        print(f"Étape d'intégration ignorée ({status}) : {body}", file=sys.stderr)

    print(f"Home Assistant prêt : {HA_URL}")
    print(f"Identifiants : {USERNAME} / {PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
