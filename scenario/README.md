# Scénarios de vérification

Scripts Python autonomes (bibliothèque standard uniquement) pour peupler une
instance de développement et vérifier les parcours de bout en bout, sans passer
par l'interface.

## Prérequis

L'infra et le backend tournent :

```sh
docker compose --profile app up -d backend     # db + mosquitto + backend
```

Les scripts lisent `ADMIN_EMAIL` et `ADMIN_PASSWORD` dans le `.env` de la racine
et parlent à l'API sur `http://127.0.0.1:8000`. Ceux qui vérifient le frontend
supposent en plus le service `frontend` sur `http://127.0.0.1:3000` :

```sh
docker compose --profile app up -d frontend
```

## Jeu de démonstration

| Script | Ce qu'il crée |
| --- | --- |
| `seed_equipment.py` | Trois équipements : deux frigos (dont un avec seuils explicites) et un congélateur. |
| `seed_cleaning.py` | Quatre plans de nettoyage couvrant tous les états — un en retard, un à faire aujourd'hui, un à venir, un après chaque usage — avec leurs déclarations et une correction de date pour alimenter le journal. |
| `seed_pasteurisation.py` | Trois lots de pasteurisation : un complet, un en cours (préchauffage seul) et un vide, pour voir les trois états dans l'interface. |

Les deux sont **idempotents** : un nom déjà présent est ignoré, on peut les
relancer sans créer de doublon.

## Vérifications

| Script | Ce qu'il vérifie |
| --- | --- |
| `check_equipment_api.py` | Création avec seuils par défaut, doublon insensible à la casse (409), modification, suppression douce puis 404. |
| `check_readings_api.py` | Saisie du matin seul puis complétion du soir sans écraser l'existant, correction tracée dans l'historique, conformité recalculée, date antidatée acceptée, date trop future et température impossible refusées. |
| `check_cleaning_api.py` | Cycle de vie d'un plan, déclarations multiples le même jour, correction et suppression auditées, calcul du prévisionnel et de la liste du retard. |
| `check_pasteurisation_api.py` | Cycle de vie d'un lot de pasteurisation, remplissage progressif des trois phases (préchauffage, palier, refroidissement), durée calculée, correction auditée, refus d'une fin antérieure au début, recherche par numéro de lot. |
| `check_frontend_pages.py` | Les pages Matériel, Relevés, Nettoyage, Pasteurisation et Historique rendent les données du serveur avec une session, et renvoient vers la connexion sans session, sans fuite de données. |
| `check_cleaning_tabs.py` | La séparation entre l'onglet opérationnel (déclarer) et l'onglet de gestion (créer, modifier), ainsi que le contenu de l'agenda. |

Les vérifications suppriment les données qu'elles ont créées avant de se
terminer.

## Exécution

```sh
python3 scenario/seed_cleaning.py
python3 scenario/check_cleaning_api.py
```

Chaque script affiche un rapport lisible et sort en code 1 si une vérification
échoue : utilisable tel quel dans un enchaînement `&&`.

## Tests d'intégration du backend

Indépendamment de ces scénarios, la suite pytest a besoin d'un PostgreSQL :

```sh
docker compose up -d db
cd backend
export TEST_DATABASE_URL="postgresql+asyncpg://haccp:<POSTGRES_PASSWORD>@localhost:5432/haccp_test"
uv run pytest
```

La fixture crée une base `haccp_test_<pid>`, y applique les migrations, puis la
supprime en fin de session : deux exécutions simultanées ne se marchent pas
dessus.
