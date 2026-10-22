# Reusable Home Assistant development environment.
#
# Defaults target this repository. To reuse this Makefile in another
# custom-component project, override COMPONENT_NAME (and COMPONENT_PATH
# if the component is not under custom_components/<name>).

SHELL := /bin/bash

COMPONENT_NAME ?= de_ev
COMPONENT_PATH ?= $(CURDIR)/custom_components/$(COMPONENT_NAME)
HA_CONFIG_DIR ?= $(CURDIR)/sandbox/ha-config
HA_BIND ?= 127.0.0.1
HA_PORT ?= 8123
HA_IMAGE ?= ghcr.io/home-assistant/home-assistant:stable
HA_CONTAINER_NAME ?= $(COMPONENT_NAME)-dev
HA_TIMEZONE ?= Europe/Paris
HA_LANGUAGE ?= fr
HA_DEV_NAME ?= Dev
HA_DEV_USER ?= dev
HA_DEV_PASSWORD ?=
HA_LATITUDE ?= 48.8566
HA_LONGITUDE ?= 2.3522
HA_ELEVATION ?= 35
HA_COUNTRY ?= FR
HA_CURRENCY ?= EUR
HA_URL ?= http://127.0.0.1:$(HA_PORT)
HA_SANDBOX_CONFIG ?= $(CURDIR)/sandbox/config.yaml
VENV ?= .venv
AUTO_ONBOARD ?= 1

COMPOSE_PROJECT_NAME ?= $(COMPONENT_NAME)-dev

DOCKER_COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

export COMPONENT_NAME COMPONENT_PATH HA_CONFIG_DIR HA_BIND HA_PORT HA_IMAGE
export HA_CONTAINER_NAME HA_TIMEZONE HA_LANGUAGE HA_DEV_NAME HA_DEV_USER
export HA_DEV_PASSWORD HA_LATITUDE HA_LONGITUDE HA_ELEVATION HA_COUNTRY
export HA_CURRENCY HA_URL HA_SANDBOX_CONFIG COMPOSE_PROJECT_NAME

.PHONY: help dev up down restart logs ps shell config reset clean onboard install-dev test lint compose-config check-component check-docker

help: ## Afficher cette aide
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<cible>\033[0m\n\nCibles:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: up ## Démarrer HA et tenter l'onboarding
	@if [ "$(AUTO_ONBOARD)" = "1" ]; then $(MAKE) --no-print-directory onboard || true; fi
	@printf "\nHome Assistant : %s\n" "$(HA_URL)"
	@printf "Logs           : make logs\n"
	@printf "Arrêt          : make down\n"

up: check-component check-docker ## Démarrer le conteneur HA
	@mkdir -p "$(HA_CONFIG_DIR)"
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml up -d
	@printf "HA démarré sur %s (conteneur %s)\n" "$(HA_URL)" "$(HA_CONTAINER_NAME)"

check-component:
	@test -f "$(COMPONENT_PATH)/manifest.json" || (printf "Composant invalide : %s/manifest.json introuvable.\nDéfinis COMPONENT_NAME ou crée le manifest.\n" "$(COMPONENT_PATH)"; exit 1)

check-docker:
	@docker version >/dev/null 2>&1 || (printf "Docker indisponible dans WSL2.\nActive Docker Desktop → Settings → Resources → WSL Integration.\n"; exit 1)

down: check-docker ## Arrêter le conteneur HA
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml down

restart: check-docker ## Redémarrer HA
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml restart homeassistant

logs: check-docker ## Suivre les logs HA
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml logs -f --tail=200 homeassistant

ps: check-docker ## Voir l'état du conteneur
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml ps

shell: check-docker ## Ouvrir un shell dans le conteneur
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml exec homeassistant sh

config: check-docker ## Vérifier la configuration HA
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml exec homeassistant python -m homeassistant --script check_config -c /config

reset: down ## Supprimer l'état HA (onboarding, DB, logs)
	@docker run --rm --entrypoint sh -v "$(HA_CONFIG_DIR):/config" "$(HA_IMAGE)" -c 'rm -rf /config/.storage; rm -f /config/.ha_run.lock /config/home-assistant_v2.db /config/home-assistant_v2.db-* /config/home-assistant.log /config/home-assistant.log.*'
	@printf "État HA supprimé. Relance avec 'make dev'.\n"

clean: reset ## Supprimer l'état et les fichiers runtime
	@docker run --rm --entrypoint sh -v "$(HA_CONFIG_DIR):/config" "$(HA_IMAGE)" -c 'rm -rf /config/deps /config/tts /config/backups /config/.cloud'
	@printf "Fichiers runtime supprimés (configuration.yaml conservé).\n"

onboard: ## Créer le compte propriétaire via l'API onboarding
	@test -f "$(HA_SANDBOX_CONFIG)" || { cp sandbox/config.example.yaml "$(HA_SANDBOX_CONFIG)"; chmod 600 "$(HA_SANDBOX_CONFIG)"; }
	@python3 sandbox/scripts/onboard.py

install-dev: ## Créer le venv et installer les dépendances de développement
	@if command -v uv >/dev/null 2>&1; then \
		uv venv --python 3.14 "$(VENV)"; \
		uv pip install --python "$(VENV)/bin/python" -e ".[dev]"; \
	else \
		python3 -m venv "$(VENV)"; \
		"$(VENV)/bin/python" -m pip install --upgrade pip; \
		"$(VENV)/bin/python" -m pip install -e ".[dev]"; \
	fi

test: ## Lancer les tests Python
	@if [ ! -x "$(VENV)/bin/python" ]; then printf "Environnement absent. Lance 'make install-dev'.\n"; exit 1; fi
	@"$(VENV)/bin/python" -m pytest -q

lint: ## Lancer ruff
	@if [ -x "$(VENV)/bin/ruff" ]; then "$(VENV)/bin/ruff" check .; \
	elif command -v ruff >/dev/null 2>&1; then ruff check .; \
	else printf "ruff n'est pas installé. Lance 'make install-dev'.\n"; exit 1; fi

compose-config: check-docker ## Valider le fichier Docker Compose
	@$(DOCKER_COMPOSE) -f sandbox/docker-compose.yml config
