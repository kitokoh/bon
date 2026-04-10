# BON - Plan de test et qualite

## 1. Objectif

Ce document fixe les verifications minimales pour garder le projet coherent.

## 2. Tests a garder

- lancement de la CLI,
- test de fumee,
- verification du bootstrap,
- verification des groupes du robot,
- compilation Python,
- lecture des statistiques de base.

## 3. Tests fonctionnels essentiels

### TF1 - Menu interactif

- Lancer `python __main__.py`.
- Verifier l'affichage du menu.
- Choisir une action.
- Verifier la sortie attendue.

### TF2 - Groupes du robot

- Lire les groupes assignes a `robot1`.
- Verifier que la liste n'est pas vide.

### TF3 - Seed de test

- Recréer ou forcer la base.
- Verifier qu'au moins des robots, groupes et campagnes existent.

## 4. Tests techniques essentiels

- `py_compile` sur les modules principaux.
- `pytest` sur le test smoke.
- verification de la base SQLite.
- verification des imports principaux.

## 5. Definition de qualite

Le projet est considere suffisamment sain si:

- les donnees de test sont visibles,
- le menu se lance,
- les docs sont alignes avec le code,
- la base reste la source de verite,
- et les changements restent compréhensibles.

## 6. Recommandation

A chaque modification importante:

- relancer les tests minimaux,
- verifier les seeds,
- mettre a jour la documentation correspondante.
