# BON - Specifications fonctionnelles

## 1. Vue d'ensemble

L'application BON fournit un menu interactif au demarrage et des commandes CLI directes. Les fonctions principales sont:

- publier dans les groupes attribues a un robot,
- publier sur une page,
- recuperer les liens des groupes connus,
- consulter l'etat des sessions,
- et suivre la file de traitement.

## 2. Parcours utilisateur

### 2.1 Demarrage sans argument

Quand l'utilisateur lance l'application sans commande, le systeme:

1. affiche un menu numerique,
2. propose les actions principales,
3. recupere les donnees necessaires depuis SQLite,
4. execute le parcours choisi.

### 2.2 Publication dans les groupes

Flux attendu:

1. choisir un robot,
2. charger automatiquement les groupes associes a ce robot,
3. selectionner une campagne et une variante de texte,
4. ouvrir le navigateur,
5. tenter la publication groupe par groupe,
6. afficher le resultat.

### 2.3 Publication sur une page

Flux attendu:

1. choisir un robot,
2. saisir ou fournir la cible page,
3. charger un texte preenregistre,
4. executer la publication,
5. afficher l'etat final.

### 2.4 Recuperation des liens de groupes

Flux attendu:

1. choisir un robot ou demander tous les robots,
2. lister les groupes associes depuis SQLite,
3. afficher les URLs,
4. exporter la liste dans un fichier texte si demande.

## 3. Regles metier

- Un robot doit pouvoir fonctionner avec des groupes predefinis.
- Les textes ne doivent pas etre saisis manuellement a chaque lancement.
- Les donnees de test doivent exister par defaut.
- Une campagne peut contenir plusieurs variantes ponderees.
- Les groupes peuvent etre reutilises par plusieurs robots.

## 4. Cas d'utilisation

### UC1 - Lancer une action au demarrage

Acteur: operateur

Preconditions:

- l'application est installee,
- la base SQLite est accessible.

Resultat:

- l'action choisie est lancee.

### UC2 - Recuperer les groupes d'un robot

Acteur: operateur

Preconditions:

- au moins un robot existe,
- des groupes sont assignes.

Resultat:

- la liste des groupes est affichee ou exportee.

### UC3 - Alimenter la base de test

Acteur: systeme

Preconditions:

- aucune donnee de test n'est encore presente, ou le bootstrap est force.

Resultat:

- des robots, groupes et campagnes de test sont disponibles.

## 5. Critères de validation

- Le menu apparait au demarrage.
- Une selection numerique declenche une action concrete.
- Les groupes associes a un robot sont automatiquement proposes.
- Les donnees de test sont visibles en lecture sans saisie manuelle.
