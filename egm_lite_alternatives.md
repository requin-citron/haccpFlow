> **BLUF:** La configuration sera stockée côté backend par utilisateur : un document de disposition contient les widgets actifs et leur largeur sur la grille. Le navigateur ne conserve plus l'état de référence.

# Alternatives Considered

## Périmètre de la configuration

### Retenu : grille de widgets éditable avec poignées

Le tableau de bord propose un mode modification. L'utilisateur ouvre une liste
de widgets disponibles, ajoute ou retire le widget Chiffre d'affaires, puis le
déplace et modifie sa largeur ou sa hauteur en tirant les poignées des quatre
côtés. Le placement s'accroche à une grille de douze colonnes et à des rangées
régulières. Le bouton de retrait est placé au-dessus de la carte pour ne pas
interférer avec les poignées.

### Écarté : options internes uniquement

Un simple bouton d'édition sur le widget permettrait de masquer certains
montants, mais le widget resterait toujours présent et à une position fixe.
Cela ne correspond qu'imparfaitement à une configuration de dashboard.

### Écarté : configuration globale par fichier d'environnement

Une configuration `.env` serait simple à déployer, mais identique pour tous les
utilisateurs et sans interaction directe dans le dashboard.

## Moteur de grille

### Retenu : grille CSS et Pointer Events natifs

Une grille CSS de douze colonnes, complétée par les Pointer Events du navigateur,
suffit pour le redimensionnement horizontal et évite une dépendance pour un
seul widget.

### Écarté : bibliothèque de grille

Une bibliothèque dédiée apporterait le déplacement et des interactions déjà
éprouvées, mais ajouterait une dépendance, du JavaScript client et des
adaptations SSR disproportionnés pour une grille à un widget dans ce premier lot.

## Persistance

### Retenu : disposition backend par utilisateur

Une table `dashboard_layouts` conserve un document JSONB de widgets par
utilisateur. Les routes `GET` et `PUT /api/v1/dashboard/layout` permettent de
charger et remplacer cette disposition. La configuration suit donc le compte sur
tous ses appareils.

### Écarté : `localStorage`

Le stockage local aurait évité une migration, mais la configuration ne serait
pas partagée entre les appareils et serait perdue lors d'un nettoyage du
navigateur.
