# Contributing

Thank you for contributing to the Dé EV Charger integration.

## Development environment

Requirements:

- Docker Desktop with WSL2 integration enabled, or Docker Engine on Linux;
- Docker Compose v2;
- `make`;
- Python 3 to run the onboarding helper.

Start a disposable Home Assistant instance with the component mounted from the
working tree:

```bash
make dev
```

Then open <http://127.0.0.1:8123>. The Makefile tries to create the owner account
automatically and prints the credentials. The account and locale are configured
in `sandbox/config.yaml`, created from `sandbox/config.example.yaml` and ignored
by Git.

```bash
make logs     # follow Home Assistant logs
make config   # validate the Home Assistant configuration
make down     # stop the container
make reset    # start again from a clean Home Assistant state
```

The component is mounted read-only at `/config/custom_components/<domain>`, so
code changes are visible after a Home Assistant restart without rebuilding an
image.

### Reusing the sandbox

The `sandbox/` directory and the `Makefile` are generic. To reuse them in another
Home Assistant custom component project:

```bash
make dev COMPONENT_NAME=my_integration HA_PORT=8124
```

See [`sandbox/README.md`](sandbox/README.md) for all variables and commands.

## Tests and linting

The tests use Home Assistant 2026.10 and require Python 3.14:

```bash
uv venv --python 3.14
uv pip install -e ".[dev]"
uv run ruff check .
uv run pytest -q
```

Without `uv`:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/pytest -q
```

The Makefile shortcuts are:

```bash
make install-dev
make lint
make test
```

## Project layout

| Path | Purpose |
|---|---|
| `custom_components/de_ev/` | Integration source |
| `custom_components/de_ev/brand/` | Brand images used by Home Assistant and the Marketplace |
| `tests/` | Unit tests with `pytest-homeassistant-custom-component` |
| `sandbox/` | Disposable Home Assistant development environment |
| `docs.md` | Technical specification, data-point mapping and roadmap |
| `README.md` | End-user documentation |

## Code style

- Python code and identifiers are written in English.
- Keep the Home Assistant conventions: type hints, `async` APIs and translated
  entity names.
- Never log the Tuya Access Secret or the local key.
- Add or update tests for behaviour changes.
- Run `ruff check .` and `pytest -q` before opening a pull request.

## Commit conventions

Commit messages follow Conventional Commits:

```text
feat: add a user-facing feature
fix: fix a bug
docs: update documentation
ci: change CI or release automation
chore: maintenance without user impact
```

The release automation uses these prefixes to build the changelog and choose the
next version. Use `docs:`, `ci:`, `chore:` or `build:` for changes that should
not create a release on their own.

## Security

- Never commit `sandbox/ha-config/.storage/`, databases or logs.
- Tuya credentials and the local key are stored in the Home Assistant config
  entry, never in the repository.
- Do not commit `.env` files, tokens or local keys.
- The Home Assistant port is bound to `127.0.0.1` by default.
- Do not expose the charger directly to the Internet.
