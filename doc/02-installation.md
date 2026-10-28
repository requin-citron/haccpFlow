# Installation et démarrage

## Prérequis

- Docker Engine et Docker Compose v2.
- Ports libres : `3000` (frontend), `8000` (API), `5432` et `1883` en local
  uniquement.
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
docker compose --profile app up -d --build
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

### Profils Compose

| Commande | Services démarrés |
| --- | --- |
| `docker compose up -d` | `db`, `mosquitto` |
| `docker compose --profile app up -d` | toute la pile |
| `docker compose --profile app up -d backend frontend` | backend + frontend + dépendances |

Le profil `app` est volontaire : un `docker compose up -d` seul ne lance pas
l'application.

## Premier administrateur

`ADMIN_EMAIL` et `ADMIN_PASSWORD` sont lus au démarrage. L'utilisateur est créé
uniquement si la table est vide ; le mot de passe n'est jamais réécrit si le
compte existe déjà.

La gestion des comptes est disponible via l'API admin (`/api/v1/users`) ; le
frontend correspondant n'est pas encore présent. Les mots de passe générés sont
retournés une seule fois lors de la création ou de la réinitialisation.

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
| Code backend | `docker compose --profile app restart backend` (le code est monté) |
| Code frontend | rechargement à chaud du serveur Next.js |
| Dépendances backend | rebuild de l'image backend |
| `Dockerfile` ou dépendances frontend | `docker compose --profile app build backend frontend` puis `up -d` |
| Nouvelle migration | redémarrer le backend : Alembic applique `head` au démarrage |
| `.env` | `docker compose --profile app up -d` pour recréer les conteneurs |

## Réinitialiser une instance de développement

```sh
docker compose --profile app down -v
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
