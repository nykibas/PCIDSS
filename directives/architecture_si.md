# DIRECTIVE : Architecture des Systèmes d'Information (SI)

Cette directive définit les standards d'urbanisation, de haute disponibilité, de résilience et de virtualisation pour l'ensemble du SI.

---

## 1. Urbanisation & Résilience (PRA / PCA)

### Plan de Reprise d'Activité (PRA)
* **Objectif de Temps de Restauration (RTO) :** < 4 heures pour les applications critiques (Niveau 1).
* **Objectif de Point de Récupération (RPO) :** < 1 heure pour les bases de données de production.
* **Stratégie Multi-Site :** Réplication asynchrone des stockage SAN entre le site principal (DC1) et le site secondaire (DC2).

### Plan de Continuité d'Activité (PCA)
* Double adduction réseau sur les routeurs de bordure.
* Utilisation de répartiteurs de charge (Load Balancers) avec détection de panne matérielle active/active.

---

## 2. Sauvegardes & Restauration (Veeam Backup & Replication)

* **Politique de Sauvegarde :**
  - Sauvegarde quotidienne complète synthétique (Synthetic Full) avec conservation de 30 jours (30 points de restauration).
  - Sauvegarde incrémentale toutes les 4 heures pendant les heures ouvrées.
* **Règle du 3-2-1 :**
  - **3** copies des données.
  - **2** types de supports différents.
  - **1** copie hors site (dans DC2 ou Cloud immuable stocké sur Veeam Hardened Repository).

---

## 3. Connectivité Réseau Résiliente (Starlink Business)

* **Rôle :** Liaison WAN de secours (Failover) automatique en cas de coupure de la fibre principale.
* **Configuration SD-WAN :**
  - Priorisation des flux SSH/Oracle SQL*Net sur la liaison Starlink en mode dégradé.
  - Limitation des flux non essentiels (mises à jour système, téléchargements lourds) via Starlink.

---

## 4. Virtualisation (VMware vCenter 8 & ESXi)

* **Haute Disponibilité (vSphere HA) :**
  - Admission Control configuré pour tolérer la panne d'un hôte ESXi par cluster.
  - Surveillance des VMs active pour redémarrer automatiquement les VMs dont l'OS ne répond plus (Heartbeat VMware Tools).
* **Optimisation des ressources (vSphere DRS) :**
  - Mode entièrement automatisé (Fully Automated), niveau de migration 3.
  - Règles d'affinité/anti-affinité pour séparer les serveurs applicatifs redondants sur des hôtes physiques différents.
