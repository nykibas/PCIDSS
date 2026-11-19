# Déploiement d'un SIEM Wazuh (Single-Node) via Docker sur OS basé sur Red Hat

## Contexte et Objectif
Ce document décrit la procédure complète pour déployer une stack SIEM **Wazuh** (Indexer, Server/Manager, Dashboard) en architecture *single-node* à l'aide de **Docker** et **Docker Compose** sur un système d'exploitation basé sur Red Hat (**RHEL**, **Rocky Linux**, **AlmaLinux** ou **CentOS Stream**).

---

## Prérequis Système
* **Système d'exploitation :** RHEL 8/9, Rocky Linux 8/9, AlmaLinux 8/9 ou CentOS Stream.
* **Ressources matérielles minimales :** 4 à 8 Go de RAM (8 Go recommandés), 2 à 4 vCPU, et au moins 50 Go d'espace disque libre pour la rétention des logs.
* **Privilèges :** Accès `root` ou utilisateur avec droits `sudo`.

---

## Étape 1 : Installation de Docker Engine et Docker Compose
Sur les systèmes basés sur Red Hat, installer Docker CE depuis le dépôt officiel (à préférer à Podman pour la compatibilité native avec les scripts officiels Wazuh).

```bash
# 1. Installer les utilitaires de gestion de dépôts
sudo dnf install -y dnf-plugins-core git

# 2. Ajouter le dépôt officiel Docker
# Note : Utiliser 'rhel' pour Red Hat Enterprise Linux, ou 'centos' pour Rocky/AlmaLinux/CentOS Stream
sudo dnf config-manager --add-repo https://docker.com
# Alternative pour Rocky/AlmaLinux :
# sudo dnf config-manager --add-repo https://docker.com

# 3. Installer Docker Engine, containerd et le plugin Docker Compose
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 4. Démarrer et activer le service Docker au démarrage
sudo systemctl enable --now docker
```

---

## Étape 2 : Configuration du Noyau et du Pare-feu (`firewalld`)
1. **Paramètre mémoire pour Wazuh Indexer (OpenSearch) :**
   ```bash
   sudo sysctl -w vm.max_map_count=262144
   echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
   ```

2. **Ouverture des ports dans `firewalld` :**
   * `443/tcp` : Accès HTTPS au Wazuh Dashboard.
   * `1514/tcp` : Réception des événements et logs des agents Wazuh.
   * `1515/tcp` : Enrôlement automatique des nouveaux agents Wazuh.

   ```bash
   sudo firewall-cmd --permanent --add-port=443/tcp
   sudo firewall-cmd --permanent --add-port=1514/tcp
   sudo firewall-cmd --permanent --add-port=1515/tcp
   sudo firewall-cmd --reload
   ```

---

## Étape 3 : Déploiement de la Stack Wazuh
1. **Cloner le dépôt officiel Wazuh Docker :**
   ```bash
   git clone https://github.com
   cd wazuh-docker/single-node
   ```

2. **Générer les certificats SSL internes :**
   ```bash
   docker compose -f generate-indexer-certs.yml run --rm generator
   ```

3. **Démarrer les conteneurs en arrière-plan :**
   ```bash
   docker compose up -d
   ```

4. **Vérifier l'état des conteneurs :**
   ```bash
   docker compose ps
   ```

---

## Étape 4 : Accès et Vérification
* **URL du Dashboard :** `https://<IP_DU_SERVEUR>`
* **Identifiants par défaut :**
  * **Utilisateur :** `admin`
  * **Mot de passe :** `SecretPassword`

---

## Dépannage et Notes Spécifiques RHEL / SELinux
* **SELinux :** Sur les versions récentes de RHEL/Rocky/AlmaLinux avec Docker CE, le déploiement fonctionne généralement sans modification. En cas d'erreur de permission (`Permission denied`) sur les volumes montés dans les logs des conteneurs, ajouter le flag `:Z` à la fin des déclarations de volumes dans `docker-compose.yml` (exemple : `./config/wazuh_indexer/wazuh.indexer.yml:/usr/share/wazuh-indexer/config/opensearch.yml:Z`).
* **Mémoire insuffisante :** Si le conteneur `wazuh.indexer` redémarre en boucle, vérifier que `vm.max_map_count` est bien appliqué (`sysctl vm.max_map_count`) et ajuster la mémoire JVM (`OPENSEARCH_JAVA_OPTS`) dans `docker-compose.yml`.
