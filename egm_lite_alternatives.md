> **BLUF:** Calculer le chiffre d'affaires dans un endpoint backend dédié, avec la formule espèces `clôture - ouverture + frais`, puis afficher le résultat dans un widget KPI au-dessus de la timeline.

# Alternatives Considered

## Source du calcul

### Retenu : endpoint backend agrégé

Un endpoint `GET /api/v1/dashboard/revenue?from=...&to=...` calcule le total et
la ventilation espèces/chèques/cartes. La règle métier est testable directement
et les futurs widgets pourront réutiliser des agrégats cohérents.

### Écarté : calcul dans le composant Next.js

Le frontend pourrait charger toutes les sessions via `/cash-sessions` et
additionner leurs champs. Cette approche évite une route backend, mais place une
règle comptable importante dans du code frontend sans test métier dédié et
transfère inutilement l'historique complet des sessions.

## Formule des espèces

### Retenu : variation de caisse avec réintégration des frais

`chiffre d'affaires = clôture - ouverture + frais pro + frais perso`.

Cette formule mesure l'argent entré pendant le suivi. Réintégrer les frais
compense les sorties utilisées pour payer des achats ou des prélèvements.

### Écarté : somme du contenu de clôture

Additionner directement le comptage de clôture compte à nouveau le fond présent
à l'ouverture. Sur plusieurs jours, le même fond serait répété dans le chiffre
d'affaires.

## Périmètre des sessions

### Retenu : suivis clôturés, non supprimés, dates incluses

Seules les sessions dont `closed_at` est renseigné et `deleted_at` est nul sont
comptées. Le filtre porte sur `session_date`, bornes incluses, en UTC.

### Écarté : inclure les suivis ouverts ou supprimés

Un suivi ouvert n'a pas de résultat définitif. Un suivi supprimé ne doit pas
alimenter le tableau de bord opérationnel.
