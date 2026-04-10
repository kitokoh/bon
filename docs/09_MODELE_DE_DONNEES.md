# BON - Modele de donnees

## 1. Objectif

Ce document resume les tables principales et leurs relations pour faciliter la reprise et les evolutions du schema.

## 2. Tables principales

### accounts

Contient les comptes operationnels.

Champs utiles:

- `id`
- `name`
- `email`
- `profile_url`
- `status`
- `health_score`

### robots

Contient les robots techniques rattaches aux comptes.

Champs utiles:

- `id`
- `robot_name`
- `account_id`
- `storage_state_path`
- `proxy_server`
- `active`

### groups

Contient les groupes identifiables par URL.

Champs utiles:

- `id`
- `url`
- `name`
- `category`
- `language`
- `quality_score`
- `active`

### robot_groups

Table de liaison entre robots et groupes.

Champs utiles:

- `robot_id`
- `group_id`
- `active`

### campaigns

Contient les campagnes de publication.

### campaign_variants

Contient les variantes de texte rattachees a une campagne.

### publications

Historique des publications.

### tasks

File de traitement persistante.

## 3. Relations

- `accounts` 1 -> n `robots`
- `robots` n -> n `groups` via `robot_groups`
- `campaigns` 1 -> n `campaign_variants`
- `robots` 1 -> n `publications`
- `groups` 1 -> n `publications`

## 4. Regles de schema

- L'URL du groupe doit rester unique.
- Le nom du robot doit rester unique.
- Le nom de campagne doit rester unique.
- Les variantes doivent etre uniques a l'interieur d'une campagne.
- Les tables de liaison doivent prevenir les doublons.

## 5. Donnees de test

Le seed par defaut doit creer:

- des comptes de test,
- des robots de test,
- des groupes de test,
- des campagnes de test,
- et des affectations valides.

## 6. Points d'attention

- La base SQLite est la reference locale.
- Les JSON peuvent servir d'import, mais pas de verite courante.
- Toute nouvelle table doit etre documentee ici.
