# BON - Cahier des charges complet

## 1. Rôle du document

Ce document est la reference de cadrage du projet BON. Il rassemble la vision produit, les objectifs, le perimetre, les contraintes, les exigences principales et les criteres de succes.

Les autres documents du dossier `docs/` precisent ensuite:

- les specifications fonctionnelles,
- les specifications techniques,
- la modelisation,
- la gestion de projet,
- et le guide de reprise.

## 2. Vision produit

BON est une application locale de pilotage et d'automatisation organisee autour de robots isoles, de donnees centralisees en SQLite et d'un menu interactif de demarrage.

L'objectif n'est pas uniquement de lancer des actions ponctuelles. Le projet vise une vraie plateforme de travail, capable de:

- conserver les groupes et contenus en base,
- associer les donnees aux robots,
- automatiser les actions repetitives,
- proposer des comportements coherents au demarrage,
- permettre une reprise rapide du projet,
- et faciliter la maintenance par une autre personne ou par un outil externe comme l'app PyQt.

## 3. Problematique adressee

Le projet repond a plusieurs besoins frequents:

- eviter de ressaisir les groupes a chaque execution,
- eviter de conserver la logique metier dans des fichiers JSON fragiles,
- centraliser les donnees utiles dans SQLite,
- garder des robots distincts avec leurs propres affectations,
- rendre le lancement plus simple pour l'operateur,
- et documenter clairement le systeme pour qu'il soit transmissible.

## 4. Objectifs fonctionnels

### 4.1 Pilotage au demarrage

Au lancement sans argument, l'application doit afficher un menu simple et exploitable permettant de:

- publier dans les groupes d'un robot,
- publier sur une page,
- recuperer les liens des groupes,
- ou quitter proprement.

### 4.2 Gestion des robots

Le projet doit permettre de:

- creer un robot,
- lui associer un compte,
- lui lier des groupes,
- lui lier des campagnes,
- et consulter son etat.

### 4.3 Gestion des contenus

Le projet doit pouvoir:

- stocker des campagnes,
- stocker des variantes de texte,
- choisir un texte preenregistre,
- et reutiliser ces contenus sans saisie manuelle.

### 4.4 Gestion des groupes

Le projet doit:

- conserver les groupes en SQLite,
- associer un groupe a un ou plusieurs robots,
- afficher les groupes d'un robot,
- et exporter la liste des groupes si besoin.

### 4.5 Supervision

Le projet doit fournir:

- un etat de session,
- une vision de la file,
- des informations de sante,
- et des elements de diagnostic.

## 5. Perimetre fonctionnel

### Inclus

- CLI interactive,
- CLI classique par commande,
- bootstrap des donnees de test,
- stockage SQLite,
- gestion des robots,
- gestion des groupes,
- gestion des campagnes et variantes,
- export des groupes,
- supervision locale,
- documentation structurante,
- et reprise du projet.

### Exclu

- interface web complete,
- synchronisation distante temps reel,
- travail multi-utilisateur collaboratif,
- consolidation cloud,
- et toute fonctionnalite non documentee ou non validee par le projet.

## 6. Acteurs

- Operateur: lance les actions et consulte l'etat.
- Developpeur: maintient le code et les donnees.
- Testeur: verifie les flux et les retours.
- Repreneur: reprend le projet avec la documentation.
- Outil externe PyQt: met a jour les groupes et les contenus.

## 7. Exigences metier

### 7.1 Donnees centralisees

Les groupes, campagnes et variantes doivent etre stockes dans SQLite et non traites comme de simples fichiers decoratifs.

### 7.2 Donnees de test par defaut

Le projet doit disposer de donnees minimales pour fonctionner sans configuration manuelle initiale.

### 7.3 Affectation automatique

Chaque robot de test doit disposer d'au moins quelques groupes et d'un contenu associe.

### 7.4 Pas de ressaisie repetitive

L'operateur ne doit pas avoir a inserer un a un les groupes a chaque lancement.

### 7.5 Transmissibilite

Le projet doit pouvoir etre repris par une autre personne grace a la documentation et au schema de donnees.

## 8. Exigences non fonctionnelles

### 8.1 Robustesse

- Les seed doivent etre idempotents.
- Les migrations doivent etre tolerantes.
- Le demarrage doit etre reproductible.

### 8.2 Lisibilite

- Les responsabilites doivent etre separees.
- Les donnees doivent etre documentees.
- Les points d'entree doivent etre identifiables.

### 8.3 Maintenabilite

- La logique importante doit etre en base ou en code, pas dans des fichiers temporaires.
- Les evolutions doivent pouvoir etre tracees.
- Le projet doit rester compatible avec la CLI et l'app PyQt.

### 8.4 Exploitabilite

- Un menu interactif doit simplifier les usages courants.
- Les commandes CLI doivent rester disponibles pour l'automatisation.
- Les donnees de test doivent permettre une verification rapide.

## 9. Architecture de principe

Le projet s'articule autour de:

- `__main__.py` comme point d'entree,
- `libs/cli_v14.py` pour la logique de commande et le menu,
- `libs/database.py` pour le modele persistant,
- `libs/session_manager.py` pour les sessions isolees,
- `libs/task_queue.py` pour les travaux differes,
- `libs/monitor.py` pour l'observation,
- `libs/social_actions.py` pour les actions metier,
- et `docs/` pour le cadrage et la transmission.

## 10. Modelisation fonctionnelle

### Entites principales

- Robot
- Account
- Group
- Campaign
- Variant
- Publication
- Task
- Session

### Relations attendues

- un robot possede une affectation de groupes,
- un robot peut referencer plusieurs campagnes,
- une campagne contient plusieurs variantes,
- une publication reference une cible et un contenu,
- une session represente l'execution isolee d'un robot.

## 11. Cycle de vie attendu

1. Lancer l'application.
2. Afficher le menu ou executer la commande.
3. Charger les donnees SQLite.
4. Recuperer les robots et leurs groupes.
5. Choisir une campagne et une variante.
6. Executer l'action.
7. Enregistrer les traces.
8. Revenir a l'etat stable.

## 12. Donnees de test

Les donnees de test doivent couvrir:

- au moins un robot actif,
- au moins un groupe fourni par l'utilisateur ou par le seed,
- au moins deux campagnes de test,
- plusieurs variantes de texte,
- et des assignations suffisantes pour valider le menu.

## 13. Criteres de succes

Le projet est considere coherent si:

- le lancement sans argument affiche un menu utile,
- les robots de test ont des groupes visibles,
- les contenus de test sont disponibles en base,
- la suppression des ressaisies manuelles est effective,
- la reprise est possible sans contexte oral,
- et la documentation raconte la meme histoire que le code.

## 14. Contraintes et arbitrages

### Contraintes

- conserver SQLite comme source locale principale,
- rester compatible avec l'app PyQt existante,
- ne pas imposer une saisie manuelle continue,
- maintenir la CLI pour les usages techniques.

### Arbitrages

- JSON peut rester comme format d'import ou d'archivage,
- mais la verite operationnelle doit rester dans SQLite.
- Le menu interactif sert l'operateur,
- la CLI conserve la precision et l'automatisation.

## 15. Risques

- divergence entre la doc et le code,
- seed insuffisant,
- confusion entre donnees de test et donnees reelles,
- surcharge des responsabilites dans un seul fichier,
- evolution non documentee du schema SQLite.

## 16. Mesures de maitrise

- maintenir les documents du dossier `docs/` a jour,
- garder un bootstrap explicite,
- documenter les nouvelles tables,
- verifier les seeds par test,
- et faire une revue rapide des ecarts a chaque evolution importante.

## 17. Liens avec les autres documents

- [Specifications fonctionnelles](01_SPECIFICATIONS_FONCTIONNELLES.md)
- [Specifications techniques](02_SPECIFICATIONS_TECHNIQUES.md)
- [Modelisation](03_MODELES_ET_MODELISATION.md)
- [Gestion de projet](04_GESTION_DE_PROJET.md)
- [Guide de reprise](05_GUIDE_DE_REPRISE_ET_EXPLOITATION.md)

## 18. Conclusion

Ce cahier des charges fixe la vision complete du projet BON:

- une base SQLite comme source de verite,
- des robots distincts,
- des contenus preenregistres,
- des groupes affectes automatiquement,
- un menu d'entree plus humain,
- et une documentation suffisante pour piloter et reprendre le projet.

Le reste du dossier `docs/` detaille ensuite comment cette vision se traduit en fonctionnel, en technique et en exploitation.
