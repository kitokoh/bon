# BON - Architecture et flux

## 1. Architecture logique

Le projet est compose de quatre grands blocs:

- entree utilisateur,
- stockage,
- execution,
- observation.

## 2. Flux principaux

### 2.1 Demarrage

1. `__main__.py` lance la CLI.
2. `cli_v14.py` decide entre menu et commande.
3. `database.py` charge ou cree la base.
4. Le bootstrap remplit les donnees de test si besoin.

### 2.2 Publication

1. Le robot est choisi.
2. Les groupes du robot sont lus dans SQLite.
3. Une campagne est choisie.
4. Une variante est tiree.
5. Playwright tente l'action.
6. La publication est tracee.

### 2.3 Recuperation des groupes

1. L'utilisateur choisit l'option.
2. Le robot est pris en compte.
3. Les groupes sont lus depuis la table de liaison.
4. La liste est affichee ou exportee.

### 2.4 Supervision

1. Le monitor collecte les signaux.
2. Le task queue expose les statuts.
3. Le session manager expose les sessions.
4. La CLI presente un resume lisible.

## 3. Principes d'architecture

- Separation des responsabilites.
- Persistence locale explicite.
- Donnees seedées et idempotentes.
- Flux simples a reprendre.
- Compatibilite avec une couche externe PyQt.

## 4. Limites

- Pas de frontend web complet dans le coeur actuel.
- Pas de gestion collaborative distante.
- Pas de dependance a un JSON de fonctionnement.

## 5. Flux de reprise

Quand on reprend le projet, il faut:

- verifier les documents,
- verifier la base,
- verifier le bootstrap,
- verifier les robots de test,
- puis relancer le menu.
