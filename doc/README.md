# Wiki haccpFlow

Documentation de référence de la plateforme HACCP **haccpFlow**.

Ce wiki décrit le fonctionnement réel de l'application : architecture, règles
métier, API, modèle de données, interface, génération de documents LaTeX,
exploitation et procédure de mise à jour de la documentation.

## Par où commencer ?

| Besoin | Page |
| --- | --- |
| Comprendre l'architecture et les flux | [Architecture](./01-architecture.md) |
| Installer et démarrer l'application | [Installation](./02-installation.md) |
| Comprendre les règles HACCP et les rôles | [Domaines métier](./03-domaines-metier.md) |
| Appeler l'API ou ajouter une route | [API](./04-api.md) |
| Modifier le schéma ou ajouter une migration | [Base de données](./05-base-de-donnees.md) |
| Travailler sur Next.js et l'interface | [Frontend](./06-frontend.md) |
| Uploader, configurer ou générer un modèle LaTeX | [Modèles LaTeX](./07-modeles-latex.md) |
| Configurer, sauvegarder, diagnostiquer | [Exploitation](./08-exploitation.md) |
| Mettre le wiki à jour après un changement | [Maintenance](./09-maintenance.md) |
| Voir les limites et la feuille de route | [Feuille de route](./10-feuille-de-route.md) |

## État actuel

- Une instance par client, déployée avec Docker Compose.
- Backend FastAPI, frontend Next.js, PostgreSQL 16, Mosquitto.
- Zigbee2MQTT est prévu **hors** de cette pile : le backend se connecte au
  broker, l'ingestion des capteurs n'est pas encore implémentée.
- Deux rôles : `admin` et `operator`. L'autorisation est toujours appliquée par
  le backend.
- Les admins peuvent créer, promouvoir, désactiver et réinitialiser les comptes
  via l'API ; l'écran frontend reste à venir.
- Les relevés, nettoyages, pasteurisations et transports ont un journal de
  corrections ; les documents générés conservent un snapshot des variables.
- Les horodatages sont stockés en UTC et affichés en français côté interface.
- Le schéma n'a pas encore de colonne `tenant_id` : le cloisonnement actuel
  repose sur une instance par client. Les évolutions doivent rester
  compatibles avec l'ajout d'un tenant.

## Sources de vérité

1. Le code et les tests priment sur ce wiki en cas de divergence.
2. `README.md` donne le démarrage rapide et la configuration.
3. `scenario/README.md` décrit les scripts de peuplement et de vérification.
4. `AGENTS.md` contient les règles de développement et de documentation.

## Mettre à jour ce wiki

Tout changement d'API, de modèle de données, de configuration, de déploiement
ou de règle métier doit mettre à jour la page correspondante et, si nécessaire,
le tableau de maintenance de [09-maintenance.md](./09-maintenance.md).

Dernière revue : **2026-10-28**.
