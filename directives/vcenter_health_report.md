# DIRECTIVE : Rapport Quotidien de Santé vCenter 8 & Virtualisation

Cette directive définit les seuils d'alerte, la périodicité et les standards de restitution pour le rapport de santé automatisé du cluster VMware vCenter 8.

---

## 1. Métriques & Seuils d'Alerte

| Indicateur (KPI) | Niveau Normal | Avertissement (Warning) | Critique (Critical) |
| :--- | :--- | :--- | :--- |
| **Utilisation CPU Hôte/Cluster** | < 75% | 75% à 85% | > 85% |
| **Utilisation RAM Hôte/Cluster** | < 80% | 80% à 90% | > 90% |
| **Occupation Datastores SAN** | < 75% | 75% à 85% | > 85% |
| **Ancienneté des Snapshots VM** | Aucune | > 48 heures | > 72 heures |
| **Alertes vSphere Active** | 0 | Alertes mineures | Alarme majeure / critique |
| **Statut Hôtes ESXi** | Connected | Maintenance Mode | Disconnected / Not Responding |

---

## 2. Format & Diffusion

* **Périodicité :** Quotidienne (exécution chaque matin à 07h00).
* **Destinataire principal :** `DSI@solidairebanque.com`
* **Supports livrés :**
  1. **Document PDF (`Rapport_Sante_vCenter_YYYYMMDD.pdf`) :** Document officiel structuré avec tableaux KPI, état des ESXi, datastores et snapshots.
  2. **Page HTML (`Rapport_Sante_vCenter_YYYYMMDD.html`) :** Rapport interactif autonome avec design responsive.
* **Corps de l'e-mail (Executive Summary) :**
  - Doit présenter les **Faits Saillants** de manière concise (synthèse synthétique des anomalies, taux de disponibilité global, action urgente requise le cas échéant).

---

## 3. Politiques de Rétention & Log

* **Rétention des rapports :** Conservés pendant **30 jours** dans `/var/log/automation/vcenter_reports/`.
* **Rétention des logs d'exécution :** Logged dans `/var/log/automation/vcenter_health.log`.
* **Prise en charge de panne :** En cas d'inaccessibilité du vCenter, le script émet une alerte critique immédiate vers la supervision Zabbix et tente 3 nouvelles tentatives espacées de 5 minutes.
