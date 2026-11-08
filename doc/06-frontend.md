# Frontend Next.js

## Technologies

- Next.js 16 (App Router), React 19, TypeScript strict.
- Tailwind CSS 4.
- `yarn` 1.22.

## Organisation

```text
frontend/src/
  app/
    (app)/                 pages protégées, layout avec navigation
    api/                   route handlers Next (proxies)
    login/                 page publique
  actions/                 Server Actions (mutations)
  components/              composants UI par domaine
  lib/                     apiFetch, session, types, formatage, UI
```

Le layout `(app)/layout.tsx` appelle `GET /api/v1/auth/me`. Sans session, il
redirige vers `/login`. Le shell affiche la navigation, l'utilisateur et le
role.

## Modules visibles

Les entrées du menu sont contrôlées par dix variables d'environnement :
`MODULE_EQUIPMENT`, `MODULE_READINGS`, `MODULE_CLEANING`,
`MODULE_PASTEURISATION`, `MODULE_TRANSPORT`, `MODULE_CASH_SESSIONS`,
`MODULE_EXPORT`, `MODULE_DOCUMENTS`, `MODULE_HISTORY` et `MODULE_USERS`.

- `1` affiche les entrées du module, `0` les masque ; une valeur absente vaut
  `1`, toute autre valeur provoque une erreur de configuration.
- `MODULE_CLEANING` contrôle à la fois `/cleaning` et `/cleaning/plans`.
- `MODULE_DOCUMENTS` contrôle à la fois `/templates` et `/documents`.
- Matériel est un prérequis de Relevés, Transport et Suivi de caisse. Son
  entrée reste donc visible si au moins un de ces modules est actif, même avec
  `MODULE_EQUIPMENT=0`.
- Sur `/equipment`, `MODULE_TRANSPORT` masque le bloc Véhicules et
  `MODULE_CASH_SESSIONS` masque le bloc Caisses. Sur le détail d'un matériel,
  `MODULE_READINGS` masque l'historique et l'action de saisie des relevés.
- Les pages ne sont pas bloquées individuellement : une URL directe reste
  accessible, conformément au choix de désactivation visuelle.
- La racine `/` et la connexion redirigent vers le premier module actif visible
  pour le rôle. Si aucun module n'est visible, le shell affiche « Aucun module
  actif ».
- Les indicateurs sont lus uniquement côté serveur puis transmis à
  `NavLinks`; ils ne sont pas exposés via `NEXT_PUBLIC_*`.

Les références croisées suivent les mêmes indicateurs :

| Module désactivé | Références également masquées |
| --- | --- |
| Matériel | Masqué seulement si Relevés, Transport et Suivi de caisse sont aussi désactivés ; masque alors leurs liens résiduels |
| Relevés | Bloc de relevés du détail Matériel, carte d'export et source d'historique |
| Nettoyage | Cartes d'export et source d'historique |
| Pasteurisation | Cartes d'export et source d'historique |
| Transport | Bloc Véhicules de Matériel, carte d'export et source d'historique |
| Suivi de caisse | Bloc Caisses de Matériel et carte d'export |
| Export | Entrée de menu |
| Documents | Entrées Modèles LaTeX et Documents générés, ainsi que la carte d'export Documents |
| Historique | Entrée de menu et mentions vers l'onglet Historique |
| Utilisateurs | Entrée de menu |

La page `/export` ne propose que les fichiers des modules sources actifs. La
page `/history` filtre ses sources et ses entrées de la même façon.

## Pages

| Route | Contenu |
| --- | --- |
| `/equipment` | Parc matériel, véhicules et caisses. |
| `/equipment/[id]` | Détail d'un matériel. |
| `/readings` | Relevés de température par jour. |
| `/cleaning` | Déclarations de nettoyage. |
| `/cleaning/[planId]` | Détail d'un plan. |
| `/cleaning/plans` | Gestion des plans. |
| `/pasteurisation` | Lots de pasteurisation. |
| `/pasteurisation/[batchId]` | Détail et phases. |
| `/transport` | Transports et véhicules. |
| `/transport/[transportId]` | Détail et checkpoints. |
| `/cash-sessions` | Suivis de caisse. |
| `/cash-sessions/[sessionId]` | Détail, frais, clôture, export. |
| `/export` | Téléchargement des six CSV. |
| `/templates` | Modèles LaTeX. |
| `/templates/[templateId]` | Variables, aperçu, génération, renommage. |
| `/documents` | Historique des PDF générés. |
| `/history` | Journal d'audit (admin). |
| `/users` | Gestion des comptes et des rôles (admin). |

## Session et appels API

- Cookies `haccp_access_token` et `haccp_refresh_token`, `httpOnly`,
  `SameSite=Lax`, `Secure` si `SESSION_COOKIE_SECURE=true` ou en production.
- `src/proxy.ts` renouvelle l'access token avant les pages, Server Actions et
  route handlers lorsque le JWT est expiré ou proche de l'expiration. Les
  nouveaux cookies sont écrits dans la réponse du proxy.
- `src/lib/api.ts` :
  - `apiFetch<T>` pour le JSON ;
  - `apiFetchRaw` pour les flux (CSV, PDF, images) ;
  - ajout du Bearer côté serveur ;
  - aucun refresh pendant le rendu : un composant serveur ne peut pas persister
    les cookies ;
  - `ApiError` expose `status`, `code`, `message` et `context`.
- Les erreurs backend sont traduites en messages localisés dans les composants
  et les Server Actions, par code métier puis par statut HTTP.

## Langues et formats

- Langues disponibles : `fr` (défaut) et `en`.
- Le choix est propre au navigateur. Il est conservé dans
  `localStorage["haccpflow.locale"]` et dans le cookie miroir
  `haccp_locale`, valable un an et `SameSite=Lax`.
- Le cookie permet aux composants serveur, aux Server Actions et aux route
  handlers de rendre la langue active dès la requête. Une valeur absente ou
  invalide retombe sur `fr`.
- Le bouton `FR / EN` du shell et de la connexion met à jour le contexte
  client, `localStorage`, le cookie et `document.documentElement.lang`, puis
  rafraîchit les composants serveur.
- Au chargement, une valeur `localStorage` différente du cookie est
  resynchronisée dans le cookie et déclenche un rafraîchissement.
- Le layout racine utilise la langue du cookie pour `<html lang>` et les
  métadonnées. Les chemins restent identiques et aucune URL localisée n'est
  créée.
- Les dates, heures, nombres, montants, durées, tailles de fichiers et
  expressions relatives utilisent `fr-FR` ou `en-GB`. L'euro, `°C` et UTC
  restent inchangés.
- Les identifiants, noms de matériel, lots, commentaires, données saisies et
  contenus LaTeX ne sont jamais traduits.
- Les libellés partagés (rôles, statuts, types, fréquences, phases, sources et
  entrées d'historique) proviennent du catalogue typé `src/lib/i18n.ts`.
- Le scénario frontend vérifie le français par défaut, l'anglais avec
  `haccp_locale=en`, le repli sur `fr` avec un cookie invalide et la présence
  des libellés anglais sur toutes les pages.

## Mutations

Deux patterns coexistent :

1. **Server Actions** pour les formulaires métier classiques
   (`src/actions/*.ts`), avec `useActionState`, `revalidatePath` et messages
   d'erreur.
2. **Route handlers Next** pour les flux qui ne peuvent pas passer par une
   Server Action ou qui doivent streamer :
   - upload/remplacement/renommage de modèle ;
   - variables et images ;
   - aperçu et génération PDF ;
   - téléchargements CSV/PDF/sources ;
   - exports.

Ces handlers gardent le jeton côté serveur et propagent les erreurs
`{ code, detail, context }`.

## Gestion des utilisateurs

- La page `/users` est réservée aux admins et masquée de la navigation pour les
  opérateurs.
- Le tableau affiche email, rôle, état, dates et actions.
- La création et la modification passent par des Server Actions dans
  `src/actions/users.ts`.
- Le mot de passe généré est affiché dans une modale dédiée avec copie et
  avertissement de non-réaffichage.
- Chaque ligne propose une suppression définitive rouge. Le bouton est désactivé
  pour le compte courant et le dernier admin actif, avec l'explication au
  survol.
- La suppression ouvre une modale qui affiche l'email et avertit que l'action
  est irréversible. L'historique est conservé, mais les actions du compte
  deviennent anonymes ; la désactivation est recommandée en cas de doute.
- Le bouton « Supprimer définitivement » reste désactivé tant que l'email exact
  du compte n'a pas été saisi. Une erreur backend laisse la modale ouverte.
- Le compte courant ne peut pas modifier ses droits, être désactivé ni être
  supprimé depuis l'UI.
- Un admin peut réinitialiser son propre mot de passe ; après copie, la modale
  redirige vers `/login` car la session est révoquée.

### Proxies existants

- `/api/exports/[dataset]`
- `/api/cash-sessions/[sessionId]/export`
- `/api/documents/[documentId]/download`
- `/api/templates` (POST)
- `/api/templates/[templateId]` (PATCH renommage)
- `/api/templates/[templateId]/download`
- `/api/templates/[templateId]/generate`
- `/api/templates/[templateId]/preview`
- `/api/templates/[templateId]/variables` (POST)
- `/api/templates/[templateId]/variables/[variableId]` (PUT/DELETE)
- `/api/templates/[templateId]/variables/[variableId]/image` (GET/PUT/DELETE)

## RBAC côté interface

- `NavLinks` masque les entrées `adminOnly`.
- Les pages admin (historique, modèles, variables, renommage, utilisateurs) vérifient
  `user.role === "admin"` et affichent un panneau « accès refusé ».
- **Rappel** : ces contrôles sont uniquement ergonomiques ; le backend refuse
  toujours les actions non autorisées.

## Conventions UI

- Catalogue de messages typé FR/EN, code et identifiants en anglais.
- Classes partagées dans `src/lib/ui.ts`.
- Dialogues accessibles (`role="dialog"`, `aria-modal`, fermeture Échap quand
  prévu).
- Dates et nombres affichés dans la langue active, données stockées en UTC.
- Formulaires avec messages d'erreur dans la langue active et état `pending`.
- Les téléchargements passent par des liens vers les proxies Next.

## Ajouter une page ou une fonctionnalité

1. Vérifier si la page doit être dans `(app)` (session requise).
2. Ajouter le lien dans `NavLinks` si nécessaire, avec `adminOnly` si pertinent.
3. Lire les données via `apiFetch` dans un composant serveur.
4. Créer une Server Action ou un route handler pour les mutations.
5. Gérer `401`, `403`, `409`, `422` et les codes métier.
6. Mettre à jour [06-frontend.md](./06-frontend.md) et la page métier.
7. Vérifier `yarn typecheck` et le scénario de pages.

## Qualité

```sh
cd frontend
yarn typecheck
yarn build
```

### Problème connu dans cet environnement

`yarn build` peut échouer sur le prérendu de `/_global-error` avec
`TypeError: Cannot read properties of null (reading 'useContext')`. Le même
échec a été reproduit sur la version HEAD, sans les changements fonctionnels :
il est donc lié à l'environnement Next/React local, pas à une fonctionnalité
applicative. Le serveur de développement et `yarn typecheck` fonctionnent.
Documenter ce point si le problème est résolu ou persiste après mise à jour des
dépendances.
