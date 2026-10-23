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

## Release process

Releases are automated with [release-please](https://github.com/googleapis/release-please).
The version is defined by the Git tag, so the tag and
`custom_components/de_ev/manifest.json` must always match.

### Normal release

1. Merge feature and fix pull requests into `main` using Conventional Commits.
2. release-please opens or updates a release pull request, for example
   `chore(main): release 0.3.0`.
3. Review the proposed version and `CHANGELOG.md`.
4. Merge the release pull request.
5. release-please creates the `vX.Y.Z` tag and the published GitHub Release.

The release pull request updates:

- `pyproject.toml`;
- `custom_components/de_ev/manifest.json`;
- `CHANGELOG.md`.

Do not bump these files or create tags by hand for normal releases.

### First release

The first public release (`v0.2.0`) is created manually once, because no previous
release exists to bootstrap release-please:

```bash
git checkout main
git pull
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
gh release create v0.2.0 --title "v0.2.0" --notes "Initial public release. See CHANGELOG.md for details."
```

After that, release-please handles every subsequent release.

### Rules

- Tag format: `vMAJOR.MINOR.PATCH` (for example `v0.3.0`).
- Never publish a release whose tag differs from the manifest version.
- Do not mark a stable release as a pre-release.
- Keep old releases: HACS and the Marketplace let users install previous
  versions.
- Use `docs:`, `ci:`, `chore:` or `build:` commits for changes that must not
  trigger a release.
- To test a release with volunteers, create the release as a GitHub pre-release
  and keep the tag/manifest versions identical. Users must enable pre-releases.

### CI on release pull requests

By default the workflow uses `GITHUB_TOKEN`, and pull requests created with that
token do not trigger other workflows. To run CI on release pull requests, add a
fine-grained personal access token as the `RELEASE_PLEASE_TOKEN` repository
secret with:

- **Contents**: read and write
- **Pull requests**: read and write
- **Issues**: read and write

Also enable **Settings → Actions → General → Allow GitHub Actions to create and
approve pull requests**.

## Security

- Never commit `sandbox/ha-config/.storage/`, databases or logs.
- Tuya credentials and the local key are stored in the Home Assistant config
  entry, never in the repository.
- Do not commit `.env` files, tokens or local keys.
- The Home Assistant port is bound to `127.0.0.1` by default.
- Do not expose the charger directly to the Internet.
