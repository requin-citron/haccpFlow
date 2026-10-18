# Tenir le wiki à jour

## Principe

La documentation fait partie de la définition de « terminé ». Un changement de
comportement, d'API, de schéma, de configuration ou de déploiement doit être
accompagné de la mise à jour de la page correspondante **dans le même
changement**.

Le code et les tests restent la source de vérité ; le wiki doit les décrire
fidèlement, pas anticiper des fonctionnalités non implémentées.

## Matrice changement → documentation

| Changement | Pages à mettre à jour |
| --- | --- |
| Nouvelle route API / nouveau payload | [04-api.md](./04-api.md), page métier concernée, [README](./README.md) |
| Nouvelle règle métier | [03-domaines-metier.md](./03-domaines-metier.md), [04-api.md](./04-api.md) |
| Nouvelle table / colonne / migration | [05-base-de-donnees.md](./05-base-de-donnees.md), [08-exploitation.md](./08-exploitation.md) si sauvegarde impactée |
| Nouvelle variable d'environnement | [08-exploitation.md](./08-exploitation.md), `.env.example`, `README.md` |
| Changement Docker / ports / volumes | [02-installation.md](./02-installation.md), [08-exploitation.md](./08-exploitation.md) |
| Nouvelle page ou nouveau flux frontend | [06-frontend.md](./06-frontend.md), [03-domaines-metier.md](./03-domaines-metier.md) |
| Changement du sous-système LaTeX | [07-modeles-latex.md](./07-modeles-latex.md), [03-domaines-metier.md](./03-domaines-metier.md), [08-exploitation.md](./08-exploitation.md) |
| Nouvel export CSV | [03-domaines-metier.md](./03-domaines-metier.md), [04-api.md](./04-api.md), `scenario/README.md` |
| Changement de rôle / sécurité | [03-domaines-metier.md](./03-domaines-metier.md), [04-api.md](./04-api.md), [08-exploitation.md](./08-exploitation.md) |
| Nouveau script de seed/vérification | [02-installation.md](./02-installation.md), `scenario/README.md` |
| Nouvelle limite ou dette technique | [10-feuille-de-route.md](./10-feuille-de-route.md) |

## Checklist avant de terminer un changement

- [ ] La page principale du domaine est à jour.
- [ ] Les routes/payloads modifiés apparaissent dans [04-api.md](./04-api.md).
- [ ] Les nouvelles variables d'environnement sont dans `.env.example` et
      [08-exploitation.md](./08-exploitation.md).
- [ ] Les migrations sont listées dans [05-base-de-donnees.md](./05-base-de-donnees.md).
- [ ] Les commandes de test/scénario sont toujours exactes.
- [ ] Les liens Markdown relatifs fonctionnent.
- [ ] Aucun secret, identifiant de tenant ou donnée personnelle n'est ajouté.
- [ ] La date de dernière revue de `doc/README.md` est mise à jour.

## Conventions de rédaction

- Rédiger en français ; garder les identifiants, chemins et codes d'API en
  anglais.
- Une page = un sujet ; éviter les doublons, préférer un lien.
- Documenter le comportement observable (routes, erreurs, règles), pas
  l'implémentation ligne par ligne.
- Les exemples de commandes doivent être copiables et ne jamais contenir de
  secret réel.
- Les chemins doivent être relatifs au dépôt ou absolus uniquement quand c'est
  nécessaire.
- Signaler explicitement les limites et les comportements non implémentés.

## Vérifier la cohérence

### Routes

Comparer l'inventaire OpenAPI et le tableau de [04-api.md](./04-api.md) :

```sh
cd backend
SECRET_KEY=0123456789abcdef0123456789abcdef \
DATABASE_URL='postgresql+asyncpg://u:p@localhost/db' \
uv run python - <<'PY'
from app.main import create_app
for path, ops in sorted(create_app().openapi()["paths"].items()):
    print(path, ",".join(sorted(ops)))
PY
```

Le test `backend/tests/test_openapi.py` vérifie l'ensemble exact des chemins ;
il doit être mis à jour à chaque ajout/suppression de route.

`backend/tests/test_docs.py` vérifie automatiquement :

- que chaque route OpenAPI apparaît dans [04-api.md](./04-api.md) ;
- que tous les liens relatifs du wiki pointent vers un fichier existant ;
- que chaque page `doc/*.md` est listée dans l'index.

Lancer uniquement ce contrôle :

```sh
cd backend
uv run pytest tests/test_docs.py
```

### Variables d'environnement

```sh
rg -n '^[A-Z][A-Z0-9_]+=' .env.example
rg -n 'Settings|Field\(' backend/app/config.py
```

Vérifier que chaque variable utile est documentée et transmise par
`docker-compose.yml` si elle doit l'être.

### Liens et pages

- Partir de `doc/README.md` et suivre les liens.
- Vérifier que chaque page listée existe.
- Vérifier que les pages ajoutées sont référencées dans l'index.

## Ajouter une page

1. Créer un fichier `doc/NN-sujet.md` avec un titre `#`.
2. L'ajouter au tableau de `doc/README.md`.
3. Ajouter les liens croisés depuis les pages voisines.
4. Vérifier les exemples et les chemins.
5. Mettre à jour la date de revue.

## Revue périodique

Lors d'une revue de documentation :

- relire les pages touchées depuis la dernière revue ;
- vérifier les versions (Next, React, PostgreSQL, TeX Live) ;
- vérifier les limites connues et la feuille de route ;
- supprimer ou corriger les informations devenues fausses ;
- mettre à jour « Dernière revue » dans `doc/README.md`.
