# Dé EV Charger

Intégration Home Assistant pour une borne de recharge VE pilotée localement via
Tuya, avec découverte cloud pour le bootstrap.

> État actuel : **phase 0.1 — bootstrap de l'intégration**. Le composant
> `custom_components/de_ev` s'installe et affiche son config flow, mais ne
> crée pas encore d'entités. La configuration Tuya et le contrôle local seront
> ajoutés dans les phases suivantes.

## Démarrage rapide

Prérequis : Docker avec l'intégration WSL2 activée, Docker Compose v2, `make`
et Python 3.

```bash
make dev
```

Ouvrir ensuite <http://127.0.0.1:8123>. Le Makefile tente de créer le compte
propriétaire automatiquement et affiche les identifiants. Le compte et la
locale se configurent dans `sandbox/config.yaml`, créé depuis
`sandbox/config.example.yaml` et ignoré par Git.

```bash
make logs     # suivre les logs
make config   # vérifier la configuration HA
make down     # arrêter
make reset    # repartir d'un HA vierge
```

## Installation

### HACS

1. Ouvrir HACS → **Intégrations** → menu → **Dépôts personnalisés**.
2. Ajouter `https://github.com/Glawnn/ha.de-ev` en catégorie **Integration**.
3. Installer **Dé EV Charger**, puis redémarrer Home Assistant.
4. **Paramètres → Appareils et services → Ajouter une intégration**, puis
   chercher **Dé EV Charger**.

### Manuelle

```bash
cp -r custom_components/de_ev /config/custom_components/
```

Redémarrer Home Assistant, puis ajouter l'intégration depuis l'interface. La
version actuelle crée une entrée de configuration et prépare les phases cloud
et locale ; elle n'expose pas encore d'entités.

## Développement

Les tests utilisent Home Assistant 2026.10 et nécessitent Python 3.14 :

```bash
uv venv --python 3.14
uv pip install -e ".[dev]"
uv run ruff check .
uv run pytest -q
```

Alternative sans `uv` :

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/pytest -q
```

## Environnement réutilisable

Le dossier `sandbox/` et le `Makefile` sont génériques. Pour les réutiliser dans
un autre projet Home Assistant :

```bash
make dev COMPONENT_NAME=mon_integration HA_PORT=8124
```

Le composant est monté en lecture seule dans
`/config/custom_components/<domaine>`, donc les modifications sont visibles
après un redémarrage de Home Assistant, sans reconstruire d'image.

Voir [`sandbox/README.md`](sandbox/README.md) pour les variables, les commandes
et les instructions de réutilisation.

## Documentation

La spécification complète (architecture, mapping des DP, entités, sessions,
énergie, roadmap) est dans [`docs.md`](docs.md).

## Sécurité

- Ne jamais committer `sandbox/ha-config/.storage/`, les bases de données ou les
  logs.
- Les identifiants Tuya et la clé locale seront stockés dans la config entry
  Home Assistant, jamais dans le dépôt.
- Le port HA est bindé sur `127.0.0.1` par défaut.
