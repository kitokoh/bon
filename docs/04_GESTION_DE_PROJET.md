# BON - Gestion de projet

## 1. Objectif de pilotage

La gestion de projet doit permettre de:

- cadrer le besoin,
- suivre l'avancement,
- identifier les risques,
- verifier la qualite,
- et garder une trace claire des decisions.

## 2. Phases

### Phase 1 - Cadrage

- recueil du besoin,
- definition du perimetre,
- priorisation des usages,
- validation des contraintes.

### Phase 2 - Modelisation

- schema des donnees,
- relations entre robots, groupes et campagnes,
- definition des flux principaux.

### Phase 3 - Implementation

- menu interactif,
- bootstrap SQLite,
- assignment automatique des groupes de test,
- lecture centralisee des contenus.

### Phase 4 - Verification

- tests unitaires,
- verification de compilation,
- verification des seeds,
- tests de demarrage.

### Phase 5 - Stabilisation

- correction des retours,
- nettoyage des ecarts,
- durcissement du bootstrap,
- consolidation de la documentation.

## 3. Livrables attendus

- cahier des charges,
- specifications fonctionnelles,
- specifications techniques,
- modelisation,
- plan d'action,
- journal des arbitrages,
- et guide de reprise.

## 4. Risques

- instabilite des interfaces externes,
- donnes de test insuffisantes,
- divergence entre la documentation et le code,
- dette technique dans le schema,
- oubli de mise a jour d'un nouveau flux.

## 5. Mesures de mitigation

- seed automatique idempotent,
- tests de fumee,
- documentation indexee,
- revue reguliere de coherences,
- priorite a la persistance des donnees.

## 6. Definition de fini

Un lot est considere termine si:

- le besoin est documente,
- le comportement attendu est explicite,
- le code est aligne,
- les donnees de test existent,
- et les tests de base passent.
