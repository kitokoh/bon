# BON - Regles metier detaillees

## 1. Regle de base

Les donnees utiles au fonctionnement doivent etre stockees dans SQLite et non ressaisies a chaque lancement.

## 2. Robots

- Un robot represente une instance d'execution.
- Un robot a un nom stable.
- Un robot peut avoir des groupes et campagnes rattaches.
- Un robot de test doit avoir au moins un contenu et plusieurs groupes.

## 3. Groupes

- Un groupe est stocke par URL.
- Un groupe peut etre visible dans la liste globale ou dans la liste d'un robot.
- Un groupe peut etre partage entre robots.
- Un groupe peut etre exporte dans un fichier texte.

## 4. Campagnes et variantes

- Une campagne contient le fond du message.
- Une variante correspond a une version textuelle.
- Une variante peut avoir un poids.
- Le systeme doit savoir choisir une variante sans saisie manuelle.

## 5. Publications

- Une publication doit conserver une trace du robot, de la cible et du contenu.
- Une publication reussie doit etre historisee.
- Les doublons doivent etre evites autant que possible.

## 6. Menu interactif

- Si aucun argument n'est donne, le systeme peut proposer un menu.
- Le menu doit s'appuyer sur les donnees deja presentes en base.
- Le choix de l'utilisateur doit declencher une action metier.

## 7. Donnees de test

- Les donnees de test servent a valider le menu et la reprise.
- Les robots de test doivent etre suffisants pour observer le comportement.
- Les groupes de test doivent etre assignes automatiquement.

## 8. Reprise et maintenance

- Les mises a jour des groupes et des contenus doivent pouvoir venir d'un outil externe.
- La console ne doit pas etre l'unique lieu de saisie.
- Les operations courantes doivent rester compréhensibles pour un nouvel arrivant.

## 9. Exceptions et arbitrages

- Si une campagne manque, le systeme peut tomber sur le contenu de test par defaut.
- Si un robot n'a pas de groupes, le bootstrap doit en fournir.
- Si un groupe fourni est absent, il doit etre ajoute ou rattache dans le cadre du seed.
