# BON - Specifications techniques

## 1. Architecture technique

BON repose sur les couches suivantes:

- CLI Python,
- moteur de sessions Playwright,
- SQLite comme stockage central,
- file de taches persistante,
- monitoring local,
- et modules metier specialises.

## 2. Composants principaux

- `__main__.py`: point d'entree.
- `libs/cli_v14.py`: CLI et menu interactif.
- `libs/database.py`: acces aux donnees et bootstrap.
- `libs/session_manager.py`: gestion des sessions isolees.
- `libs/task_queue.py`: file de traitement.
- `libs/monitor.py`: supervision et health score.
- `libs/social_actions.py`: actions metier Playwright.

## 3. Stockage

La base SQLite contient notamment:

- `accounts`
- `robots`
- `groups`
- `robot_groups`
- `campaigns`
- `campaign_variants`
- `publications`
- `published_comments`
- `dm_queue`
- `tasks`

## 4. Strategie de bootstrap

Au demarrage:

- la base est initialisee,
- les migrations idempotentes sont appliquees,
- les donnees de test sont seedées si necessaire,
- les robots recoivent leurs groupes et campagnes par defaut.

## 5. Menu interactif

Le mode sans argument doit:

- detecter un terminal interactif,
- afficher un menu numerique,
- proposer les actions principales,
- et se terminer apres execution de l'action choisie.

## 6. Regles techniques

- Ne pas demander la ressaisie manuelle des donnees de base.
- Utiliser SQLite comme source de verite locale.
- Garder le fonctionnement compatible avec les appels CLI classiques.
- Rendre les seed et upserts idempotents.
- Eviter de casser les tests existants.

## 7. Gestion des donnees de test

Les donnees de test comprennent:

- des robots de base,
- des groupes de test,
- des campagnes de test,
- et des variantes textuelles pour validation du flux.

## 8. Qualite attendue

- Démarrage reproductible.
- Donnees persistantes.
- Lecture simple du schema.
- Code reorganise par responsabilite.
- Journalisation suffisante pour le diagnostic.
