# API

## Généralités

- Préfixe : `/api/v1` (sauf santé : `/health/...`).
- OpenAPI interactif : `/docs` si `DOCS_ENABLED=true`.
- Authentification : OAuth2 password flow, access token JWT Bearer.
- Toutes les dates internes sont en UTC ; les dates métier sont au format
  ISO `YYYY-MM-DD`.
- Les routes sont protégées par rôle côté FastAPI. L'interface ne fait que
  refléter ces droits.

## Authentification

| Méthode | Route | Accès |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | public, formulaire `username`/`password` |
| `POST` | `/api/v1/auth/refresh` | public, refresh token |
| `POST` | `/api/v1/auth/logout` | public, révoque le refresh token |
| `GET` | `/api/v1/auth/me` | authentifié |

Réponse de login/refresh :

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

Le frontend stocke ces deux valeurs dans des cookies `httpOnly` et ajoute
`Authorization: Bearer <access_token>` côté serveur. Le navigateur ne manipule
jamais les jetons.

## Format d'erreur

Toutes les erreurs applicatives ont la forme :

```json
{
  "detail": "Message lisible",
  "code": "stable_error_code",
  "context": { "champ": "valeur" }
}
```

Codes fréquents :

| Code | Sens |
| --- | --- |
| `invalid_token` | access token absent/expiré/invalide |
| `insufficient_role` | rôle insuffisant (403) |
| `validation_error` | payload Pydantic invalide (422) |
| `not_found` (ou code métier) | ressource absente (404) |
| `*_conflict` / `*_taken` | doublon métier (409) |
| `internal_error` | erreur inattendue (500) |

## Rôles

- `operator` : consultation et saisie quotidienne.
- `admin` : tout, plus les désactivations, l'audit, les utilisateurs et la
  gestion complète des modèles LaTeX.

Les tableaux ci-dessous indiquent l'accès **backend**.

## Santé

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/health/live` | public |
| `GET` | `/health/ready` | public ; 503 si PostgreSQL ou MQTT indisponible |

## Utilisateurs

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/users` | admin |

## Matériel et relevés

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/equipment` | admin, opérateur |
| `POST` | `/api/v1/equipment` | admin, opérateur |
| `PUT` | `/api/v1/equipment/{equipment_id}` | admin, opérateur |
| `DELETE` | `/api/v1/equipment/{equipment_id}` | admin (désactivation douce) |
| `GET` | `/api/v1/equipment/{equipment_id}/readings` | admin, opérateur |
| `PUT` | `/api/v1/equipment/{equipment_id}/readings/{reading_date}` | admin, opérateur |
| `GET` | `/api/v1/equipment/{equipment_id}/readings/{reading_date}` | admin, opérateur |
| `GET` | `/api/v1/equipment/{equipment_id}/readings/{reading_date}/history` | admin, opérateur |

## Nettoyage

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/cleaning-plans` | admin, opérateur |
| `POST` | `/api/v1/cleaning-plans` | admin, opérateur |
| `PUT` | `/api/v1/cleaning-plans/{plan_id}` | admin, opérateur |
| `DELETE` | `/api/v1/cleaning-plans/{plan_id}` | admin |
| `GET` | `/api/v1/cleaning-plans/{plan_id}/records` | admin, opérateur |
| `POST` | `/api/v1/cleaning-plans/{plan_id}/records` | admin, opérateur |
| `PUT` | `/api/v1/cleaning-plans/{plan_id}/records/{record_id}` | admin, opérateur |
| `DELETE` | `/api/v1/cleaning-plans/{plan_id}/records/{record_id}` | admin, opérateur |
| `GET` | `/api/v1/cleaning-plans/{plan_id}/records/{record_id}/history` | admin, opérateur |
| `GET` | `/api/v1/cleaning-schedule` | admin, opérateur |
| `GET` | `/api/v1/cleaning-schedule/overdue` | admin, opérateur |

## Pasteurisation

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/pasteurisations` | admin, opérateur |
| `POST` | `/api/v1/pasteurisations` | admin, opérateur |
| `GET` | `/api/v1/pasteurisations/{batch_id}` | admin, opérateur |
| `PUT` | `/api/v1/pasteurisations/{batch_id}` | admin, opérateur |
| `DELETE` | `/api/v1/pasteurisations/{batch_id}` | admin |
| `PUT` | `/api/v1/pasteurisations/{batch_id}/phases/{phase}` | admin, opérateur |
| `GET` | `/api/v1/pasteurisations/{batch_id}/phases/{phase}/history` | admin, opérateur |

`phase` ∈ `preheating`, `holding`, `cooling`.

## Véhicules et transports

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/vehicles` | admin, opérateur |
| `POST` | `/api/v1/vehicles` | admin, opérateur |
| `PUT` | `/api/v1/vehicles/{vehicle_id}` | admin, opérateur |
| `DELETE` | `/api/v1/vehicles/{vehicle_id}` | admin |
| `GET` | `/api/v1/transports` | admin, opérateur |
| `POST` | `/api/v1/transports` | admin, opérateur |
| `GET` | `/api/v1/transports/{transport_id}` | admin, opérateur |
| `PUT` | `/api/v1/transports/{transport_id}` | admin, opérateur |
| `PUT` | `/api/v1/transports/{transport_id}/readings` | admin, opérateur |
| `DELETE` | `/api/v1/transports/{transport_id}` | admin |

## Caisses et suivis

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/cash-registers` | admin, opérateur |
| `POST` | `/api/v1/cash-registers` | admin, opérateur |
| `PUT` | `/api/v1/cash-registers/{cash_register_id}` | admin, opérateur |
| `DELETE` | `/api/v1/cash-registers/{cash_register_id}` | admin |
| `GET` | `/api/v1/cash-sessions` | admin, opérateur |
| `POST` | `/api/v1/cash-sessions` | admin, opérateur |
| `GET` | `/api/v1/cash-sessions/{session_id}` | admin, opérateur |
| `PUT` | `/api/v1/cash-sessions/{session_id}` | admin, opérateur |
| `DELETE` | `/api/v1/cash-sessions/{session_id}` | admin |
| `POST` | `/api/v1/cash-sessions/{session_id}/expenses` | admin, opérateur |
| `PUT` | `/api/v1/cash-sessions/{session_id}/expenses/{expense_id}` | admin, opérateur |
| `DELETE` | `/api/v1/cash-sessions/{session_id}/expenses/{expense_id}` | admin, opérateur |
| `POST` | `/api/v1/cash-sessions/{session_id}/close` | admin, opérateur |
| `GET` | `/api/v1/cash-sessions/{session_id}/export` | admin, opérateur |

## Exports

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/exports/{dataset}` | admin, opérateur |

`dataset` ∈ `readings`, `cleanings`, `pasteurisations`, `transports`,
`cash-registers`, `documents`.

Paramètres optionnels : `from`, `to` (`YYYY-MM-DD`, bornes incluses).
Réponse : CSV UTF-8 avec BOM, séparateur `;`.

L'export `documents` ajoute, après les métadonnées, une colonne par nom de
variable présent dans les documents exportés.

## Modèles LaTeX

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/templates` | admin, opérateur |
| `POST` | `/api/v1/templates` | admin (multipart `file`, `name` optionnel) |
| `PUT` | `/api/v1/templates/{template_id}` | admin (remplace le source, multipart) |
| `PATCH` | `/api/v1/templates/{template_id}` | admin (renommage JSON `{"name": "..."}`) |
| `GET` | `/api/v1/templates/{template_id}/download` | admin (source `.tex`) |
| `GET` | `/api/v1/templates/{template_id}/variables` | admin, opérateur |
| `POST` | `/api/v1/templates/{template_id}/variables` | admin |
| `PUT` | `/api/v1/templates/{template_id}/variables/{variable_id}` | admin |
| `DELETE` | `/api/v1/templates/{template_id}/variables/{variable_id}` | admin |
| `PUT` | `/api/v1/templates/{template_id}/variables/{variable_id}/image` | admin (multipart JPEG/PNG) |
| `GET` | `/api/v1/templates/{template_id}/variables/{variable_id}/image` | admin |
| `DELETE` | `/api/v1/templates/{template_id}/variables/{variable_id}/image` | admin |
| `POST` | `/api/v1/templates/{template_id}/preview` | admin |
| `POST` | `/api/v1/templates/{template_id}/generate` | admin, opérateur |

Détails des payloads et du rendu : [Modèles LaTeX](./07-modeles-latex.md).

## Documents générés

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/documents` | authentifié |
| `GET` | `/api/v1/documents/{document_id}/download` | authentifié |

Paramètres de liste : `limit` (défaut 50, max 200), `offset`,
`template_id` optionnel.

## Historique d'audit

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/history` | admin |

Paramètres : `entity`, `from`, `to`, `limit` (50 par défaut, 200 maximum).

## Exemples

### Connexion

```sh
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=admin@example.com' \
  --data-urlencode 'password=...'
```

### Génération d'un PDF

```json
POST /api/v1/templates/{id}/generate
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "values": {
    "bl_numero": "220826",
    "client_nom": "Biocoop",
    "lignes_produits": [
      { "designation": "Bocal A", "pots": 10, "prix": "3.95" }
    ]
  }
}
```

### Renommage

```json
PATCH /api/v1/templates/{id}
Authorization: Bearer <access_token>
Content-Type: application/json

{ "name": "Nouveau nom" }
```

### Export filtré

```sh
curl -H "Authorization: Bearer $TOKEN" \
  'http://localhost:8000/api/v1/exports/documents?from=2026-08-01&to=2026-08-31' \
  -o documents.csv
```

## Ajouter une route

1. Définir le schéma Pydantic et la règle métier dans un service.
2. Ajouter la route dans `backend/app/api/v1/`.
3. Déclarer le rôle minimal (`require_role`) ou documenter l'accès public.
4. Mettre à jour `backend/tests/test_openapi.py` (le test vérifie l'ensemble
   exact des chemins).
5. Ajouter les tests d'API et, si nécessaire, un proxy Next.js.
6. Mettre à jour [04-api.md](./04-api.md) et la page métier concernée.
