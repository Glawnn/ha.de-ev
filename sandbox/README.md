# Home Assistant development sandbox

The `sandbox/` directory provides a disposable, preconfigured and reusable
Home Assistant environment for developing a custom integration.

The component is not baked into the image: it is mounted read-only at
`/config/custom_components/<domain>`. Code changes therefore become visible
after a Home Assistant restart, without rebuilding the image.

## Requirements

- Docker Desktop with WSL2 integration enabled, or Docker Engine on Linux.
- Docker Compose v2 (`docker compose`).
- `make`.
- Python 3 for the onboarding script.

On WSL2, verify that Docker is reachable:

```bash
docker version
docker compose version
```

If `docker` is not found, enable the distribution in Docker Desktop:
**Settings → Resources → WSL Integration**.

## Quick start

```bash
make dev
```

Then open <http://127.0.0.1:8123>.

`make dev`:

1. starts the Home Assistant container;
2. waits for the web interface to respond;
3. creates `sandbox/config.yaml` from `sandbox/config.example.yaml` if needed;
4. tries to create the owner account through the onboarding API;
5. prints the URL and credentials if onboarding succeeded.

If automatic onboarding fails, open the UI and create the account manually.
The configuration and the component are already in place.

## Sandbox configuration

The owner account and locale are read from `sandbox/config.yaml`. This file is
local, ignored by Git, and created from `sandbox/config.example.yaml` on the
first `make dev`:

```bash
cp sandbox/config.example.yaml sandbox/config.yaml
$EDITOR sandbox/config.yaml
```

The file uses flat `key: value` YAML:

```yaml
username: dev
password: "change-me"
name: Dev
language: fr
timezone: Europe/Paris
country: FR
currency: EUR
latitude: 48.8566
longitude: 2.3522
elevation: 35
timeout: 180
```

An empty `password` generates a random one on first onboarding. A changed
username or password only applies to a new account: run `make reset` before
`make dev` to recreate it. Environment variables such as `HA_DEV_USER` and
`HA_DEV_PASSWORD` are used as fallbacks when the YAML key is missing or empty.
Docker settings (port, image, etc.) remain Makefile variables.

## Commands

| Command | Effect |
|---|---|
| `make dev` | Start HA and run onboarding |
| `make up` | Start HA without onboarding |
| `make down` | Stop HA |
| `make restart` | Restart the container |
| `make logs` | Follow the logs |
| `make ps` | Show the container status |
| `make shell` | Open a shell in the container |
| `make config` | Validate the HA configuration |
| `make onboard` | Run onboarding again |
| `make reset` | Remove onboarding, the database and logs |
| `make clean` | Remove state and runtime files |
| `make test` | Run the Python tests |
| `make lint` | Run ruff |
| `make compose-config` | Validate the Compose file |

## Variables

The defaults target this repository. They can be overridden:

```bash
make dev COMPONENT_NAME=my_integration HA_PORT=8124
```

| Variable | Default | Purpose |
|---|---|---|
| `COMPONENT_NAME` | `de_ev` | Component directory and domain name |
| `COMPONENT_PATH` | `custom_components/<name>` | Source path mounted into HA |
| `HA_CONFIG_DIR` | `sandbox/ha-config` | Persistent HA configuration |
| `HA_BIND` | `127.0.0.1` | Listen address |
| `HA_PORT` | `8123` | Local port |
| `HA_IMAGE` | `ghcr.io/home-assistant/home-assistant:stable` | HA image |
| `HA_CONTAINER_NAME` | `<name>-dev` | Container name |
| `HA_TIMEZONE` | `Europe/Paris` | Timezone |
| `HA_DEV_USER` | YAML / `dev` | Owner username fallback |
| `HA_DEV_PASSWORD` | YAML / generated | Owner password fallback |
| `HA_SANDBOX_CONFIG` | `sandbox/config.yaml` | Sandbox onboarding YAML |
| `AUTO_ONBOARD` | `1` | Automatic onboarding with `make dev` |

## Reusing it in another project

1. Copy `Makefile` and the `sandbox/` directory into the new repository.
2. Set `COMPONENT_NAME` and, if needed, `COMPONENT_PATH`.
3. Make sure the component contains a `manifest.json`.
4. Run `make dev`.

The `sandbox/ha-config/` directory is self-contained: it holds the HA
configuration and a `.gitignore` that excludes sensitive data (`.storage`,
database, logs).

To run several environments side by side, change `HA_PORT` and
`COMPOSE_PROJECT_NAME`:

```bash
make dev COMPONENT_NAME=my_integration HA_PORT=8124 COMPOSE_PROJECT_NAME=my-integration-dev
```

## Data and security

- `sandbox/ha-config/.storage/` contains users, tokens and configuration
  entries: **never commit it**.
- `sandbox/config.yaml` contains the sandbox password: **never commit it**.
  Only `sandbox/config.example.yaml` belongs in Git.
- The port is bound to `127.0.0.1` by default. To expose HA on the network,
  use `HA_BIND=0.0.0.0` with care.
- The component is mounted read-only; `PYTHONDONTWRITEBYTECODE=1` prevents
  `__pycache__` directories from being created in the repository.
- This environment is intended for development, not production.

## Notes

- Home Assistant can take 30 to 60 seconds to start.
- The first start may download the Docker image.
- To test a local Tuya device, the container must be able to reach the local
  network. Docker bridge mode is enough for outbound connections; mDNS/UDP
  discovery may require a specific network mode.
- To add USB access (Zigbee, Z-Wave, Bluetooth), add the required devices and
  capabilities to `docker-compose.yml`.
