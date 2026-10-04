# haccpFlow

Plateforme open source de gestion HACCP, pensée pour être installée **une
instance par client**. Elle couvre aujourd'hui deux volets du plan de maîtrise
sanitaire :

- **Chaîne du froid** — parc de matériel (frigos, congélateurs) avec seuils
  réglementaires, relevés matin et soir, et journal des corrections.
- **Plan de nettoyage et de désinfection (PND)** — zones et matériels à
  nettoyer, fréquences, produits, déclarations de nettoyage, prévisionnel et
  liste du retard.
- **Pasteurisation** — registre des lots (date, produit, numéro de lot,
  quantité) et suivi de leurs trois phases : préchauffage, palier, puis
  refroidissement, chacune avec ses heures, sa température cible et ses
  observations.
- **Transport** — référentiel des véhicules (nom et plaque) et registre des
  déplacements : lieu, produit, lot, puis les relevés de chaîne du froid au
  départ et à l'arrivée.
- **Export CSV** — quatre extractions prêtes pour Excel (relevés, nettoyages,
  pasteurisation, transport) filtrables par période, désactivés compris, pour
  répondre à un contrôle ou archiver.
- **Caisses** — enrôlement d'une caisse avec son comptage initial, coupure par
  coupure, des pièces de 1 centime aux billets de 50 euros.

L'enrôlement de capteurs Zigbee2MQTT viendra compléter les relevés manuels.

## Stack

| Composant | Technologie |
| --- | --- |
| Backend | FastAPI, Python 3.13, SQLAlchemy 2 async, Alembic, `uv` |
| Frontend | Next.js (App Router), React, TypeScript strict, Tailwind CSS, `yarn` |
| Base de données | PostgreSQL 16 |
| Messagerie | Eclipse Mosquitto (MQTT) |
| Ingestion Zigbee | Zigbee2MQTT, **hors de cette stack** : il tourne on-premise avec les capteurs et publie sur le broker |
| Déploiement | Docker Compose |

## Démarrage rapide

```sh
cp .env.example .env        # puis renseigner les secrets (voir plus bas)
docker compose --profile app up -d backend frontend
```

- Application : http://localhost:3000
- Documentation interactive de l'API : http://localhost:8000/docs
- Le premier démarrage applique les migrations puis crée l'administrateur à
  partir de `ADMIN_EMAIL` / `ADMIN_PASSWORD`.

`backend` et `frontend` sont derrière le profil `app` : un simple
`docker compose up -d` ne démarre que la base et le broker, tandis que le
profil `app` lance toute la pile.

## Services et ports

| Service | Port publié | Rôle |
| --- | --- | --- |
| `db` | `127.0.0.1:5432` | PostgreSQL |
| `mosquitto` | `127.0.0.1:1883` | Broker MQTT (auth obligatoire) |
| `backend` | `0.0.0.0:8000` | API FastAPI |
| `frontend` | `0.0.0.0:3000` | Interface Next.js |

Les ports de la base et du broker sont volontairement limités à `127.0.0.1` :
ils servent à l'outillage local, pas au réseau. Le navigateur ne parle qu'au
frontend, qui relaie vers l'API côté serveur — les jetons ne sont donc jamais
exposés au navigateur.

## Configuration

Toute la configuration passe par des variables d'environnement, regroupées dans
`.env.example`. Les valeurs vides marquées **requis** font échouer `docker
compose` au démarrage plutôt que de laisser tourner une instance mal
configurée.

### Exécution

| Variable | Défaut | Description |
| --- | --- | --- |
| `TZ` | `UTC` | Fuseau des conteneurs. Les horodatages sont stockés en UTC. |
| `ENVIRONMENT` | `development` | `production` active le mode production côté backend. |
| `LOG_LEVEL` | `info` | Niveau de journalisation du backend. |

### PostgreSQL

| Variable | Défaut | Description |
| --- | --- | --- |
| `POSTGRES_USER` | `haccp` | **Requis.** Utilisateur de la base. |
| `POSTGRES_PASSWORD` | — | **Requis.** Générer avec `openssl rand -hex 32`. |
| `POSTGRES_DB` | `haccp` | **Requis.** Nom de la base. |
| `POSTGRES_PORT` | `5432` | Port publié sur `127.0.0.1` pour l'outillage. |

### MQTT

| Variable | Défaut | Description |
| --- | --- | --- |
| `MQTT_USERNAME` | `haccp` | **Requis.** Les connexions anonymes sont refusées. |
| `MQTT_PASSWORD` | — | **Requis.** Le fichier de mots de passe est reconstruit à chaque démarrage depuis cette valeur. |
| `MQTT_PORT` | `1883` | Port publié sur `127.0.0.1`. |
| `MQTT_TOPIC_PREFIX` | `zigbee2mqtt` | Préfixe sous lequel Zigbee2MQTT publie ; le backend s'abonnera en dessous. |

Le backend reçoit aussi `MQTT_HOST` et `MQTT_PORT`, fixés par le compose : ce
sont des valeurs internes au réseau Docker. `MQTT_CLIENT_ID` (défaut
`haccpflow-backend`) n'est utile que si plusieurs backends partagent un broker.

### Backend et authentification

| Variable | Défaut | Description |
| --- | --- | --- |
| `SECRET_KEY` | — | **Requis.** Signe les jetons JWT. Générer avec `openssl rand -hex 32`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Durée de vie du jeton d'accès. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Durée de vie du refresh token, révocable et renouvelé à chaque usage. |
| `DOCS_ENABLED` | `true` | Expose `/docs`, `/redoc` et `/openapi.json`. À passer à `false` en production. |
| `PUBLIC_API_URL` | *(vide)* | URL absolue inscrite dans l'entrée `servers` de l'OpenAPI. |
| `CORS_ORIGINS` | `http://localhost:3000` | Origines autorisées, séparées par des virgules. Inutile en pratique : le frontend appelle l'API côté serveur. |
| `BACKEND_PORT` | `8000` | Port publié de l'API. |

### Premier administrateur

| Variable | Défaut | Description |
| --- | --- | --- |
| `ADMIN_EMAIL` | `admin@example.com` | **Requis par compose.** Compte créé au premier démarrage. |
| `ADMIN_PASSWORD` | — | **Requis par compose.** N'est jamais réécrit si l'utilisateur existe déjà. |

### Seuils de température par défaut (°C)

Utilisés uniquement quand un matériel est créé **sans** seuils explicites. Chaque
équipement stocke ensuite ses propres valeurs, et les seuils ne sont jamais
codés en dur dans la logique : ce sont ces variables qui font foi.

| Variable | Défaut | Description |
| --- | --- | --- |
| `DEFAULT_FRIDGE_MIN_TEMPERATURE_C` | `0` | Seuil bas d'un réfrigérateur. |
| `DEFAULT_FRIDGE_MAX_TEMPERATURE_C` | `4` | Seuil haut d'un réfrigérateur. |
| `DEFAULT_FREEZER_MIN_TEMPERATURE_C` | `-25` | Seuil bas d'un congélateur. |
| `DEFAULT_FREEZER_MAX_TEMPERATURE_C` | `-18` | Seuil haut d'un congélateur. |

### Frontend

| Variable | Défaut | Description |
| --- | --- | --- |
| `FRONTEND_PORT` | `3000` | Port publié de l'interface. |
| `SESSION_COOKIE_SECURE` | `false` | À passer à `true` dès que l'application est servie en HTTPS : les cookies de session deviennent `Secure`. |

Le frontend reçoit `API_INTERNAL_URL` (`http://backend:8000`), fixé par le
compose : c'est l'adresse utilisée pour les appels serveur à serveur.

## Rôles et accès

Deux rôles existent : `admin` et `operator`. L'autorisation est **toujours
vérifiée côté backend** ; l'interface ne fait que masquer les actions
inaccessibles.

| Fonctionnalité | Opérateur | Administrateur |
| --- | :---: | :---: |
| Consulter le matériel | ✅ | ✅ |
| Créer et modifier un matériel | ✅ | ✅ |
| Désactiver un matériel | ❌ | ✅ |
| Saisir, compléter et corriger un relevé de température | ✅ | ✅ |
| Consulter l'historique des modifications (onglet Historique) | ❌ | ✅ |
| Consulter les plans de nettoyage | ✅ | ✅ |
| Créer et modifier un plan de nettoyage | ✅ | ✅ |
| Désactiver un plan de nettoyage | ❌ | ✅ |
| Déclarer, corriger ou supprimer un nettoyage | ✅ | ✅ |
| Consulter le prévisionnel et la liste du retard | ✅ | ✅ |
| Consulter les lots de pasteurisation | ✅ | ✅ |
| Créer un lot et enregistrer ses phases | ✅ | ✅ |
| Corriger une phase de pasteurisation | ✅ | ✅ |
| Désactiver un lot de pasteurisation | ❌ | ✅ |
| Consulter les véhicules et les transports | ✅ | ✅ |
| Créer un véhicule et déclarer un transport | ✅ | ✅ |
| Désactiver un véhicule ou un transport | ❌ | ✅ |
| Enrôler une caisse et corriger son comptage | ✅ | ✅ |
| Désactiver une caisse | ❌ | ✅ |
| Lister les utilisateurs | ❌ | ✅ |

En résumé : l'opérateur fait le quotidien, l'administrateur est seul à pouvoir
retirer quelque chose du référentiel.

> **Limite connue** : il n'existe pas encore de route de gestion des
> utilisateurs. Seul l'administrateur initial est créé au démarrage. Ajouter un
> opérateur demande pour l'instant une insertion en base.

## Développement

### Backend

```sh
cd backend
uv sync                                   # une fois
export SECRET_KEY=$(openssl rand -hex 32)
export DATABASE_URL="postgresql+asyncpg://haccp:<mot de passe>@localhost:5432/haccp"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Qualité : `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.

Le code est monté dans le conteneur : une modification se prend en compte en
**redémarrant** le service (`docker compose restart backend`).

### Frontend

```sh
cd frontend
yarn install
yarn dev
```

Qualité : `yarn typecheck`, `yarn build`.

Le service tourne en mode développement avec le code monté : les modifications
sont rechargées à chaud, sans reconstruction d'image.

### Migrations

Chaque évolution du modèle ajoute une révision dans
`backend/alembic/versions/`. Le conteneur backend applique `alembic upgrade
head` à chaque démarrage, ce qui est sûr puisqu'il n'y a qu'une instance par
client.

### Scénarios de vérification

Le dossier `scenario/` contient des scripts autonomes pour peupler une instance
de développement et vérifier les parcours de bout en bout, sans passer par
l'interface. Voir [`scenario/README.md`](scenario/README.md) pour le détail de
ce que fait chaque script.

```sh
python3 scenario/seed_cleaning.py
python3 scenario/check_cleaning_api.py
```

## Tests

La suite backend compte plus de 240 tests : des tests unitaires sans aucune
dépendance, et des tests d'intégration sur un PostgreSQL jetable.

```sh
docker compose up -d db
cd backend
export TEST_DATABASE_URL="postgresql+asyncpg://haccp:<mot de passe>@localhost:5432/haccp_test"
uv run pytest
```

Chaque session de test crée sa propre base `haccp_test_<pid>`, y applique les
migrations, puis la supprime : deux exécutions simultanées ne se marchent pas
dessus.

## Sécurité

- Aucun secret dans le dépôt : tout vient de l'environnement, `.env` est ignoré
  par git.
- Jetons JWT en cookies `httpOnly` ; le navigateur ne détient jamais de jeton,
  et l'accès à l'API se fait côté serveur.
- Mots de passe hachés en Argon2id, refresh tokens opaques stockés hachés et
  révoqués en cas de rejeu.
- Autorisations vérifiées sur chaque route, jamais dans l'interface seule.
- Seuils HACCP configurables par matériel, jamais figés dans le code.
- Modifications des relevés et des nettoyages journalisées : auteur, valeur
  précédente et horodatage.
- Base et broker non exposés hors de `127.0.0.1`.

## Feuille de route

- Enrôlement de capteurs et ingestion MQTT : les relevés automatiques viendront
  compléter les créneaux laissés vides (`source = sensor` est déjà prévu).
- Alerte quand un lot de pasteurisation reste incomplet.
- Gestion des utilisateurs depuis l'interface.
- Listener TLS sur le broker pour les sites on-premise.
- Export du plan de maîtrise sanitaire en PDF.

## Licence

GNU Affero General Public License v3.0 — voir [LICENSE](LICENSE).
