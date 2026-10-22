# Dé EV Charger

Intégration Home Assistant pour une borne de recharge VE pilotée localement via
Tuya, avec découverte cloud pour le bootstrap.

> État actuel : **phase 0.3 — carte Lovelace**. Le config flow découvre la
> borne via Tuya Cloud ou accepte une configuration locale, expose les mesures
> et les commandes de charge, et fournit une carte de pilotage personnalisable.

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
5. Choisir **Cloud** (Access ID / Access Secret du projet Tuya) ou **Local**
   (IP, Device ID, Local Key). Le protocole est détecté automatiquement
   (3.5 → 3.4 → 3.3).

### Manuelle

```bash
cp -r custom_components/de_ev /config/custom_components/
```

Redémarrer Home Assistant, puis ajouter l'intégration depuis l'interface.
La borne n'accepte qu'un seul client TCP local à la fois : fermer l'application
Smart Life / Tuya pendant l'utilisation de l'intégration.

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

## Carte Lovelace

L'intégration fournit la carte `custom:de-ev-charger`. Aucune ressource
frontend à installer séparément : elle est servie par l'intégration.

Exemple minimal, à partir d'une entité de la borne (l'IP et les autres entités
sont retrouvées automatiquement via l'appareil) :

```yaml
type: custom:de-ev-charger
entity: sensor.garage_status
```

Exemple complet, avec choix des informations et des commandes :

```yaml
type: custom:de-ev-charger
device_id: 9f4c2a1b8e7d6c5f4a3b2c1d0e9f8a7b
title: Borne du garage
subtitle: Allée
icon: mdi:ev-station
metrics:
  - power
  - energy_session
  - session_duration
  - current
  - voltage
  - temperature
controls:
  - start_stop
  - current
```

`metrics` accepte les clés `status`, `power`, `voltage`, `current`,
`temperature`, `energy_session`, `session_duration`, `max_current`,
`work_state` et `last_session_energy`. `controls` accepte `start_stop` et
`current`. Pour retirer une information, il suffit de la retirer de la liste.

Chaque entrée de `metrics` peut aussi être un objet pour personnaliser le
libellé, l'icône ou l'entité :

```yaml
metrics:
  - key: power
    label: Puissance instantanée
    icon: mdi:flash
  - key: energy_session
    entity: sensor.garage_session_energy
```

Pour forcer toutes les entités (utile si la découverte automatique ne trouve
pas l'appareil), utiliser une correspondance explicite :

```yaml
type: custom:de-ev-charger
entities:
  status: sensor.garage_status
  power: sensor.garage_power
  energy_session: sensor.garage_session_energy
  charge_session: switch.garage_charging_session
  charge_current: number.garage_charging_current
```

## Documentation

La spécification complète (architecture, mapping des DP, entités, sessions,
énergie, roadmap) est dans [`docs.md`](docs.md).

## Sécurité

- Ne jamais committer `sandbox/ha-config/.storage/`, les bases de données ou les
  logs.
- Les identifiants Tuya et la clé locale seront stockés dans la config entry
  Home Assistant, jamais dans le dépôt.
- Le port HA est bindé sur `127.0.0.1` par défaut.
