# DIRECTIVE : Administration Système Red Hat Enterprise Linux (RHEL)

Cette directive standardise les opérations d'administration, de sécurisation et de mise à jour sur les serveurs RHEL 8, 9 et 10.

---

## 1. Durcissement de la Sécurité (Hardening)

* **SSH / Accès Distant :**
  - Authentification par clé SSH uniquement (`PasswordAuthentication no`).
  - Interdiction de l'accès direct en root (`PermitRootLogin no`).
  - Port SSH personnalisé ou accès restreint via Bastion.
* **Pare-feu (firewalld) :**
  - Règle par défaut : Tout rejeter (`drop` ou `reject`).
  - Autoriser uniquement les ports explicitement nécessaires (ex: 22 pour SSH, 1521 pour Oracle listener, 9100 pour Zabbix agent).
* **SELinux :**
  - SELinux doit TOUJOURS être configuré en mode **Enforcing** (`SELINUX=enforcing` dans `/etc/selinux/config`).
  - Toute modification de politique SELinux doit être documentée et réalisée via des modules ou règles personnalisées (`semanage`, `restorecon`).

---

## 2. Gestion des Paquets & Dépôts (Red Hat Satellite)

* **Enregistrement des Serveurs :**
  - Tous les serveurs RHEL doivent être enregistrés auprès de Red Hat Satellite à l'aide d'une clé d'activation (`subscription-manager register --org="MonOrg" --activationkey="Key-RHEL-9"`).
* **Cycle de Vie (Content Views) :**
  - Les correctifs de sécurité (Errata) sont appliqués mensuellement après validation en environnement de test.

---

## 3. Configuration des Proxys Réseau

* **Variables d'Environnement Système :**
  - Déclarer les variables de proxy dans `/etc/profile.d/proxy.sh` :
    ```bash
    export http_proxy="http://proxy.entreprise.internal:8080"
    export https_proxy="http://proxy.entreprise.internal:8080"
    export no_proxy="localhost,127.0.0.1,.entreprise.internal"
    ```
* **Configuration dnf/yum :**
  - Configurer le proxy dans `/etc/dnf/dnf.conf` (ou `/etc/yum.conf`) :
    ```ini
    proxy=http://proxy.entreprise.internal:8080
    ```

---

## 4. Standardisation des Scripts Bash

* **Sécurité d'exécution :**
  - Commencer tous les scripts par `set -euo pipefail` pour s'assurer qu'un script s'arrête immédiatement en cas d'erreur ou d'utilisation de variable non définie.
* **Logs & Traçabilité :**
  - Rediriger les sorties vers syslog ou des fichiers de logs dédiés sous `/var/log/automation/`.
