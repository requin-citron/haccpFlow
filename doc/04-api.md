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
  "expires_in": 3600,
  "refresh_expires_in": 2592000
}
```

`expires_in` et `refresh_expires_in` sont exprimés en secondes. Le frontend
stocke les deux jetons dans des cookies `httpOnly` dont la durée de vie suit ces
valeurs, puis ajoute `Authorization: Bearer <access_token>` côté serveur. Le
navigateur ne manipule jamais les jetons.

Une rotation de refresh token peut être rejouée pendant une courte fenêtre de
grâce (10 s) pour absorber deux requêtes concurrentes. Au-delà, un rejeu révoque
toute la famille de rotation issue de la connexion.

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
| `user_email_taken` | email déjà utilisé (409) |
| `user_last_admin` | dernier admin actif protégé (409) |
| `user_self_lockout` | tentative de retrait de ses propres droits (409) |
| `user_not_found` | compte absent (404) |
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
| `POST` | `/api/v1/users` | admin (crée un compte et retourne un mot de passe temporaire) |
| `PATCH` | `/api/v1/users/{user_id}` | admin (rôle et/ou activation) |
| `DELETE` | `/api/v1/users/{user_id}` | admin (suppression définitive, réponse `204`) |
| `POST` | `/api/v1/users/{user_id}/reset-password` | admin (retourne un mot de passe temporaire) |

Création :

```json
{
  "email": "operateur@example.com",
  "role": "operator"
}
```

La réponse contient les champs publics du compte et
`temporary_password`. Ce champ n'est jamais renvoyé par `GET /users` et les
réponses sont marquées `Cache-Control: no-store`.

Mise à jour partielle :

```json
{
  "role": "admin",
  "is_active": false
}
```

Au moins un champ est requis. Un changement de rôle ou de statut invalide les
access tokens existants via `auth_version`; une désactivation révoque aussi tous
les refresh tokens du compte. Le dernier admin actif et l'auto-modification de
ses propres droits sont refusés.

Réinitialisation :

- route admin uniquement ;
- génère un mot de passe fort, le retourne une seule fois et révoque les
  sessions existantes ;
- aucun changement en libre-service n'est exposé.

Suppression définitive :

- `DELETE /api/v1/users/{user_id}` supprime le compte et répond `204` sans
  corps ; l'email redevient disponible ;
- les refresh tokens sont supprimés en cascade et les access tokens existants
  ne peuvent plus retrouver le compte ;
- les traces métier sont conservées. Leurs clés étrangères vers l'auteur
  passent à `NULL`, donc les API d'historique exposent `actor_email: null` ;
- le compte courant et le dernier administrateur actif ne peuvent pas être
  supprimés (`user_self_lockout` ou `user_last_admin`, statut `409`) ;
- aucune migration n'est nécessaire : le schéma applique déjà `ON DELETE SET
  NULL` aux traces et `ON DELETE CASCADE` aux refresh tokens.

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

`PUT .../readings/{reading_date}` accepte les champs partiels
`morning_celsius`, `evening_celsius`, `morning_justification` et
`evening_justification`. Un champ de température absent conserve la valeur
effective courante. Une modification d'une valeur existante est refusée en
`422` avec `reading_justification_required` si la justification du même
créneau manque.

La réponse expose :

- `morning` et `evening` : valeurs effectives, pour rester compatibles avec
  les clients existants ;
- `morning_original` et `evening_original` : mesures initiales immuables ;
- `morning_modified` et `evening_modified` : dernière correction, ou `null`.

Un objet modifié contient `previous_celsius`, `new_celsius`,
`is_compliant`, `justification`, `changed_by_email` et `changed_at`.
Plusieurs corrections successives sont consolidées : seule la dernière est
exposée, tandis que l'originale reste inchangée.

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

Les checkpoints transport utilisent les champs
`initial_time`, `initial_temperature_celsius`, `in_progress_time` et
`in_progress_temperature_celsius`. L'endpoint `/readings` accepte une mise à
jour partielle : un champ absent conserve sa valeur, un champ `null` l'efface.
Les anciens noms `departure_*` et `arrival_*` ne sont plus acceptés.

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

`POST` et `PUT /cash-registers` acceptent `kind` avec `cash`, `cheque` ou
`card`. Sans `kind`, la création reste compatible et produit `cash`. Le type
est refusé en modification (`cash_register_kind_immutable`). Une caisse
`cheque` ou `card` refuse tout compteur de coupure non nul
(`cash_register_counts_not_supported`).

Pour une caisse espèces, l'ouverture et la modification d'un suivi conservent
`opening_counts` ; une modification sans comptage retourne
`cash_session_opening_counts_required`. Pour chèques/cartes, ces champs sont
interdits (`cash_session_opening_counts_not_supported`).

La clôture espèces conserve son payload complet
`{"closing_counts": {...}}`. La clôture chèques/cartes utilise
`{"collected_amount_cents": 12500}`. Un payload qui ne correspond pas au type
de caisse retourne `cash_session_closing_payload_mismatch`. Les réponses de
suivi exposent `cash_register_kind` et `collected_amount_cents`.

## Tableau de bord

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/dashboard/revenue?from=YYYY-MM-DD&to=YYYY-MM-DD` | admin, opérateur |
| `GET` | `/api/v1/dashboard/missing-readings?from=YYYY-MM-DD&to=YYYY-MM-DD` | admin, opérateur |
| `GET` | `/api/v1/dashboard/layout` | admin, opérateur |
| `PUT` | `/api/v1/dashboard/layout` | admin, opérateur |

`revenue` calcule le chiffre d'affaires des suivis clôturés, non supprimés et
compris dans la période inclusive. Les bornes inversées retournent
`422 dashboard_range_invalid`. La réponse contient `from`, `to`,
`total_cents`, `cash_cents`, `cheque_cents`, `card_cents`,
`cash_expenses_cents` et `closed_session_count`.

Pour les espèces, le calcul est
`clôture - ouverture + frais professionnels + frais personnels`. Pour les
chèques et cartes, le montant encaissé est utilisé directement.

`missing-readings` retourne `missing_slots`, `filled_slots`, `total_slots` et
`equipment_count`. Chaque équipement actif attend deux créneaux par jour depuis
sa date de création, sans compter les jours futurs ni les équipements
désactivés.

`layout` retourne la disposition personnelle du compte. Sans sauvegarde, la
réponse virtuelle contient le widget `revenue` sur toute la largeur. Le `PUT`
remplace toute la disposition par une liste `widgets`. Chaque widget contient
`key`, `column_start`, `row_start`, `width_columns` et `row_span`; la grille
utilise douze colonnes et les clés sont uniques. Les widgets disponibles sont
`revenue`, `missing_readings` et `overdue_cleanings`, et ne peuvent pas se
chevaucher. Une liste vide est une disposition valide et persistée. Le widget
`overdue_cleanings` réutilise `/api/v1/cleaning-schedule/overdue` et ne dépend
pas de la période globale.

## Exports

| Méthode | Route | Accès |
| --- | --- | --- |
| `GET` | `/api/v1/exports/{dataset}` | admin, opérateur |

`dataset` ∈ `readings`, `cleanings`, `pasteurisations`, `transports`,
`cash-registers`, `documents`.

Paramètres optionnels : `from`, `to` (`YYYY-MM-DD`, bornes incluses).
Réponse : CSV UTF-8 avec BOM, séparateur `;`.

L'export `readings` produit une ligne par matériel et par date avec les
colonnes : matériel, type, date, températures matin et soir originales,
températures modifiées, justifications, conformité effective et source
effective. Les auteurs et horodatages d'audit ne sont pas exportés.

L'export `documents` expose le modèle, le fichier PDF, sa taille, son SHA-256,
puis une colonne par nom de variable présent dans les documents exportés.

Les exports nettoyages, caisses et documents n'exposent pas non plus les
auteurs ou horodatages techniques. Les filtres `from`/`to` restent disponibles
et l'audit complet reste accessible via les API d'historique.

L'export `cash-registers` ajoute en fin de ligne le type de caisse et
l'encaissement du jour. L'extract d'une session chèques/cartes remplace les
blocs de coupures par un bloc « Encaissement du jour ».

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
    "client_nom": "Client Exemple",
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
