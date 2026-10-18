# Domaines métier

## Rôles et autorisations

Deux rôles existent :

| Rôle | Usage |
| --- | --- |
| `operator` | Saisie quotidienne : relevés, nettoyages, lots, transports, caisses, génération de PDF. |
| `admin` | Tout ce que fait l'opérateur, plus la désactivation des référentiels, l'historique d'audit, les utilisateurs, les modèles LaTeX et leurs variables. |

L'autorisation est **toujours** appliquée côté backend avec
`Depends(require_role(...))`. L'interface masque les actions, mais ne constitue
pas une barrière de sécurité.

Tableau complet : [README — Rôles et accès](../README.md#rôles-et-accès).

## Chaîne du froid

### Matériel

- Deux types : `fridge` (réfrigérateur) et `freezer` (congélateur).
- Chaque matériel porte ses propres seuils `min_temperature_celsius` et
  `max_temperature_celsius`.
- Les variables `DEFAULT_*_TEMPERATURE_C` ne servent qu'à créer un matériel
  sans seuils explicites ; elles ne remplacent jamais les seuils stockés.
- Le nom est unique parmi les matériels actifs, sans tenir compte de la casse.
- La désactivation est douce (`deleted_at`) et réservée aux admins. Le nom est
  alors libéré pour un nouveau matériel.
- Champs complémentaires : `location`, `notes`.

### Relevés de température

- Deux créneaux : `morning` et `evening`, une valeur par créneau et par jour.
- L'API accepte un créneau seul ; le second peut être complété plus tard sans
  écraser le premier.
- La conformité est recalculée à chaque écriture :
  `min <= température <= max`.
- Les corrections sont journalisées dans `temperature_reading_edits` avec
  l'auteur, l'ancienne valeur, la nouvelle valeur et l'horodatage.
- Une date antidatée est acceptée ; une date trop future est refusée (tolérance
  d'un jour pour les décalages de fuseau).
- Les listes par défaut couvrent les 7 derniers jours ; une plage explicite ne
  peut pas dépasser 366 jours.
- Les relevés automatiques (`source = sensor`) sont prévus, mais l'ingestion
  MQTT/Zigbee n'est pas encore active.

## Nettoyage et désinfection (PND)

### Plan de nettoyage

- Nom unique parmi les plans actifs, sans tenir compte de la casse.
- Fréquences : `after_each_use`, `daily`, `weekly`.
- Produits et consignes stockés dans le plan.
- Désactivation douce réservée aux admins.

### Déclarations de nettoyage

- Une déclaration porte une `cleaning_date` et un commentaire optionnel.
- Plusieurs déclarations sont possibles le même jour.
- La prochaine échéance est calculée à partir de la dernière déclaration :
  - `daily` : +1 jour ;
  - `weekly` : +7 jours ;
  - `after_each_use` : pas d'échéance planifiée ;
  - jamais nettoyé : dû depuis la date de création du plan.
- Statuts calculés, jamais stockés : `overdue`, `due_today`, `upcoming`.
- Les créations, corrections et suppressions de déclarations sont auditées.
- Les endpoints de prévisionnel et de retard sont globaux.

## Pasteurisation

### Lot

- Champs : date, produit, numéro de lot, quantité.
- Le numéro de lot n'est pas unique (un lot peut être pasteurisé plusieurs
  fois).
- Désactivation douce réservée aux admins.

### Phases

Trois phases ordonnées : `preheating`, `holding`, `cooling`.

Pour chaque phase :

- heure de début ;
- heure de fin ;
- température cible ;
- observation.

Règles :

- la durée est calculée si les deux heures sont présentes et si la fin est
  strictement après le début, sans traverser minuit ;
- une phase est complète si début, fin et température cible sont présents ;
- les phases peuvent être remplies progressivement ;
- les modifications de phase sont auditées avec l'ancienne et la nouvelle
  valeur ;
- la recherche par numéro de lot est disponible.

## Transport

### Véhicule

- Nom et plaque optionnels individuellement, mais un véhicule doit rester
  identifiable.
- Nom et plaque sont uniques parmi les véhicules actifs, sans tenir compte de
  la casse, quand ils sont renseignés.
- Désactivation douce réservée aux admins.

### Transport

- Champs : date, lieu, produit, numéro de lot (optionnel), véhicule du
  référentiel ou libellé libre, observation.
- Deux checkpoints : départ et arrivée, chacun avec heure et température.
- Un transport est complet si les deux heures et les deux températures sont
  présentes.
- Les corrections des relevés et de l'observation sont auditées.
- Recherche par numéro de lot ; désactivation douce réservée aux admins.

## Caisses

### Enrôlement

- Douze coupures, de 1 centime à 50 euros, stockées en nombre d'unités.
- Le total est calculé en centimes (entier), jamais en flottant.
- Nom unique parmi les caisses actives, sans tenir compte de la casse.
- Désactivation douce réservée aux admins.
- Une caisse avec un suivi ouvert ne peut pas être désactivée.

### Suivi de caisse

- Un seul suivi ouvert à la fois par caisse.
- À l'ouverture, le fond peut être repris du comptage de la caisse ou forcé.
- Les frais sont de deux natures : `professional` ou `personal`, avec nom,
  quantité, prix unitaire en centimes et taux de TVA.
- Les totaux (généraux, pro, perso) sont calculés.
- À la clôture, un comptage complet est obligatoire ; il devient le nouvel état
  de la caisse.
- Un suivi clôturé est figé (plus de frais ni de modification).
- Un admin peut supprimer un suivi ; un opérateur peut clôturer mais pas
  supprimer.
- Chaque suivi peut être exporté seul en CSV.

## Exports CSV

Six jeux de données, filtrables par `from`/`to` :

| Dataset | Contenu |
| --- | --- |
| `readings` | Relevés de température, par créneau. |
| `cleanings` | Déclarations de nettoyage. |
| `pasteurisations` | Lots et trois phases. |
| `transports` | Transports et checkpoints. |
| `cash-registers` | États successifs des caisses. |
| `documents` | PDF générés : métadonnées + une colonne par variable. |

Format : UTF-8 BOM, séparateur `;`, dates françaises, valeurs texte échappées
par le writer CSV. L'export `documents` neutralise en plus les valeurs
commençant par `=`, `+`, `-` ou `@` pour éviter les formules Excel.

## Historique d'audit

`GET /api/v1/history` est réservé aux admins. Il agrège les modifications de :

- relevés de température ;
- déclarations de nettoyage ;
- phases de pasteurisation ;
- transports.

Chaque entrée contient l'entité, l'action, l'auteur, la date et les changements
champ par champ. Filtres : `entity`, `from`, `to`, `limit` (50 par défaut,
200 maximum).

Les historiques ciblés d'un relevé, d'une déclaration de nettoyage ou d'une
phase de pasteurisation sont accessibles aux deux rôles ; seul le flux global
`/history` est admin.

## Documents générés

- Historique des PDF générés, accessible à tous les utilisateurs connectés.
- Chaque document conserve le nom du modèle, l'auteur, le fichier, la taille,
  le SHA-256 et le snapshot des variables résolues.
- Le PDF est téléchargeable depuis l'historique.
- Les documents sont inclus dans l'export CSV `documents`.

## Utilisateurs

Seule la liste des utilisateurs est exposée (`GET /api/v1/users`, admin). Il
n'existe pas encore de création/modification d'utilisateur depuis l'interface :
seul l'admin initial est créé au démarrage.
