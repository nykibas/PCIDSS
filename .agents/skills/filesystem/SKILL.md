---
name: filesystem
description: Interagir avec le système de fichiers local via le serveur MCP Filesystem. Permet la lecture, l'écriture, la recherche et le listing sécurisé de fichiers.
---

# Guide d'utilisation du serveur MCP Filesystem

Ce skill documente les outils fournis par le serveur MCP Filesystem pour interagir en toute sécurité avec le répertoire de travail `d:\InfraManagement`.

## 🛠️ Outils disponibles

Le serveur MCP filesystem expose les outils suivants :

1. **`read_file`**
   - **Arguments :** `path` (chemin absolu ou relatif)
   - **Description :** Lit l'intégralité du contenu d'un fichier texte en UTF-8.
2. **`write_file`**
   - **Arguments :** `path` (chemin), `content` (contenu texte)
   - **Description :** Crée un nouveau fichier ou remplace le contenu d'un fichier existant.
3. **`list_directory`**
   - **Arguments :** `path` (chemin du répertoire)
   - **Description :** Liste les fichiers et dossiers dans un répertoire spécifié.
4. **`directory_tree`**
   - **Arguments :** `path` (chemin du répertoire)
   - **Description :** Renvoie une arborescence récursive du répertoire spécifié.
5. **`search_nodes`**
   - **Arguments :** `query` (terme de recherche), `path` (répertoire dans lequel chercher)
   - **Description :** Recherche des fichiers par leur nom ou leur contenu.

## 🔒 Règles de sécurité importantes

- **Périmètre autorisé :** Seul le répertoire `d:\InfraManagement` est accessible. Toute tentative de lecture ou d'écriture en dehors de ce répertoire provoquera une erreur d'autorisation.
- **Accords Utilisateurs :** L'assistant demandera l'approbation de l'utilisateur avant d'écrire ou de modifier des fichiers critiques.
