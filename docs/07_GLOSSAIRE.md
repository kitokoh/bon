# BON - Glossaire

## Termes principaux

- Account: compte operationnel rattache a un robot.
- Bootstrap: initialisation automatique des donnees de base.
- Campaign: ensemble de messages ou variantes lies a un objectif.
- CLI: interface en ligne de commande.
- Group: groupe Facebook stocke par son URL.
- Monitor: composant de supervision et de score de sante.
- Publication: trace d'une action de publication.
- Robot: instance operationnelle isolee associee a un compte.
- Session: contexte Playwright isole pour un robot.
- Seed: donnees de test injectees par defaut.
- SQLite: base locale embarquee du projet.
- Task: entree de file de traitement.
- Variant: variante de texte d'une campagne.

## Expressions internes

- Source de verite: donnee consideree comme reference pour le projet.
- Donnees de test: jeux de donnees minimaux fournis par defaut.
- Menu interactif: mode sans argument qui propose les actions principales.
- Resume de reprise: documentation necessaire pour reprendre le projet sans contexte oral.
- Assignation: liaison d'un groupe ou d'une campagne a un robot.

## Regles de lecture

- Un robot n'est pas un compte Facebook en soi, mais une instance technique associee a un compte.
- Un groupe est identifie par son URL canonique.
- Une campagne peut contenir plusieurs variantes.
- Le seed de test doit rester distinct des donnees operationnelles.
