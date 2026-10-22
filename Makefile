# Reusable Home Assistant development environment.
#
# Defaults target this repository. To reuse this Makefile in another
# custom-component project, override COMPONENT_NAME (and COMPONENT_PATH
# if the component is not under custom_components/<name>).

SHELL := /bin/bash

COMPONENT_NAME ?= de_ev
COMPONENT_PATH ?= $(CURDIR)/custom_components/$(COMPONENT_NAME)
HA_CONFIG_DIR ?= $(CURDIR)/dev/ha-config
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
AUTO_ONBOARD ?= 1

COMPOSE_PROJECT_NAME ?= $(COMPONENT_NAME)-dev

DOCKER_COMPOSE ?= $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

export COMPONENT_NAME COMPONENT_PATH HA_CONFIG_DIR HA_BIND HA_PORT HA_IMAGE
export HA_CONTAINER_NAME HA_TIMEZONE HA_LANGUAGE HA_DEV_NAME HA_DEV_USER
export HA_DEV_PASSWORD HA_LATITUDE HA_LONGITUDE HA_ELEVATION HA_COUNTRY
export HA_CURRENCY HA_URL COMPOSE_PROJECT_NAME

.PHONY: help dev up down restart logs ps shell config reset clean onboard test lint compose-config check-component check-docker

help: ## Afficher cette aide
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<cible>\033[0m\n\nCibles:\n"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: up ## Démarrer HA et tenter l'onboarding
	@if [ "$(AUTO_ONBOARD)" = "1" ]; then $(MAKE) --no-print-directory onboard || true; fi
	@printf "\nHome Assistant : %s\n" "$(HA_URL)"
	@printf "Logs           : make logs\n"
	@printf "Arrêt          : make down\n"

up: check-component check-docker ## Démarrer le conteneur HA
	@mkdir -p "$(HA_CONFIG_DIR)"
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml up -d
	@printf "HA démarré sur %s (conteneur %s)\n" "$(HA_URL)" "$(HA_CONTAINER_NAME)"

check-component:
	@test -f "$(COMPONENT_PATH)/manifest.json" || (printf "Composant invalide : %s/manifest.json introuvable.\nDéfinis COMPONENT_NAME ou crée le manifest.\n" "$(COMPONENT_PATH)"; exit 1)

check-docker:
	@docker version >/dev/null 2>&1 || (printf "Docker indisponible dans WSL2.\nActive Docker Desktop → Settings → Resources → WSL Integration.\n"; exit 1)

down: check-docker ## Arrêter le conteneur HA
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml down

restart: check-docker ## Redémarrer HA
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml restart homeassistant

logs: check-docker ## Suivre les logs HA
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml logs -f --tail=200 homeassistant

ps: check-docker ## Voir l'état du conteneur
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml ps

shell: check-docker ## Ouvrir un shell dans le conteneur
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml exec homeassistant sh

config: check-docker ## Vérifier la configuration HA
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml exec homeassistant python -m homeassistant --script check_config -c /config

reset: down ## Supprimer l'état HA (onboarding, DB, logs)
	@rm -rf "$(HA_CONFIG_DIR)/.storage"
	@rm -f "$(HA_CONFIG_DIR)"/home-assistant_v2.db "$(HA_CONFIG_DIR)"/home-assistant_v2.db-* "$(HA_CONFIG_DIR)"/home-assistant.log "$(HA_CONFIG_DIR)"/home-assistant.log.*
	@printf "État HA supprimé. Relance avec 'make dev'.\n"

clean: reset ## Supprimer l'état et les fichiers runtime
	@rm -rf "$(HA_CONFIG_DIR)/deps" "$(HA_CONFIG_DIR)/tts" "$(HA_CONFIG_DIR)/backups" "$(HA_CONFIG_DIR)/.cloud"
	@printf "Fichiers runtime supprimés (configuration.yaml conservé).\n"

onboard: ## Créer le compte propriétaire via l'API onboarding
	@python3 dev/scripts/onboard.py

test: ## Lancer les tests Python
	@if find tests -name 'test_*.py' -print -quit 2>/dev/null | grep -q .; then python3 -m pytest -q; else printf "Aucun test pour le moment.\n"; fi

lint: ## Lancer ruff
	@if command -v ruff >/dev/null 2>&1; then ruff check .; else printf "ruff n'est pas installé.\n"; fi

compose-config: check-docker ## Valider le fichier Docker Compose
	@$(DOCKER_COMPOSE) -f dev/docker-compose.yml config
