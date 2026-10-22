# Dé EV Charger

Intégration Home Assistant pour une borne de recharge VE pilotée localement via
Tuya, avec découverte cloud pour le bootstrap.

> État actuel : **phase 0.2 — environnement de développement**. Le composant
> `custom_components/de_ev` est un squelette volontairement minimal. La
> configuration Tuya et le contrôle local seront ajoutés dans les phases
> suivantes.

## Démarrage rapide

Prérequis : Docker avec l'intégration WSL2 activée, Docker Compose v2, `make`
et Python 3.

```bash
make dev
```

Ouvrir ensuite <http://127.0.0.1:8123>. Le Makefile tente de créer le compte
propriétaire automatiquement et affiche les identifiants.

```bash
make logs     # suivre les logs
make config   # vérifier la configuration HA
make down     # arrêter
make reset    # repartir d'un HA vierge
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
