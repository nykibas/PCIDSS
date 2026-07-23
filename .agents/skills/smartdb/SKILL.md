---
name: smartdb
description: Gateway de base de données universel via SmartDB_MCP. Fournit des outils d'exploration de structure de tables, d'analyse de santé des bases de données et d'optimisation de requêtes SQL.
---

# Guide d'utilisation de SmartDB_MCP

Ce skill documente les outils fournis par le serveur MCP `smartdb` pour interagir avec, explorer et optimiser les bases de données relationnelles du SI (notamment l'instance Oracle 19c configurée).

## 🛠️ Outils disponibles

Le serveur MCP `smartdb` expose les outils suivants :

1. **`get_db_version`**
   - **Description :** Retourne la version de la base de données connectée.
2. **`get_table_name`**
   - **Arguments :** Aucun ou filtre textuel
   - **Description :** Liste toutes les tables ou recherche des tables spécifiques.
3. **`get_table_desc`**
   - **Arguments :** `table_names` (liste de tables)
   - **Description :** Retourne la structure DDL et les colonnes des tables spécifiées.
4. **`get_table_index`**
   - **Arguments :** `table_names` (liste de tables)
   - **Description :** Liste les index associés aux tables.
5. **`execute_sql`**
   - **Arguments :** `sql` (requête SQL)
   - **Description :** Exécute des commandes SQL. Les commandes sont soumises à vérification de rôle (ex: `readonly` ou `admin` selon configuration).
6. **`get_db_health`**
   - **Description :** Analyse la santé globale (verrous, transactions actives, sessions, charge) et génère un rapport de diagnostic.
7. **`sql_creator`**
   - **Arguments :** `prompt` (description en langage naturel), `db_type` (type de base)
   - **Description :** Génère une syntaxe SQL valide et optimisée pour la base cible.
8. **`sql_optimize`**
   - **Arguments :** `sql` (requête à optimiser), `table_info` (optionnel)
   - **Description :** Fournit des conseils experts basés sur le plan d'exécution pour améliorer le temps de réponse de la requête.

## 🔒 Bonnes pratiques d'exploitation

- **Rôle d'administration :** L'agent dispose par défaut du rôle `admin` sur l'instance Oracle. Valider systématiquement l'impact d'une modification DDL (ALTER, DROP) sur le plan de sauvegarde/PRA.
- **Optimisation active :** Toujours soumettre les requêtes complexes à l'outil `sql_optimize` avant de les déployer.
