# Installation et démarrage

## Prérequis

- Docker Engine et Docker Compose v2.
- Ports libres : `3000` (frontend), `8000` (API), `5432` et `1883` en local
  uniquement. Traefik, s'il est déjà installé, écoute séparément sur `80`/`443`.
- Pour le développement hors Docker : Python 3.13, `uv`, Node.js compatible avec
  Next.js 16, `yarn` 1.22.
- Pour recompiler les PDF localement : TeX Live avec `pdflatex` et les paquets
  LaTeX (déjà présents dans l'image backend).

## Démarrage complet avec Docker

```sh
cd /chemin/vers/haccpFlow
cp .env.example .env
```

Renseigner au minimum dans `.env` :

- `POSTGRES_PASSWORD`
- `MQTT_PASSWORD`
- `SECRET_KEY` (`openssl rand -hex 32`)
- `ADMIN_PASSWORD`

Puis :

```sh
docker compose up -d --build
docker compose ps
```

| Accès | URL |
| --- | --- |
| Application | http://localhost:3000 |
| API OpenAPI (si `DOCS_ENABLED=true`) | http://localhost:8000/docs |
| Santé API | http://localhost:8000/health/live |
| Disponibilité complète | http://localhost:8000/health/ready |

Au premier démarrage, le backend attend PostgreSQL et Mosquitto, applique les
migrations Alembic, puis crée l'administrateur si la table `users` est vide.

### Démarrage et arrêt

| Commande | Services démarrés |
| --- | --- |
| `docker compose up -d` | toute la pile : `db`, `mosquitto`, `backend`, `frontend` |
| `docker compose up -d db mosquitto` | infrastructure seule |
| `docker compose up -d backend` | backend et ses dépendances |

`docker compose down` arrête et retire tous les conteneurs et le réseau Compose.
Sans l'option `-v`, les volumes PostgreSQL et MQTT sont conservés.

## Déploiement release

Le compose racine est prévu pour le développement : il utilise la cible Next.js
`development`, monte les sources et publie les ports sur toutes les interfaces.
La release ajoute uniquement `docker-compose.release.yml` :

| Fichier | Rôle |
| --- | --- |
| `docker-compose.yml` | Définition commune des services |
| `docker-compose.release.yml` | Images de production, cookies sécurisés, ports locaux |

Le fichier release ne crée ni réseau Traefik, ni routeur, ni certificat, ni port
hôte. Il prépare des labels vides que l'administrateur renseigne directement
dans le compose selon son installation Traefik existante.

### Configuration

```sh
cp .env.example .env
```

Renseigner les secrets habituels. Aucune variable Traefik n'est demandée dans
`.env` : les labels sont à compléter directement dans
`docker-compose.release.yml`.

Le service frontend écoute sur `3000` uniquement dans le réseau Compose. Aucun
port hôte n'est publié pour le frontend ni pour le backend. Ton instance
Traefik doit être raccordée au réseau Docker Compose pour router directement
vers ces services.

### Démarrage

```sh
docker compose \
  -f docker-compose.yml \
  -f docker-compose.release.yml \
  up -d --build
docker compose \
  -f docker-compose.yml \
  -f docker-compose.release.yml \
  ps
```

La publication du domaine, le routage et les certificats restent gérés par
Traefik déjà présent sur le serveur.

Le fichier `docker-compose.release.yml` :

- construit le frontend avec la cible `runner` et `NODE_ENV=production` ;
- force `SESSION_COOKIE_SECURE=true` et `ENVIRONMENT=production` ;
- désactive `/docs`, `/redoc` et `/openapi.json` ;
- remplace le montage des sources backend par le seul volume durable
  `./backend/data:/app/data` ;
- ne publie aucun port hôte pour frontend/backend.

### Mise à jour

```sh
git pull --ff-only
docker compose \
  -f docker-compose.yml \
  -f docker-compose.release.yml \
  up -d --build
```

Les migrations Alembic sont appliquées au redémarrage du backend. Les volumes
PostgreSQL, Mosquitto et `backend/data` sont conservés.

### Arrêt

Utiliser la même liste de fichiers pour cibler la bonne composition :

```sh
docker compose \
  -f docker-compose.yml \
  -f docker-compose.release.yml \
  down
```

Sans `-v`, aucune donnée persistante n'est supprimée.

## Premier administrateur

`ADMIN_EMAIL` et `ADMIN_PASSWORD` sont lus au démarrage. L'utilisateur est créé
uniquement si la table est vide ; le mot de passe n'est jamais réécrit si le
compte existe déjà.

La gestion des comptes est disponible dans la page admin `/users` et via l'API
(`/api/v1/users`). Les mots de passe générés sont retournés une seule fois lors
de la création ou de la réinitialisation.

## Développement local

### Infrastructure seule

```sh
docker compose up -d db mosquitto
```

### Backend

```sh
cd backend
uv sync
export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="postgresql+asyncpg://haccp:<mot_de_passe>@localhost:5432/haccp"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

### Frontend

```sh
cd frontend
yarn install
API_INTERNAL_URL=http://localhost:8000 yarn dev
```

`API_INTERNAL_URL` est l'adresse utilisée par le serveur Next.js pour joindre
FastAPI. En Docker elle vaut `http://backend:8000`.

## Cycle de modification

| Changement | Action |
| --- | --- |
| Code backend | `docker compose restart backend` (le code est monté) |
| Code frontend | rechargement à chaud du serveur Next.js |
| Dépendances backend | rebuild de l'image backend |
| `Dockerfile` ou dépendances frontend | `docker compose build backend frontend` puis `docker compose up -d` |
| Nouvelle migration | redémarrer le backend : Alembic applique `head` au démarrage |
| `.env` | `docker compose up -d` pour recréer les conteneurs |

## Réinitialiser une instance de développement

```sh
docker compose down -v
```

**Attention** : `-v` supprime la base PostgreSQL et les volumes MQTT. Les
fichiers LaTeX/PDF sous `backend/data/` ne sont pas dans un volume Docker et
doivent être supprimés séparément si nécessaire.

## Jeu de démonstration

Les scripts de `scenario/` parlent à une instance déjà démarrée et lisent les
identifiants admin dans `.env` :

```sh
python3 scenario/seed_equipment.py
python3 scenario/seed_cleaning.py
python3 scenario/seed_pasteurisation.py
python3 scenario/seed_transport.py
python3 scenario/seed_delivery_note.py
```

Voir [scenario/README.md](../scenario/README.md) pour le détail.

## Vérifications

```sh
# Tests backend avec PostgreSQL jetable
docker compose up -d db
cd backend
export TEST_DATABASE_URL="postgresql+asyncpg://haccp:<mot_de_passe>@localhost:5432/haccp_test"
uv run pytest

# Qualité backend
uv run ruff check .
uv run ruff format --check .
uv run mypy

# Frontend
cd ../frontend
yarn typecheck
yarn build
```

La base de test est créée sous `haccp_test_<pid>`, migrée puis supprimée : deux
exécutions parallèles ne se marchent pas dessus.
