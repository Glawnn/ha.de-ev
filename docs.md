# ha.de-ev — Intégration Home Assistant pour borne EV Tuya

> **Statut** : conception validée, développement à démarrer  
> **Version cible** : `0.1.0`  
> **Dépôt** : <https://github.com/Glawnn/ha.de-ev>  
> **Domaine Home Assistant** : `de_ev`

---

## 1. Résumé

`ha.de-ev` est une intégration Home Assistant personnalisée pour piloter et superviser une borne de recharge Tuya **Dé Pow EV Charger** (3,5 kW).

L'intégration utilise le **cloud Tuya uniquement pour la configuration initiale** :

1. connexion avec `Access ID / Client ID`, `Access Secret / Client Secret` et la région Tuya ;
2. récupération de la clé locale et de l'adresse de la borne ;
3. bascule immédiate en **contrôle 100 % local** sur le port `6668`.

Elle expose ensuite les mesures, les commandes, l'énergie et un historique des sessions de recharge dans Home Assistant, avec intégration au tableau de bord Énergie natif.

---

## 2. Objectifs

### 2.1 Objectif principal

Permettre à l'utilisateur de :

- configurer la borne avec uniquement ses identifiants Tuya Cloud ;
- allumer / arrêter la charge ;
- régler le courant de charge entre 6 A et 16 A par pas de 1 A ;
- suivre la puissance, la tension, le courant, la température et l'énergie ;
- consulter l'historique des sessions de recharge ;
- retrouver la consommation dans le tableau de bord Énergie de Home Assistant ;
- garder le contrôle local, même si le cloud Tuya devient indisponible.

### 2.2 Non-objectifs de la v1

- pilotage exclusivement cloud ;
- planification tarifaire avancée ;
- pilotage solaire / surplus ;
- gestion multi-véhicules ;
- intégration HACS immédiate ;
- support complet de tous les modèles Tuya EV.

Ces éléments pourront être ajoutés après validation de la v1.

---

## 3. Contexte matériel

| Élément | Valeur |
|---|---|
| Modèle | Dé Pow EV Charger |
| Puissance | 3,5 kW |
| Firmware validé | `1.9.7` |
| Profil Tuya | `depow_v2` |
| Protocole local | `3.5` |
| Port local | `6668` |
| Connexion locale | une seule connexion TCP à la fois |
| Clé locale | 16 caractères, récupérée via le cloud |

### 3.1 Contraintes connues

- La borne n'accepte qu'**un seul client local** à la fois. Smart Life ou l'application Tuya ouverte peut bloquer la connexion.
- Le cloud Tuya ne fournit **pas l'historique des DP**. Il ne renvoie que des événements de type online / RSSI.
- Le DP `105` ne contient que la **dernière session terminée**, écrasée à chaque nouvelle session.
- Le DP `107` contient les **raccourcis de l'application Tuya** (`6/8/10/13/16 A`), ce n'est pas une limite matérielle.
- Le courant doit être réglé par pas de `1 A`, dans la plage `6–16 A`.
- La valeur `11 A` est acceptée par le protocole mais n'a pas encore été testée physiquement sur la borne.
- L'IP de la borne peut changer via DHCP.
- La clé locale peut changer après un ré-appairage.
- L'essai gratuit Tuya IoT Core peut expirer ; le contrôle local doit continuer à fonctionner avec une clé valide.

---

## 4. Fonctionnalités

### 4.1 v1 — périmètre validé

| Fonctionnalité | Détail |
|---|---|
| Configuration cloud | Région + Access ID + Access Secret |
| Découverte | Récupération de la clé locale et de l'IP via le cloud |
| Connexion locale | Validation réelle de la connexion tinytuya |
| Zone HA | Sélection optionnelle de la pièce |
| État | En charge, disponible, branché, en attente, pause, défaut |
| Mesures | Puissance, tension, courant, température, durée |
| Énergie | Énergie de session en kWh |
| Contrôle | Start / stop, courant 6–16 A |
| Historique | Détection automatique des sessions + stockage JSON |
| Dashboard Énergie | Capteur `total_increasing` compatible HA |
| Diagnostic | Firmware, variante, état interne, DP brut |
| Robustesse | Reauth, reconfigure, redécouverte IP, erreurs explicites |
| Traductions | Français et anglais |

### 4.2 v1.1 — après validation

- programmation horaire (DP `151`) ;
- activation / désactivation NFC (DP `155`) ;
- redémarrage de la borne (DP `142`) ;
- bouton « prêt à charger » ;
- export CSV des sessions ;
- capteur d'énergie totale cumulée.

### 4.3 Plus tard

- coût par session avec heures creuses / pleines ;
- attribution d'un véhicule ;
- notifications de fin de charge ;
- pilotage solaire / surplus ;
- support d'autres profils Tuya (`qccdz_v1`) ;
- carte Lovelace dédiée ;
- intégration HACS.

---

## 5. Architecture

```text
┌─────────────────────┐
│  Home Assistant     │
│                     │
│  Config Flow        │
│      │              │
│      ▼              │
│  Cloud Tuya ────────┼──► Access ID / Secret / Région
│      │              │
│      │ clé locale   │
│      ▼              │
│  ChargerClient      │
│      │              │
│      ▼              │
│  DataUpdateCoordinator
│      │              │
│      ├── Entités    │
│      ├── Sessions   │
│      └── Énergie    │
│                     │
└─────────┬───────────┘
          │ TCP 6668
          ▼
┌─────────────────────┐
│  Borne EV Tuya      │
│  depow_v2           │
└─────────────────────┘
```

### 5.1 Principes

- Le cloud ne sert qu'au **bootstrap** et au **renouvellement de clé** en cas d'échec d'authentification.
- Le polling est **local**, toutes les 30 secondes par défaut.
- Toutes les opérations sur la borne sont **sérialisées**.
- Aucune écriture n'est envoyée si la valeur est déjà correcte.
- Les secrets ne sont jamais écrits dans les logs.
- L'historique des sessions est stocké dans un `Store` Home Assistant, pas dans SQLite.

---

## 6. Arborescence du projet

```text
ha.de-ev/
├── custom_components/
│   └── de_ev/
│       ├── __init__.py
│       ├── manifest.json
│       ├── const.py
│       ├── config_flow.py
│       ├── options_flow.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── switch.py
│       ├── number.py
│       ├── button.py
│       ├── diagnostics.py
│       ├── services.yaml
│       ├── strings.json
│       ├── translations/
│       │   ├── fr.json
│       │   └── en.json
│       ├── profiles.py
│       ├── charger.py
│       ├── cloud.py
│       ├── discovery.py
│       └── sessions.py
├── sandbox/
│   ├── docker-compose.yml
│   ├── ha-config/
│   │   ├── configuration.yaml
│   │   └── .gitignore
│   ├── scripts/
│   │   └── onboard.py
│   └── README.md
├── tests/
│   ├── conftest.py
│   ├── test_config_flow.py
│   ├── test_coordinator.py
│   ├── test_sessions.py
│   ├── test_sensors.py
│   └── test_diagnostics.py
├── .github/
│   └── workflows/
│       └── ci.yml
├── Makefile
├── hacs.json
├── pyproject.toml
├── .gitignore
├── README.md
├── LICENSE
└── docs.md
```

En phase 0.2, seuls le `Makefile`, `sandbox/`, `README.md`, `.gitignore` et le
squelette minimal de `custom_components/de_ev` existent. Le reste de
l'arborescence est la cible v1 et sera ajouté au fil des phases.

### 6.1 Manifest

```json
{
  "domain": "de_ev",
  "name": "Dé EV Charger",
  "version": "0.1.0",
  "config_flow": true,
  "integration_type": "device",
  "iot_class": "local_polling",
  "requirements": ["tinytuya>=1.20.0"],
  "loggers": ["tinytuya"],
  "dhcp": [{"registered_devices": true}]
}
```

Le manifest de la phase 0.2 est volontairement sans dépendance externe
(`"requirements": []`) pour valider le montage et le chargement du composant.
`tinytuya` sera ajouté en phase 0.1.

---

## 7. Modèle de données

### 7.1 `Snapshot`

Représente l'état décodé de la borne à un instant donné.

```python
@dataclass(slots=True)
class Snapshot:
    profile: str
    status: str
    status_label: str
    charging: bool
    plugged: bool
    power_w: float
    voltage_v: float
    current_a: float
    energy_kwh: float | None
    current_target_a: int | None
    max_current_a: int
    do_charge: bool | None
    temperature_c: float | None
    session_duration_s: int | None
    work_state: int | None
    nfc_enabled: bool | None
    product_variant: int | None
    schedule: dict | None
    last_session: dict | None
    charger_info: dict | None
```

### 7.2 `SessionRecord`

Représente une session terminée, persistée dans le `Store`.

```json
{
  "started_at": "2026-10-19T19:23:05+02:00",
  "ended_at": "2026-10-20T05:35:00+02:00",
  "duration_s": 36749,
  "charging_s": 2554,
  "energy_kwh": 31.1,
  "peak_power_w": 3001,
  "avg_power_w": 1800,
  "cost": null,
  "vehicle": null,
  "source": "dp105"
}
```

---

## 8. Mapping des DP

### 8.1 Profil `depow_v2`

| DP | Contenu | Usage |
|---|---|---|
| `101` | état interne numérique | diagnostic |
| `102` | JSON `L1=[V×10, A×10, kW×10]`, `t` température ×10, `d` durée ×0,1 s, `e` énergie ×0,1 kWh | mesures |
| `105` | JSON dernière session : `t`, `s`, `e`, `d`, `c` | historique |
| `106` | JSON infos borne : `r`, `fv`, `cp`, `t`, `e` | diagnostic |
| `107` | JSON raccourcis de l'application | diagnostic, **pas une limite** |
| `109` | état texte : `IDLE`, `IDLEINS`, `WORKING`, `STOP`, `PAUSE`, `ERRORPAUSE` | état |
| `140` | ordre de charge | switch |
| `150` | consigne de courant | number |
| `151` | programmation JSON (`m`, `ss`, `se`) | lecture v1, écriture v1.1 |
| `152` | courant maximum configuré | diagnostic |
| `155` | NFC activé | lecture v1, écriture v1.1 |
| `156` | earth-free | diagnostic |
| `157` | variante produit | diagnostic |
| `188` | heartbeat | diagnostic |
| `189` | nombre de DP | diagnostic |

### 8.2 Décodage de `102`

- `L1[0] / 10` → tension en V ;
- `L1[1] / 10` → courant en A ;
- `t / 10` → température en °C ;
- `d / 10` → durée en secondes ;
- `e / 10` → énergie de session en kWh.

### 8.3 Décodage de `105`

- `t` → date de début ;
- `s` → début ;
- `e` → fin ;
- `d` → durée en secondes ;
- `c / 10` → énergie de la session en kWh.

---

## 9. Entités Home Assistant v1

### 9.1 Capteurs

| Entité | Unité | Classe | Remarque |
|---|---|---|---|
| `sensor.de_ev_status` | — | enum | état lisible |
| `sensor.de_ev_power` | W | power | mesure |
| `sensor.de_ev_voltage` | V | voltage | mesure |
| `sensor.de_ev_current` | A | current | mesure |
| `sensor.de_ev_temperature` | °C | temperature | mesure |
| `sensor.de_ev_energy_session` | kWh | energy | `total_increasing` |
| `sensor.de_ev_session_duration` | s | duration | diagnostic |
| `sensor.de_ev_last_session_energy` | kWh | energy | DP `105` |
| `sensor.de_ev_session_count` | — | — | nombre de sessions |
| `sensor.de_ev_work_state` | — | — | diagnostic |
| `sensor.de_ev_max_current_config` | A | current | diagnostic |
| `sensor.de_ev_product_variant` | — | — | diagnostic |
| `sensor.de_ev_raw_dps` | — | — | désactivé par défaut |

### 9.2 Binaires

| Entité | Détail |
|---|---|
| `binary_sensor.de_ev_charging` | charge en cours |
| `binary_sensor.de_ev_plugged` | véhicule branché |
| `binary_sensor.de_ev_fault` | défaut actif |

### 9.3 Commandes

| Entité | Détail |
|---|---|
| `switch.de_ev_charge_session` | start / stop |
| `number.de_ev_charge_current` | 6–16 A, pas de 1 A |

### 9.4 Entités futures

- `time.de_ev_schedule_start` / `time.de_ev_schedule_end` ;
- `switch.de_ev_schedule_enabled` ;
- `switch.de_ev_nfc_enabled` ;
- `button.de_ev_reboot` ;
- `button.de_ev_ready_to_charge`.

---

## 10. Config flow

### 10.1 Étape 1 — Cloud

Champs :

| Champ | Type | Obligatoire |
|---|---|---|
| Région | `eu`, `us`, `cn`, `in` | oui |
| Access ID / Client ID | texte | oui |
| Access Secret / Client Secret | mot de passe | oui |
| Device ID | texte | non |

Validation :

```python
cloud.getdevices()
```

avec un timeout de 30 secondes, exécuté dans un executor.

Erreurs :

- `cloud_auth_failed` : identifiants ou région invalides ;
- `cloud_no_devices` : projet Tuya non lié au compte, ou API non autorisée ;
- `cloud_timeout` : réseau ou service Tuya indisponible.

### 10.2 Étape 2 — Sélection de la borne

- filtre les appareils du compte ;
- affiche le nom, le modèle, l'ID et l'état en ligne ;
- récupère la clé locale dans le champ `key` / `local_key` ;
- récupère l'IP cloud éventuelle.

### 10.3 Étape 3 — Réseau local

- IP pré-remplie si disponible ;
- sinon scan UDP / TCP ;
- saisie manuelle possible ;
- protocole `3.5` par défaut, repli `3.4` / `3.3` ;
- validation par lecture réelle des DP.

Erreurs :

- `cannot_connect` : port fermé ou borne injoignable ;
- `invalid_auth` : clé locale invalide ;
- `invalid_protocol` : version de protocole incorrecte ;
- `port_busy` : un autre client local occupe la borne.

### 10.4 Étape 4 — Pièce HA

- sélecteur d'area Home Assistant ;
- optionnel ;
- affecte l'appareil via le device registry après création.

### 10.5 Données stockées dans la config entry

```text
access_id
access_secret
region
device_id
host
local_key
protocol_version
mac
area_id
```

### 10.6 Reauth / reconfigure / DHCP

- `reauth` si la clé locale a changé ;
- `reconfigure` pour l'IP ou les identifiants cloud ;
- `dhcp` discovery par MAC ;
- `unique_id = device_id`.

---

## 11. Coordinator

```python
class DeEvCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(self, hass, entry, client):
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            config_entry=entry,
        )
```

### 11.1 Règles

- polling local toutes les 30 s ;
- appels tinytuya dans un executor ;
- verrou `asyncio.Lock` + verrou interne côté client ;
- pas d'écriture si la valeur est identique ;
- relecture après écriture ;
- DP `140` en écriture seule : on vérifie l'état via `109` / `101`.

### 11.2 Gestion des erreurs

| Erreur | Comportement |
|---|---|
| `ChargerUnreachable` | `UpdateFailed`, tentative de redécouverte |
| `ChargerBusy` | `UpdateFailed`, message « Smart Life ouvert ? » |
| `ChargerAuthError` | `ConfigEntryAuthFailed` après 2–3 échecs |
| Cloud indisponible | on conserve la clé locale, pas de blocage |
| IP changée | redécouverte UDP/TCP, puis mise à jour du host |

---

## 12. Détection des sessions

### 12.1 Principe

La détection est **automatique et à la volée**. Elle ne dépend pas du cloud.

```text
IDLE
  │ branchement
  ▼
PLUGGED
  │ WORKING + courant > 0,5 A
  ▼
CHARGING
  │ plus de charge pendant 3 polls
  ▼
FINISHED
  │
  ▼
RECORDED
```

### 12.2 Début de session

Conditions :

- `status == "charging"` ou `do_charge == True` ;
- `current_a > 0.5` ;
- confirmé sur 2 polls consécutifs.

On enregistre :

- `started_at` en heure locale HA ;
- `start_energy_kwh` ;
- `peak_power_w` ;
- échantillons de puissance pour la moyenne.

### 12.3 Pendant la session

À chaque poll :

- mise à jour du pic de puissance ;
- mise à jour de la durée ;
- mise à jour de l'énergie courante ;
- sauvegarde périodique de la session active (toutes les 5 minutes).

### 12.4 Fin de session

Conditions :

- plus de charge pendant 3 polls consécutifs ;
- ou `status` passe à `STOP` / `IDLE` ;
- ou la signature DP `105` change.

### 12.5 Clôture

- si le DP `105` correspond à la session détectée, on utilise ses valeurs comme référence ;
- sinon on utilise les valeurs live ;
- on calcule `avg_power_w` ;
- on écrit la session dans le `Store` ;
- on met à jour `last_signature` ;
- on déclenche l'événement `de_ev_session_completed`.

### 12.6 Reprise après redémarrage

- la session active est restaurée depuis le `Store` ;
- si le DP `105` a changé pendant l'arrêt de HA, la session terminée est importée ;
- au premier ajout, la dernière session du DP `105` est importée ;
- déduplication par signature `(duration_s, energy_kwh)` + date de début.

### 12.7 Rétention

- 60 sessions par défaut ;
- configurable 30–200 ;
- liste complète accessible via le service `de_ev.get_sessions` ;
- attributs légers sur `sensor.de_ev_session_count` ;
- export CSV en v1.1.

---

## 13. Énergie et tableau de bord HA

### 13.1 Capteur principal

```python
native_unit_of_measurement = "kWh"
device_class = SensorDeviceClass.ENERGY
state_class = SensorStateClass.TOTAL_INCREASING
```

Le capteur `sensor.de_ev_energy_session` repart à zéro à chaque session. C'est compatible avec `TOTAL_INCREASING` : Home Assistant interprète la baisse comme un nouveau cycle.

### 13.2 Ajout dans HA

1. **Paramètres → Tableaux de bord → Énergie** ;
2. **Appareils individuels → Ajouter un appareil** ;
3. choisir `sensor.de_ev_energy_session`.

### 13.3 Ce que HA fait automatiquement

- consommation journalière et mensuelle ;
- statistiques long terme horaires ;
- graphiques natifs ;
- gestion des resets de session.

### 13.4 Ce que HA ne fait pas

- il ne devine pas l'appareil : il faut l'ajouter une fois ;
- il ne conserve pas la liste des sessions ;
- il ne calcule pas le coût par appareil dans le dashboard Énergie ;
- il ne remplace pas l'historique détaillé du `Store`.

---

## 14. Sécurité

- Ne jamais logger l'Access Secret ni la clé locale.
- Masquer les secrets dans `diagnostics.py`.
- Stocker les secrets dans la config entry HA.
- Ne pas committer de `.env`, de token ou de clé locale.
- Ne pas exposer la borne sur Internet.
- Garder le contrôle local comme source de vérité.
- Limiter le courant au calibre du disjoncteur et à la section du câble.
- Ne pas tester 16 A si l'installation n'est pas dimensionnée.

---

## 15. Développement pas à pas

### Phase 0.2 — Environnement de développement Docker

**But** : disposer d'un Home Assistant jetable, préconfiguré et réutilisable,
avec le composant monté, pour tester chaque phase sans toucher à l'instance de
production.

**Prérequis** : Docker Desktop avec l'intégration WSL2 activée (ou Docker
Engine sous Linux), Docker Compose v2, `make` et Python 3.

Tâches :

- ajouter un `Makefile` réutilisable ;
- ajouter `sandbox/docker-compose.yml` avec l'image
  `ghcr.io/home-assistant/home-assistant:stable` ;
- monter le composant en lecture seule dans
  `/config/custom_components/<domaine>` ;
- ajouter une configuration HA minimale (`default_config`, localisation,
  logs debug) ;
- ajouter un script d'onboarding best-effort via l'API HA ;
- ajouter un `.gitignore` pour `.storage`, la base et les logs ;
- documenter la réutilisation dans `sandbox/README.md`.

Commandes :

```bash
make dev       # démarre HA + onboarding
make logs      # suit les logs
make config    # vérifie la configuration HA
make down      # arrête
make reset     # repart d'un HA vierge
make compose-config
```

**Réutilisation** :

```bash
make dev COMPONENT_NAME=mon_integration HA_PORT=8124
```

**Critère d'acceptation** :

- `make dev` démarre HA sur `http://127.0.0.1:8123` ;
- le composant apparaît dans « Ajouter une intégration » et le config flow
  démarre ;
- `make config` valide la configuration ;
- `make down` arrête proprement le conteneur ;
- le même `Makefile` fonctionne pour un autre composant en changeant
  `COMPONENT_NAME`.

> Si `docker` n'est pas trouvé dans WSL2, activer l'intégration de la
> distribution dans Docker Desktop : **Settings → Resources → WSL Integration**.

### Phase 0.1 — Bootstrap de l'intégration

**But** : avoir un squelette installable dans Home Assistant.

Tâches :

- compléter le squelette existant de `custom_components/de_ev/` ;
- remplacer le manifest placeholder par le manifest v0.1 avec `tinytuya` ;
- compléter `strings.json` et les traductions ;
- ajouter `pyproject.toml`, `ruff`, `pytest`,
  `pytest-homeassistant-custom-component` ;
- ajouter `hacs.json` ;
- ajouter le workflow CI ;
- compléter le README d'installation.

**Critère d'acceptation** :

- l'intégration apparaît dans « Ajouter une intégration » ;
- le config flow démarre ;
- `ruff check` et `pytest` passent.

### Phase 1 — Domaine et profils

**But** : décoder les DP sans dépendre de Home Assistant.

Tâches :

- créer `profiles.py` à partir du POC ;
- définir `Snapshot` ;
- implémenter `decode()` pour `depow_v2` ;
- gérer `current_shortcuts` et `last_session` ;
- ajouter des échantillons de DP dans les tests ;
- tester les échelles et les valeurs limites.

**Critère d'acceptation** :

- un jeu de DP réel produit un `Snapshot` correct ;
- les tests couvrent `6 A`, `11 A`, `16 A`, l'énergie, la température et la dernière session.

### Phase 2 — Cloud et client local

**But** : récupérer la clé locale et lire la borne.

Tâches :

- créer `cloud.py` ;
- gérer les régions et le fallback de signature ;
- extraire `id`, `name`, `local_key`, `ip`, `category`, `online` ;
- créer `charger.py` ;
- gérer le verrou, les timeouts et les erreurs ;
- implémenter la lecture des DP et l'écriture vérifiée ;
- mocker tinytuya dans les tests.

**Critère d'acceptation** :

- connexion réelle à la borne ;
- lecture de tous les DP ;
- start/stop et courant vérifiés ;
- erreurs `port occupé`, `clé invalide`, `injoignable` correctement classées.

### Phase 3 — Config flow

**But** : ajouter la borne avec uniquement les identifiants cloud.

Tâches :

- étape cloud ;
- étape sélection de la borne ;
- étape IP / protocole ;
- étape pièce HA optionnelle ;
- création de la config entry ;
- `reauth`, `reconfigure`, `dhcp` ;
- options flow.

**Critère d'acceptation** :

- ajout complet sans saisir la clé locale ;
- mauvais identifiants → erreur claire ;
- projet sans borne → erreur claire ;
- mauvaise clé locale → erreur claire ;
- redémarrage HA → l'entrée reste valide.

### Phase 4 — Coordinator et entités

**But** : exposer les données et les commandes dans HA.

Tâches :

- créer `coordinator.py` ;
- créer `entity.py` ;
- créer les plateformes `sensor`, `binary_sensor`, `switch`, `number` ;
- ajouter les traductions ;
- ajouter `device_info` ;
- ajouter les entités diagnostic ;
- gérer la disponibilité.

**Critère d'acceptation** :

- toutes les entités v1 sont créées ;
- les valeurs correspondent au POC ;
- les commandes fonctionnent ;
- les entités non supportées sont indisponibles proprement.

### Phase 5 — Sessions

**But** : historique automatique des recharges.

Tâches :

- créer `sessions.py` ;
- charger / sauvegarder le `Store` ;
- implémenter la machine à états ;
- gérer la reprise après redémarrage ;
- dédupliquer ;
- importer la dernière session du DP `105` ;
- exposer `session_count`, `last_session_energy` ;
- ajouter le service `get_sessions` ;
- déclencher l'événement de fin de session.

**Critère d'acceptation** :

- une charge réelle crée une session ;
- un redémarrage ne crée pas de doublon ;
- une session terminée pendant l'arrêt de HA est importée ;
- la rétention fonctionne.

### Phase 6 — Énergie

**But** : dashboard Énergie natif.

Tâches :

- ajouter `device_class` et `state_class` ;
- vérifier les unités ;
- documenter l'ajout dans le dashboard ;
- tester un cycle de charge ;
- vérifier le comportement après reset ;
- vérifier les statistiques long terme.

**Critère d'acceptation** :

- la consommation apparaît dans le dashboard ;
- le total continue après un reset ;
- les statistiques survivent à un redémarrage.

### Phase 7 — Robustesse

**But** : rendre l'intégration fiable au quotidien.

Tâches :

- redécouverte IP ;
- rafraîchissement de clé locale throttlé ;
- repair issues ;
- diagnostics ;
- messages d'erreur utilisateur ;
- logs sans secrets ;
- gestion des timeouts.

**Critère d'acceptation** :

- IP changée → récupération ;
- Smart Life ouvert → message clair ;
- clé changée → reauth ;
- cloud indisponible → le local continue.

### Phase 8 — Packaging et validation réelle

**But** : pouvoir installer et utiliser l'intégration.

Tâches :

- README final ;
- `hacs.json` ;
- installation manuelle documentée ;
- test sur borne réelle ;
- validation des courants 6, 11 et 16 A si installation adaptée ;
- validation du dashboard Énergie ;
- validation après redémarrage HA ;
- tag `v0.1.0`.

**Critère d'acceptation** :

- installation propre ;
- aucune erreur dans les logs ;
- fonctionnalités v1 validées ;
- documentation à jour.

---

## 16. Tests

### 16.1 Tests unitaires

- `test_config_flow.py` : cloud OK, auth KO, aucun appareil, sélection, IP, area, reauth.
- `test_coordinator.py` : poll, erreurs, redécouverte, auth.
- `test_sessions.py` : début, fin, reprise, déduplication, rétention.
- `test_sensors.py` : unités, classes, disponibilité, `total_increasing`.
- `test_diagnostics.py` : secrets masqués.

### 16.2 Tests manuels

- ajout avec identifiants cloud ;
- lecture de tous les capteurs ;
- start / stop ;
- courant 6 A, 11 A, 16 A ;
- fin de session ;
- dashboard Énergie ;
- redémarrage HA ;
- changement d'IP simulé ;
- Smart Life ouvert ;
- mauvaise clé locale.

### 16.3 Outils

```bash
ruff check .
pytest -q
```

---

## 17. Installation

### 17.1 Développement Docker

Pour développer sans toucher à l'instance de production :

```bash
make dev
```

Prérequis : Docker avec intégration WSL2, Docker Compose v2, `make` et Python 3.
L'interface est disponible sur <http://127.0.0.1:8123>. Le script d'onboarding
crée le compte `dev` et affiche le mot de passe ; en cas d'échec, créer le
compte dans l'interface. Le compte et la locale se règlent dans
`sandbox/config.yaml`, créé depuis `sandbox/config.example.yaml` et ignoré par
Git. Un mot de passe vide est généré aléatoirement.

Le composant est monté depuis `custom_components/de_ev` en lecture seule. Après
une modification, redémarrer HA (`make restart`) ou utiliser le redémarrage
rapide de l'interface.

Commandes utiles : `make logs`, `make config`, `make down`, `make reset`.
Voir [`sandbox/README.md`](sandbox/README.md) pour la réutilisation et les
variables.

### 17.2 Manuelle

```bash
cp -r custom_components/de_ev /config/custom_components/
```

Puis :

1. redémarrer Home Assistant ;
2. **Paramètres → Appareils et services → Ajouter une intégration** ;
3. chercher **Dé EV Charger** ;
4. saisir la région, l'Access ID et l'Access Secret ;
5. sélectionner la borne ;
6. valider l'IP et le protocole ;
7. choisir la pièce.

### 17.3 HACS

Le dépôt est structuré avec `custom_components/de_ev/` à la racine, donc il pourra être ajouté comme dépôt personnalisé HACS lorsque la v1 sera publiée.

---

## 18. Configuration Tuya Cloud

1. Créer un projet sur <https://iot.tuya.com>.
2. Choisir la région correspondant au compte (ex. `eu`).
3. Lier le compte Smart Life / Tuya au projet.
4. Autoriser les API nécessaires :
   - Device Control ;
   - Device Status ;
   - Smart Home Basic Service.
5. Récupérer l'`Access ID` et l'`Access Secret`.
6. Vérifier que la borne apparaît dans `getdevices`.

> L'`Access Secret` ne doit jamais être commité. La clé locale n'est pas l'Access Secret.

---

## 19. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `cloud_auth_failed` | identifiants ou région incorrects | vérifier le projet Tuya |
| `cloud_no_devices` | compte non lié / API non autorisée | lier le compte et activer les API |
| `cannot_connect` | IP incorrecte ou borne hors ligne | vérifier le réseau, rescanner |
| `port_busy` | Smart Life ou Tuya ouvert | fermer l'application |
| `invalid_auth` | clé locale incorrecte | reauth / réappairage |
| `invalid_protocol` | version 3.5 incorrecte | tester 3.4 / 3.3 |
| entité indisponible | DP absent du firmware | désactiver l'entité |
| dashboard vide | capteur non ajouté | ajouter dans Énergie |
| historique vide | première session pas encore terminée | attendre la fin de charge |
| `docker: command not found` | intégration WSL2 désactivée | activer Docker Desktop → WSL Integration |
| `port is already allocated` | port 8123 occupé | `make dev HA_PORT=8124` |
| onboarding automatique en échec | API HA changée / instance déjà configurée | finir dans l'UI ou `make reset` |

---

## 20. Roadmap

### Outillage — phase 0.2 (avant v0.1.0)

Cette étape n'est pas une version produit : elle précède la v0.1.0.

- `Makefile` réutilisable ;
- environnement Docker Compose Home Assistant ;
- montage en lecture seule du composant ;
- onboarding automatique best-effort ;
- configuration YAML locale (`sandbox/config.yaml`, ignorée par Git) ;
- documentation de réutilisation.

### v0.1.0

- config flow cloud ;
- connexion locale ;
- entités v1 ;
- sessions ;
- dashboard Énergie ;
- diagnostics ;
- reauth.

### v0.2.0

- programmation horaire ;
- NFC ;
- reboot ;
- export CSV ;
- capteur d'énergie totale.

### v0.3.0

- coût par session ;
- heures creuses / pleines ;
- notifications ;
- carte Lovelace.

### v1.0.0

- support multi-bornes ;
- support `qccdz_v1` ;
- HACS ;
- documentation complète.

---

## 21. Décisions de conception

| Sujet | Décision |
|---|---|
| Base | projet from scratch, pas de fork |
| Environnement de dev | Docker Compose + Makefile réutilisable (phase 0.2) |
| Montage dev | composant en lecture seule dans `/config/custom_components/<domaine>` |
| Onboarding dev | API HA, fallback UI |
| Cloud | bootstrap uniquement |
| Contrôle | local |
| Zone | région Tuya + area HA optionnelle |
| Historique | détection live + `Store` JSON |
| Rétention | 60 sessions par défaut |
| Dashboard | `sensor.energy_session` en `total_increasing` |
| Secrets | config entry HA, jamais loggés |
| HACS | après la v1 |
| Licence | à définir |

---

## 22. Crédits

- [tinytuya](https://github.com/jasonacox/tinytuya) pour le protocole Tuya local.
- [lachand/EV_charger](https://github.com/lachand/EV_charger) pour les constantes DP et les profils connus.
- POC local `poc-ev` pour la validation du décodage, du contrôle et des sessions.

---

## 23. Prochaine étape

Valider la **phase 0.2** (`make dev`, `make config`, `make down`), puis passer à
la **phase 0.1** : compléter le squelette `custom_components/de_ev`, le
manifest, les traductions, la CI et les premiers tests.
