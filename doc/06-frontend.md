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
- Les erreurs backend sont traduites en messages français dans les composants.

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
- Les pages admin (historique, modèles, variables, renommage) vérifient
  `user.role === "admin"` et affichent un panneau « accès refusé ».
- **Rappel** : ces contrôles sont uniquement ergonomiques ; le backend refuse
  toujours les actions non autorisées.

## Conventions UI

- Libellés en français, code et identifiants en anglais.
- Classes partagées dans `src/lib/ui.ts`.
- Dialogues accessibles (`role="dialog"`, `aria-modal`, fermeture Échap quand
  prévu).
- Dates affichées en français, données stockées en UTC.
- Formulaires avec messages d'erreur en français et état `pending`.
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
