# Déploiement Automatisé SIEM Wazuh (Single-Node) via Ansible Automation Platform (AAP)

Ce projet Ansible automatise de bout en bout le déploiement d'une plateforme **SIEM Wazuh** (*Indexer, Manager, Dashboard*) sur **RHEL 9** hébergée sur **VMware vCenter 8**, à partir d'**Ansible Automation Platform (AAP)**.

---

## Architecture du projet

```text
DeploiementSIEM/
├── ansible.cfg
├── collections/
│   └── requirements.yml              # Collections community.vmware, community.general, ansible.posix, community.docker
├── group_vars/
│   └── all.yml                       # Variables par défaut (surchargeables via Survey AAP)
├── playbooks/
│   └── deploy_wazuh.yml              # Playbook principal (3 phases)
├── roles/
│   ├── vmware_provision/             # Scoring ESXi (RAM/CPU), choix Datastore, clonage RHEL 9 + disque 100 Go
│   ├── rhel_satellite/               # Enregistrement Red Hat Satellite, prérequis, LVM XFS sur /var/lib/docker
│   ├── docker_engine/                # Installation Docker CE & Docker Compose v2 + rotation logs
│   └── wazuh_single_node/            # sysctl, firewalld, SELinux, certificats SSL, stack Wazuh & healthcheck
└── aap/
    ├── survey_spec.json              # Définition du Survey AAP prêt à l'emploi
    └── custom_credential_satellite_wazuh.yml  # Modèle de Custom Credential Type AAP
```

---

## Algorithme de sélection de l'hôte ESXi optimal

Lors de la **Phase 1** (`roles/vmware_provision`), le job interroge vCenter 8 (`schema: vsphere`) pour tous les hôtes ESXi du cluster cible :

1. **Filtrage d'éligibilité :**
   - État `connected`
   - Hors mode maintenance (`inMaintenanceMode == false`)
   - Mémoire libre suffisante : $\text{RAM libre} \ge \text{RAM VM} + 2048\text{ Mo}$ (marge de sécurité)
2. **Scoring pondéré :**
   $$\text{Score} = 0.6 \times \frac{\text{RAM libre}}{\text{RAM totale}} + 0.4 \times \frac{\text{CPU libre (MHz)}}{\text{CPU total (MHz)}}$$
3. **Datastore automatique :** si `vcenter_datastore: "auto"`, le datastore accessible ayant le plus d'espace libre (minimum $\text{Disque Docker} + 60\text{ Go}$) est retenu automatiquement.

---

## Mise en œuvre dans Ansible Automation Platform (AAP)

### 1. Prérequis Execution Environment (EE)
L'Execution Environment utilisé par le Job Template doit embarquer :
- Le paquet Python `pyVmomi` (requis par `community.vmware`)
- Les collections listées dans `collections/requirements.yml` (installées automatiquement par AAP lors de la synchro Projet si autorisé, ou pré-buildées dans l'EE via `ansible-builder`).

### 2. Credentials à attacher au Job Template AAP
Aucun secret n'est stocké dans Git. Attachez **3 Credentials** au Job Template :
1. **VMware vCenter** *(type natif AAP)* : injecte automatiquement `VMWARE_HOST`, `VMWARE_USER`, `VMWARE_PASSWORD`.
2. **Machine Credential** *(type natif AAP)* : clé SSH privée correspondant à l'utilisateur `wazuh_ssh_user` (par défaut `ansible`) présent dans le template RHEL 9, avec élévation `sudo`.
3. **Satellite & Wazuh SIEM Secrets** *(Custom Credential Type)* : créé à partir de `aap/custom_credential_satellite_wazuh.yml` pour injecter `SATELLITE_ACTIVATION_KEY` et les mots de passe Wazuh.

### 3. Configuration du Job Template AAP
- **Inventory :** un inventaire contenant `localhost` (`ansible_connection=local`). La VM cible est ajoutée dynamiquement en mémoire (`add_host`) durant l'exécution.
- **Project :** ce dépôt Git.
- **Playbook :** `playbooks/deploy_wazuh.yml`.
- **Survey :** importer ou recréer les questions décrites dans `aap/survey_spec.json`.

---

## Sécurité, SELinux et Rollback

- **Moindre privilège réseau :** seuls les ports `443/tcp` (Dashboard), `1514/tcp` (Agents) et `1515/tcp` (Enrôlement) sont ouverts dans `firewalld`.
- **SELinux Enforcing :** le contexte `container_file_t` est appliqué automatiquement sur `/opt/wazuh-docker/single-node/config` afin d'éviter toute erreur `Permission denied` sans désactiver SELinux.
- **Stratégie de Rollback :** la **Phase 3** crée automatiquement un snapshot VMware quiescé (`post-wazuh-deploy-<version>`) une fois le Dashboard validé en HTTP 200/302, avant l'intégration dans les jobs de sauvegarde **Veeam**.
