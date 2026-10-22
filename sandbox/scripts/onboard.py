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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def load_config(path: Path) -> dict[str, str]:
    """Load a flat YAML config using only the standard library."""
    config: dict[str, str] = {}
    if not path.is_file():
        return config

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value[:1] in {"'", '"'}:
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end != -1 else value[1:]
        else:
            value = value.split("#", 1)[0].strip()
        config[key.strip()] = value
    return config


CONFIG_PATH = Path(
    os.environ.get(
        "HA_SANDBOX_CONFIG",
        Path(__file__).resolve().parents[1] / "config.yaml",
    )
)
CONFIG = load_config(CONFIG_PATH)


def setting(key: str, env: str, default: str = "") -> str:
    """Read from the YAML config, then the environment, then a default."""
    return CONFIG.get(key) or os.environ.get(env) or default


HA_URL = setting("ha_url", "HA_URL", "http://127.0.0.1:8123").rstrip("/")
CLIENT_ID = f"{HA_URL}/"

USERNAME = setting("username", "HA_DEV_USER", "dev")
PASSWORD = setting("password", "HA_DEV_PASSWORD") or secrets.token_urlsafe(12)
NAME = setting("name", "HA_DEV_NAME", "Dev")
LANGUAGE = setting("language", "HA_LANGUAGE", "fr")
TIMEZONE = setting("timezone", "HA_TIMEZONE", "Europe/Paris")
COUNTRY = setting("country", "HA_COUNTRY", "FR")
CURRENCY = setting("currency", "HA_CURRENCY", "EUR")
LATITUDE = float(setting("latitude", "HA_LATITUDE", "48.8566"))
LONGITUDE = float(setting("longitude", "HA_LONGITUDE", "2.3522"))
ELEVATION = int(setting("elevation", "HA_ELEVATION", "35"))
TIMEOUT = int(setting("timeout", "HA_ONBOARD_TIMEOUT", "180"))


def request(
    path: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    form: bool = False,
) -> tuple[int | None, Any]:
    """Send a JSON or form request to Home Assistant."""
    url = f"{HA_URL}{path}"
    data = None
    if payload is not None:
        if form:
            data = urllib.parse.urlencode(payload).encode("utf-8")
        else:
            data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST" if data is not None else "GET",
    )
    req.add_header(
        "Content-Type",
        "application/x-www-form-urlencoded" if form else "application/json",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")

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
    elif status in (400, 403, 404, 409):
        print("Onboarding déjà effectué ou compte déjà existant.")
        print(f"Home Assistant : {HA_URL}")
        return 0
    else:
        print(f"Échec de l'onboarding utilisateur ({status}) : {body}", file=sys.stderr)
        return 1

    auth_code = body.get("auth_code") if isinstance(body, dict) else None
    if not auth_code:
        print(f"Réponse d'onboarding invalide : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/auth/token",
        {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": CLIENT_ID,
        },
        form=True,
    )
    if (
        status not in (200, 201)
        or not isinstance(body, dict)
        or "access_token" not in body
    ):
        print(f"Échec de l'échange du jeton ({status}) : {body}", file=sys.stderr)
        return 1

    access_token = body["access_token"]

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
        token=access_token,
    )
    if status not in (200, 201):
        print(f"Échec de la configuration de base ({status}) : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/analytics",
        {},
        token=access_token,
    )
    if status not in (200, 201):
        print(f"Échec de l'étape analytics ({status}) : {body}", file=sys.stderr)
        return 1

    status, body = request(
        "/api/onboarding/integration",
        {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID},
        token=access_token,
    )
    if status not in (200, 201):
        print(f"Étape d'intégration ignorée ({status}) : {body}", file=sys.stderr)

    print(f"Home Assistant prêt : {HA_URL}")
    print(f"Identifiants : {USERNAME} / {PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
