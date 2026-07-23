# Directive : Architecture des Accès Administratifs (SSH)

## 1. Objectif de la Directive
L'ensemble du parc serveur (Red Hat Enterprise Linux et Microsoft Windows Server) doit être pilotable de manière homogène via **Ansible Automation Platform (AAP)** en utilisant exclusivement le protocole **SSH**.
Toute authentification basée sur un mot de passe (y compris via WinRM sur Windows) est déclarée obsolète et considérée comme un risque de sécurité.

## 2. Principes Fondamentaux de Sécurité (Zero Trust)
1. **Authentification Asymétrique :** La connexion doit être obligatoirement établie via une clé SSH publique forte (Ed25519 ou RSA 4096).
2. **Compte de Service Standardisé :** Il est interdit d'utiliser le compte `root` (Linux) ou `Administrator` (Windows) pour l'exécution des tâches d'orchestration. Un compte de service dédié nommé `ladmin` doit être utilisé de manière transversale.
3. **Élévation de Privilèges Sans Prompt :** 
   - Sur Linux : Le compte `ladmin` doit être configuré avec un accès `sudo` total sans exigence de mot de passe (`NOPASSWD: ALL`).
   - Sur Windows : Le compte `ladmin` doit appartenir au groupe local `Administrators` (S-1-5-32-544).
4. **Hardenisation OpenSSH :**
   - Sur Windows, le shell par défaut (DefaultShell) doit être positionné sur PowerShell.
   - Sur Linux, `PasswordAuthentication no` doit être configuré dans `sshd_config` après déploiement.

## 3. Implémentation sur Microsoft Windows
Le déploiement et le support du serveur OpenSSH sur Windows sont régis par les règles suivantes :
- Le composant optionnel (Feature) `OpenSSH.Server~~~~0.0.1.0` doit être installé sur chaque hôte.
- Le service système `sshd` doit être configuré en démarrage `Automatic`.
- Pour les membres du groupe administrateurs, le démon Microsoft OpenSSH s'attend strictement à lire le fichier `administrators_authorized_keys` situé dans le dossier restreint `C:\ProgramData\ssh\`.
- Les droits d'accès (ACL) à ce fichier de clés doivent impérativement interdire l'accès en écriture à tout compte non-administrateur ou non-SYSTEM.

## 4. Maintenance de la Clé AAP
- La paire de clés privée/publique de l'Ansible Automation Platform doit être générée sans passphrase (pour permettre l'automatisation sans supervision).
- Elle doit être injectée dynamiquement par le système de gestion des accès privilégiés ou Ansible Vault.
