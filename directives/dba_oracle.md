# DIRECTIVE : Administration de Bases de Données (DBA Oracle 19c)

Cette directive définit les standards d'exploitation, de sauvegarde et d'optimisation pour les bases de données Oracle Database 19c.

---

## 1. Stratégie de Sauvegarde RMAN

* **Mode Archivelog :**
  - Toutes les bases de production doivent être en mode `ARCHIVELOG`.
* **Politique de Rétention RMAN :**
  - `CONFIGURE RETENTION POLICY TO RECOVERY WINDOW OF 14 DAYS;`
  - `CONFIGURE CONTROLFILE AUTOBACKUP ON;`
* **Planning des Sauvegardes :**
  - **Niveau 0 (Complète) :** Hebdomadaire (le dimanche à 01:00).
  - **Niveau 1 (Incrémentale) :** Quotidienne (du lundi au samedi à 01:00).
  - **Archivelogs :** Sauvegarde et suppression toutes les heures.
* **Script Type RMAN (Niveau 0) :**
  ```rman
  RUN {
    ALLOCATE CHANNEL c1 DEVICE TYPE DISK;
    BACKUP INCREMENTAL LEVEL 0 DATABASE PLUS ARCHIVELOG DELETE INPUT;
    RELEASE CHANNEL c1;
  }
  ```

---

## 2. Tuning des Performances (AWR / ASH)

* **Automatic Workload Repository (AWR) :**
  - Fréquence des snapshots : Toutes les 60 minutes.
  - Durée de rétention des snapshots : 8 jours (par défaut).
  - Génération de rapports AWR (`awrrpt.sql`) en cas de dégradation de performance constatée sur une période donnée.
* **Active Session History (ASH) :**
  - Analyse des sessions actives en temps réel via la vue `V$ACTIVE_SESSION_HISTORY`.
  - Utilisation du script `ashrpt.sql` pour diagnostiquer les pics d'activité transitoires (quelques minutes).

---

## 3. Conformité & Sécurité des Données

* **Gestion des Comptes & Mots de passe :**
  - Aucun mot de passe en dur dans les scripts.
  - Utilisation systématique de portefeuilles Oracle Wallet (Secure External Password Store - SEPS) ou chargement depuis le fichier `.env`.
* **Principe du Moindre Privilège :**
  - Attribution stricte des rôles. Accès `SYSDBA` restreint au groupe d'administration OS `dba`.
  - Audit actif sur les connexions sensibles et modifications de schémas (DDL).
