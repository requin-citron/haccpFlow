# Limites connues et feuille de route

## Limites actuelles

### Multi-tenant

- Le schéma n'a pas de `tenant_id` : une instance par client.
- Les requêtes devront être filtrées par tenant lors de l'ajout du
  multi-tenant, côté backend.

### Utilisateurs

- Gestion backend et page `/users` disponibles : création, rôle, désactivation,
  réinitialisation, suppression définitive confirmée par email et affichage
  unique du mot de passe.
- Pas encore de recherche, de filtre ni de pagination sur la liste des comptes.
- Les changements de comptes ne sont pas journalisés dans l'historique métier.
- Une suppression est irréversible et aucune restauration de compte n'est
  proposée.

### Capteurs et MQTT

- Le backend se connecte au broker mais ne consomme aucun topic.
- L'ingestion Zigbee2MQTT et les relevés automatiques (`source = sensor`) sont
  à implémenter.
- Zigbee2MQTT reste externe à la stack Compose.

### Modèles LaTeX

- Pas de suppression de modèle ni de versionnement.
- Remplacement du source uniquement via `PUT /templates/{id}` (admin).
- Une seule image par variable, uniquement statique.
- Pas d'upload d'image locale à chaque génération.
- Pas de gestion d'assets autres que les images de variables.
- Le dossier `templates/` est ignoré par Git ; le seed du bon de livraison
  dépend de sa présence locale.
- `|safe` permet à un admin d'insérer du LaTeX brut dans un modèle ; c'est une
  décision de confiance.

### PDF

- Le sandbox `pdflatex` n'est pas une isolation système complète.
- La compilation dépend des paquets TeX Live de l'image ; un paquet absent
  nécessite un rebuild.
- Les PDF sont conservés sans purge automatique.

### Exports

- Les exports peuvent être volumineux ; pas de pagination dans le fichier.
- La protection contre les formules Excel est appliquée à l'export `documents`
  mais pas encore généralisée aux autres exports de texte libre.
- Le CSV `documents` ajoute une colonne par variable ; un grand nombre de
  modèles différents peut produire un tableau large et clairsemé.

### Frontend

- `yarn build` peut échouer sur `/_global-error` (`useContext` nul) dans
  l'environnement local ; le problème a été reproduit sur HEAD.
- Certaines listes n'ont pas de pagination explicite (historique plafonné,
  documents limités à 50 dans l'interface).

### Audit

- L'historique d'audit admin couvre les relevés, nettoyages, phases de
  pasteurisation et transports.
- Les éditions de variables de modèle et les renommages ne sont pas dans ce
  flux ; elles restent visibles via `updated_at` et les snapshots de documents.

## Feuille de route

### Priorités fonctionnelles

1. Ingestion Zigbee2MQTT : abonnement, mapping capteur → matériel, relevés
   `sensor`, idempotence et gestion des doublons.
2. Multi-tenant : `tenant_id`, filtrage backend, index et contraintes par
   tenant, migration des données existantes.
3. Versionnement/suppression des modèles LaTeX et gestion d'assets générique.
4. Images locales par génération (upload temporaire, expiration, nettoyage).
5. Export PDF du plan de maîtrise sanitaire.

### Qualité et exploitation

- Alerte lorsqu'un lot de pasteurisation reste incomplet.
- TLS sur le broker pour les sites on-premise.
- Purge/rétention configurable des PDF générés.
- Généralisation de la protection CSV contre les formules.
- Résolution du build Next.js dans l'environnement local.
- CI automatisée (lint, types, tests, scénarios, build).

### Documentation

- Maintenir la matrice de [Maintenance](./09-maintenance.md) à chaque
  changement.
- Ajouter une page dédiée dès qu'un domaine devient autonome.
