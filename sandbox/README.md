# Environnement de développement Home Assistant

Le dossier `sandbox/` fournit un environnement Home Assistant jetable,
préconfiguré et réutilisable pour développer une intégration personnalisée.

Le composant n'est pas copié dans l'image : il est monté en lecture seule dans
`/config/custom_components/<domaine>`. Toute modification du code est donc
visible après un redémarrage de Home Assistant, sans reconstruire d'image.

## Prérequis

- Docker Desktop avec l'intégration WSL2 activée, ou Docker Engine sur Linux.
- Docker Compose v2 (`docker compose`).
- `make`.
- Python 3 pour le script d'onboarding.

Sur WSL2, vérifier que Docker est accessible :

```bash
docker version
docker compose version
```

Si `docker` n'est pas trouvé, activer l'intégration de la distribution dans
Docker Desktop : **Settings → Resources → WSL Integration**.

## Démarrage rapide

```bash
make dev
```

Puis ouvrir <http://127.0.0.1:8123>.

`make dev` :

1. démarre le conteneur Home Assistant ;
2. attend que l'interface réponde ;
3. tente de créer le compte propriétaire via l'API onboarding ;
4. affiche l'URL et les identifiants si l'onboarding a réussi.

Si l'onboarding automatique échoue, ouvrir l'interface et créer le compte
manuellement. La configuration et le composant sont déjà en place.

## Commandes

| Commande | Effet |
|---|---|
| `make dev` | Démarre HA + onboarding |
| `make up` | Démarre HA sans onboarding |
| `make down` | Arrête HA |
| `make restart` | Redémarre le conteneur |
| `make logs` | Suit les logs |
| `make ps` | Affiche l'état du conteneur |
| `make shell` | Ouvre un shell dans le conteneur |
| `make config` | Vérifie la configuration HA |
| `make onboard` | Relance l'onboarding |
| `make reset` | Supprime l'onboarding, la DB et les logs |
| `make clean` | Supprime l'état et les fichiers runtime |
| `make test` | Lance les tests Python |
| `make lint` | Lance ruff |
| `make compose-config` | Valide le fichier Compose |

## Variables

Les valeurs par défaut ciblent ce dépôt. Elles sont surchargeables :

```bash
make dev COMPONENT_NAME=mon_integration HA_PORT=8124
```

| Variable | Défaut | Rôle |
|---|---|---|
| `COMPONENT_NAME` | `de_ev` | Nom du dossier et domaine du composant |
| `COMPONENT_PATH` | `custom_components/<nom>` | Chemin source monté dans HA |
| `HA_CONFIG_DIR` | `sandbox/ha-config` | Configuration persistante HA |
| `HA_BIND` | `127.0.0.1` | Interface d'écoute |
| `HA_PORT` | `8123` | Port local |
| `HA_IMAGE` | `ghcr.io/home-assistant/home-assistant:stable` | Image HA |
| `HA_CONTAINER_NAME` | `<nom>-dev` | Nom du conteneur |
| `HA_TIMEZONE` | `Europe/Paris` | Fuseau horaire |
| `HA_DEV_USER` | `dev` | Utilisateur propriétaire |
| `HA_DEV_PASSWORD` | généré | Mot de passe propriétaire |
| `AUTO_ONBOARD` | `1` | Onboarding automatique avec `make dev` |

## Réutilisation dans un autre projet

1. Copier `Makefile` et le dossier `sandbox/` dans le nouveau dépôt.
2. Adapter `COMPONENT_NAME` et, si besoin, `COMPONENT_PATH`.
3. Vérifier que le composant contient un `manifest.json`.
4. Lancer `make dev`.

Le dossier `sandbox/ha-config/` est autonome : il contient la configuration HA
et un `.gitignore` qui exclut les données sensibles (`.storage`, base de
données, logs).

Pour utiliser plusieurs environnements en parallèle, changer `HA_PORT` et
`COMPOSE_PROJECT_NAME` :

```bash
make dev COMPONENT_NAME=mon_integration HA_PORT=8124 COMPOSE_PROJECT_NAME=mon-integration-dev
```

## Données et sécurité

- `sandbox/ha-config/.storage/` contient les utilisateurs, tokens et entrées de
  configuration : **ne jamais le committer**.
- Le port est bindé sur `127.0.0.1` par défaut. Pour exposer HA sur le réseau,
  utiliser `HA_BIND=0.0.0.0` en connaissance de cause.
- Le composant est monté en lecture seule ; `PYTHONDONTWRITEBYTECODE=1` évite
  de créer des `__pycache__` dans le dépôt.
- L'environnement est destiné au développement, pas à la production.

## Notes

- Home Assistant peut mettre 30 à 60 secondes à démarrer.
- Le premier démarrage peut télécharger l'image Docker.
- Pour tester un appareil Tuya local, le conteneur doit pouvoir joindre le
  réseau local. Le mode bridge Docker suffit pour les connexions sortantes ;
  la découverte mDNS/UDP peut nécessiter un mode réseau spécifique.
- Pour ajouter un accès USB (Zigbee, Z-Wave, Bluetooth), ajouter les devices et
  les capabilities nécessaires dans `docker-compose.yml`.
