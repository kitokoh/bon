# Guide pour la Gestion Manuelle des Sélecteurs Facebook

Ce guide a pour but de vous aider à comprendre et à mettre à jour les sélecteurs CSS ou XPath utilisés par le bot pour interagir avec les pages Facebook. Facebook modifie régulièrement sa structure HTML, ce qui peut rendre les sélecteurs invalides et empêcher le bot de fonctionner correctement.

## Table des Matières
1.  [Qu'est-ce qu'un Sélecteur ?](#1-quest-ce-quun-sélecteur-)
2.  [Outils Nécessaires](#2-outils-nécessaires)
3.  [Comment Trouver un Sélecteur ?](#3-comment-trouver-un-sélecteur-)
    *   [Utilisation des Outils de Développement du Navigateur](#utilisation-des-outils-de-développement-du-navigateur)
    *   [Choisir de Bons Sélecteurs CSS](#choisir-de-bons-sélecteurs-css)
    *   [Choisir de Bons Sélecteurs XPath](#choisir-de-bons-sélecteurs-xpath)
    *   [Conseils pour des Sélecteurs Robustes](#conseils-pour-des-sélecteurs-robustes)
4.  [Tester vos Sélecteurs](#4-tester-vos-sélecteurs)
    *   [Dans la Console du Navigateur](#dans-la-console-du-navigateur)
5.  [Comprendre et Mettre à Jour `config/selectors.json`](#5-comprendre-et-mettre-à-jour-configselectorsjson)
    *   [Structure du Fichier](#structure-du-fichier)
    *   [Modifier un Sélecteur Existant](#modifier-un-sélecteur-existant)
6.  [Le Mode "Fallback Manuel" du Bot (Prochainement)](#6-le-mode-fallback-manuel-du-bot-prochainement)

---

## 1. Qu'est-ce qu'un Sélecteur ?

Un sélecteur est une chaîne de caractères qui identifie de manière unique un ou plusieurs éléments (comme un bouton, un champ de texte, un lien, etc.) sur une page web. Le bot utilise ces sélecteurs pour savoir où cliquer, où écrire du texte, etc.

Il existe principalement deux types de sélecteurs que nous utilisons :
*   **Sélecteurs CSS :** Utilisent la syntaxe CSS pour cibler les éléments. Ils sont souvent plus lisibles et plus rapides.
*   **Sélecteurs XPath :** Permettent de naviguer dans la structure XML/HTML d'une page. Ils sont plus puissants et peuvent cibler des éléments difficilement accessibles avec CSS, mais peuvent être plus lents et plus complexes.

---

## 2. Outils Nécessaires

*   Un navigateur web moderne (Google Chrome ou Firefox sont recommandés).
*   Les **Outils de Développement** intégrés à votre navigateur (généralement accessibles en faisant un clic droit sur un élément de la page et en choisissant "Inspecter" ou "Inspecter l'élément", ou en appuyant sur F12).

---

## 3. Comment Trouver un Sélecteur ?

### Utilisation des Outils de Développement du Navigateur

1.  **Ouvrez Facebook** dans votre navigateur et naviguez jusqu'à la page ou l'action qui pose problème au bot.
2.  **Faites un clic droit** sur l'élément que vous souhaitez cibler (par exemple, le bouton "Publier", le champ de texte pour écrire un post).
3.  Dans le menu contextuel, choisissez **"Inspecter"** ou **"Inspecter l'élément"**.
    ![Image exemple inspecter element](https://i.stack.imgur.com/s2wUq.png) (*Note: Ceci est une image placeholder, une image réelle du menu inspecter serait mieux ici.*)
4.  Les Outils de Développement s'ouvriront, mettant en surbrillance le code HTML de l'élément que vous avez sélectionné.
    ![Image exemple HTML surligne](https://developer.chrome.com/static/docs/devtools/dom/images/elements-panel-highlighted.png) (*Note: Placeholder.*)

### Choisir de Bons Sélecteurs CSS

Une fois l'élément HTML en surbrillance :

*   **Recherchez des attributs `id` uniques :** Si l'élément a un `id` (par exemple, `<div id="submit_button">`), le sélecteur CSS est simple et généralement robuste : `#submit_button`.
*   **Recherchez des attributs `class` spécifiques :** Les classes sont souvent utilisées pour le style, mais certaines peuvent être uniques ou suffisamment distinctives.
    *   Exemple : `<button class="post-button action-submit">` pourrait être ciblé par `.post-button` ou `.action-submit`. Si plusieurs classes sont nécessaires pour l'unicité : `.post-button.action-submit`.
    *   **Attention :** Facebook utilise souvent des classes générées automatiquement qui changent fréquemment (ex: `_a23b _x4yz`). Évitez celles-ci autant que possible.
*   **Utilisez les attributs `aria-label`, `role`, `data-testid` ou autres attributs significatifs :** Ce sont souvent de bons candidats pour des sélecteurs stables.
    *   `[aria-label="Publier"]` : Cible un élément ayant l'attribut `aria-label` égal à "Publier". C'est très utilisé dans le `selectors.json` actuel pour gérer le multilinguisme.
    *   `[data-testid="composer-submit-button"]` : Cible un élément avec l'attribut `data-testid`.
    *   `button[role="button"]` : Cible un élément `<button>` ayant l'attribut `role="button"`.
*   **Combinaisons et relations parent-enfant :**
    *   `div.container > button.submit` : Cible un bouton avec la classe `submit` qui est un enfant direct d'un div avec la classe `container`.
    *   `form textarea[name="message"]` : Cible un `textarea` avec l'attribut `name="message"` à l'intérieur d'un `form`.

### Choisir de Bons Sélecteurs XPath

XPath est utile lorsque les CSS ne suffisent pas, par exemple pour remonter dans l'arborescence DOM ou pour trouver des éléments en fonction de leur contenu textuel.

1.  Dans les Outils de Développement (onglet Éléments), une fois l'élément HTML en surbrillance :
2.  Faites un clic droit sur l'élément HTML.
3.  Allez dans "Copier" -> **"Copier le XPath"** ou **"Copier le XPath complet"**.
    *   **"Copier le XPath"** essaie de donner un XPath optimisé et plus court.
    *   **"Copier le XPath complet"** donne le chemin absolu depuis la racine du document (ex: `/html/body/div[1]/div/div[...]/button`). Ces XPath complets sont **très fragiles** et doivent être évités autant que possible.

*   **Exemples de XPath utiles :**
    *   `//button[@aria-label="Publier"]` : Cible n'importe quel bouton sur la page avec l'attribut `aria-label` "Publier". (Similaire à `[aria-label="Publier"]` en CSS).
    *   `//div[contains(text(), "Texte important")]` : Cible un `div` qui contient le texte "Texte important".
    *   `//h2[text()="Titre de section"]/following-sibling::button` : Cible un bouton qui est un frère suivant un titre `h2` avec le texte "Titre de section".

### Conseils pour des Sélecteurs Robustes

*   **Privilégiez les `id`** s'ils sont uniques et semblent stables.
*   **Utilisez des attributs spécifiques à la fonctionnalité** comme `data-testid`, `aria-label`, `name`, ou `role` plutôt que des classes de style génériques.
*   **Évitez les sélecteurs trop longs ou trop spécifiques** à la structure HTML actuelle (ex: `div > div > div > span > button`). Plus c'est long, plus c'est fragile.
*   **Attention aux classes générées automatiquement** par Facebook (souvent des suites de lettres et chiffres aléatoires). Elles changent très souvent.
*   **Testez vos sélecteurs** (voir section suivante) pour vous assurer qu'ils ciblent bien l'élément désiré et *uniquement* celui-ci (sauf si vous voulez une liste d'éléments).

---

## 4. Tester vos Sélecteurs

### Dans la Console du Navigateur

Une fois que vous avez un sélecteur potentiel, vous pouvez le tester directement dans la console des Outils de Développement :

*   **Pour les sélecteurs CSS :**
    Tapez `$$("votre_selecteur_css")` dans la console et appuyez sur Entrée.
    *   Exemple : `$$("button[aria-label='Publier']")`
    *   Cela retournera un tableau (liste) des éléments correspondants. S'il y a un seul élément, c'est bon signe. Si le tableau est vide, votre sélecteur ne trouve rien. S'il y a plusieurs éléments, votre sélecteur n'est pas assez spécifique (sauf si vous attendez plusieurs résultats).
    *   Vous pouvez survoler les résultats dans la console pour les voir en surbrillance dans la page.

*   **Pour les sélecteurs XPath :**
    Tapez `$x("votre_selecteur_xpath")` dans la console et appuyez sur Entrée.
    *   Exemple : `$x("//button[@aria-label='Publier']")`
    *   Mêmes remarques que pour les sélecteurs CSS concernant le résultat.

---

## 5. Comprendre et Mettre à Jour `config/selectors.json`

Le fichier `config/selectors.json` contient tous les sélecteurs utilisés par le bot.

### Structure du Fichier

Il s'agit d'un fichier JSON qui ressemble à ceci :

```json
{
  "nom_logique_de_l_element_1": "selecteur_css_ou_xpath_pour_cet_element",
  "nom_logique_de_l_element_2": "un_autre_selecteur",
  "submit_button": "[aria-label*='Post'], [aria-label*='Publier'], ...",
  "group_link": "a[href*='/groups/']",
  // ... autres sélecteurs
}
```

*   Chaque **clé** (ex: `"submit_button"`) est un nom logique que le code du bot utilise pour se référer à un élément.
*   Chaque **valeur** est la chaîne du sélecteur CSS ou XPath.
*   Notez que pour certains sélecteurs (comme `"submit_button"`), la valeur est une longue chaîne de sélecteurs CSS séparés par des virgules. Cela permet de gérer différentes langues ou variations de l'interface Facebook. Le bot essaiera chacun de ces sélecteurs jusqu'à ce qu'il en trouve un qui fonctionne.

### Modifier un Sélecteur Existant

1.  **Identifiez la clé logique** dans `config/selectors.json` qui correspond à l'élément qui pose problème. Les noms de clés sont généralement en anglais et descriptifs (ex: `display_input`, `input`, `submit`, `group_link`).
2.  **Trouvez un nouveau sélecteur robuste** en utilisant les méthodes décrites ci-dessus.
3.  **Modifiez la valeur associée à la clé** dans `config/selectors.json` avec votre nouveau sélecteur.
    *   Si la valeur existante est une longue liste de sélecteurs (pour le multilinguisme), vous pouvez soit :
        *   Remplacer toute la liste si vous êtes sûr que votre nouveau sélecteur est universel.
        *   Ajouter votre nouveau sélecteur à la liste, séparé par une virgule (ex: `"cle": "ancien_selecteur_1, ancien_selecteur_2, votre_nouveau_selecteur"`).
4.  **Sauvegardez le fichier `config/selectors.json`.**
5.  **Redémarrez le bot** pour qu'il prenne en compte les modifications.

**Important :** Faites attention à la syntaxe JSON (virgules, guillemets). Une erreur de syntaxe peut empêcher le chargement de la configuration. Vous pouvez utiliser un validateur JSON en ligne pour vérifier votre fichier après modification.

---

## 6. Le Mode "Fallback Manuel" du Bot (Prochainement)

Une fonctionnalité est en cours de développement pour aider lorsque le bot ne trouve pas un sélecteur critique.

*   Si le bot ne parvient pas à localiser un élément essentiel, au lieu de s'arrêter brusquement, il pourra :
    1.  Vous informer de l'élément manquant (par son nom logique, ex: "submit_button").
    2.  Mettre l'exécution en pause.
    3.  Vous demander de fournir un nouveau sélecteur CSS ou XPath directement dans la console.
*   Vous pourrez alors utiliser les techniques de ce guide pour trouver un sélecteur sur la page actuellement affichée par le bot.
*   Le bot tentera ensuite d'utiliser le sélecteur que vous avez fourni pour continuer son action.

Cette fonctionnalité vise à rendre le bot plus résilient aux changements d'interface mineurs et à vous permettre de "dépanner" le bot sans avoir à modifier directement `config/selectors.json` à chaque fois (bien que la mise à jour du fichier reste la solution à long terme pour les sélecteurs cassés).

---

Nous espérons que ce guide vous sera utile ! Maintenir les sélecteurs à jour est un défi constant avec l'automatisation de sites comme Facebook.
