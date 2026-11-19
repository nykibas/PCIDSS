#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration automatisée et idempotente d'Ansible Automation Platform (AAP)
pour le déploiement du SIEM Wazuh (Single-Node) - Solidaire Banque.

Crée ou met à jour :
1. Custom Credential Type : "Satellite & Wazuh SIEM Secrets"
2. Credential : "Satellite & Wazuh SIEM - Prod" (Activation Key ak_rhel9_prd)
3. Inventory : "SIEM_Wazuh_Provisioning" (avec localhost)
4. Project Git : "Deploiement SIEM Wazuh" (https://github.com/nykibas/PCIDSS.git)
5. Job Template : "Deploiement SIEM Wazuh (Single-Node)" + Credentials + Survey
"""

import os
import sys
import ssl
import json
import base64
import urllib.request
import urllib.error
import urllib.parse

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SIEM_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(SIEM_DIR)
EXEC_SCRIPTS = os.path.join(PROJECT_ROOT, "execution", "scripts")
if EXEC_SCRIPTS not in sys.path:
    sys.path.insert(0, EXEC_SCRIPTS)

import decrypt_secrets


def load_env():
    infra_env = os.path.join(PROJECT_ROOT, "infra.env")
    if os.path.exists(infra_env):
        with open(infra_env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

    secrets_path = os.path.join(PROJECT_ROOT, ".secrets.env.enc")
    if os.path.exists(secrets_path):
        cipher = decrypt_secrets.get_cipher()
        with open(secrets_path, "rb") as f:
            for line in cipher.decrypt(f.read()).decode("utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

    for pv in ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]:
        os.environ.pop(pv, None)


class AAPClient:
    def __init__(self, host, username, password):
        self.base_url = f"https://{host}/api/controller/v2"
        b64 = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {b64}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def req(self, method, path, payload=None):
        url = f"{self.base_url}/{path.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        r = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(r, context=self.ctx, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"AAP API {method} {url} -> HTTP {e.code}: {err_body}") from e

    def find_by_name(self, resource, name):
        q = urllib.parse.urlencode({"name": name})
        res = self.req("GET", f"{resource}/?{q}")
        results = res.get("results", [])
        return results[0] if results else None


def main():
    load_env()
    aap = AAPClient(
        os.environ["ANSIBLE_SERVER"],
        os.environ["ANSIBLE_LOGIN"],
        os.environ["ANSIBLE_PASSWORD"],
    )
    org_id = 1  # Default

    # 1. Custom Credential Type : Satellite & Wazuh SIEM Secrets
    ct_name = "Satellite & Wazuh SIEM Secrets"
    ct_payload = {
        "name": ct_name,
        "description": "Injecte l'Activation Key Red Hat Satellite et les secrets optionnels Wazuh",
        "kind": "cloud",
        "inputs": {
            "fields": [
                {
                    "id": "satellite_activation_key",
                    "type": "string",
                    "label": "Red Hat Satellite Activation Key",
                    "secret": True,
                },
                {
                    "id": "wazuh_indexer_password",
                    "type": "string",
                    "label": "Wazuh Indexer Admin Password (optionnel)",
                    "secret": True,
                },
                {
                    "id": "wazuh_api_password",
                    "type": "string",
                    "label": "Wazuh API Password (optionnel)",
                    "secret": True,
                },
                {
                    "id": "wazuh_dashboard_password",
                    "type": "string",
                    "label": "Wazuh Dashboard Password (optionnel)",
                    "secret": True,
                },
            ],
            "required": ["satellite_activation_key"],
        },
        "injectors": {
            "env": {
                "SATELLITE_ACTIVATION_KEY": "{{ satellite_activation_key }}",
                "WAZUH_INDEXER_PASSWORD": "{{ wazuh_indexer_password }}",
                "WAZUH_API_PASSWORD": "{{ wazuh_api_password }}",
                "WAZUH_DASHBOARD_PASSWORD": "{{ wazuh_dashboard_password }}",
            }
        },
    }
    ct = aap.find_by_name("credential_types", ct_name)
    if ct:
        ct = aap.req("PATCH", f"credential_types/{ct['id']}/", ct_payload)
        print(f"[OK] Custom Credential Type mis a jour : id={ct['id']} ({ct_name})")
    else:
        ct = aap.req("POST", "credential_types/", ct_payload)
        print(f"[OK] Custom Credential Type cree : id={ct['id']} ({ct_name})")

    # 2. Credential : Satellite & Wazuh SIEM - Prod
    cred_name = "Satellite & Wazuh SIEM - Prod"
    ak_value = os.environ.get("SATELLITE_ACTIVATION_KEY", "ak_rhel9_prd")
    cred_payload = {
        "name": cred_name,
        "description": "Activation Key RHEL 9 Prod (SOLIDAIRE BANQUE) et secrets Wazuh",
        "organization": org_id,
        "credential_type": ct["id"],
        "inputs": {
            "satellite_activation_key": ak_value,
        },
    }
    cred = aap.find_by_name("credentials", cred_name)
    if cred:
        cred = aap.req("PATCH", f"credentials/{cred['id']}/", cred_payload)
        print(f"[OK] Credential mis a jour : id={cred['id']} ({cred_name})")
    else:
        cred = aap.req("POST", "credentials/", cred_payload)
        print(f"[OK] Credential cree : id={cred['id']} ({cred_name})")

    # 3. Inventory : SIEM_Wazuh_Provisioning (+ host localhost)
    inv_name = "SIEM_Wazuh_Provisioning"
    inv = aap.find_by_name("inventories", inv_name)
    if not inv:
        inv = aap.req("POST", "inventories/", {
            "name": inv_name,
            "description": "Inventaire dédié au provisioning VMware + déploiement dynamique SIEM Wazuh",
            "organization": org_id,
        })
        print(f"[OK] Inventory cree : id={inv['id']} ({inv_name})")
    else:
        print(f"[OK] Inventory existant : id={inv['id']} ({inv_name})")

    hosts = aap.req("GET", f"inventories/{inv['id']}/hosts/?name=localhost").get("results", [])
    if not hosts:
        aap.req("POST", f"inventories/{inv['id']}/hosts/", {
            "name": "localhost",
            "description": "Control node local pour Phase 1 (vCenter) et Phase 3 (Snapshot)",
            "enabled": True,
            "variables": "ansible_connection: local\nansible_python_interpreter: '{{ ansible_playbook_python }}'\n",
        })
        print(f"[OK] Host 'localhost' ajoute a l'inventaire {inv_name}")
    else:
        print(f"[OK] Host 'localhost' deja present dans {inv_name}")

    # 4. Project Git : Deploiement SIEM Wazuh
    proj_name = "Deploiement SIEM Wazuh"
    proj_payload = {
        "name": proj_name,
        "description": "Déploiement automatisé SIEM Wazuh Single-Node sur RHEL 9 / vCenter 8 / Satellite",
        "organization": org_id,
        "scm_type": "git",
        "scm_url": "https://github.com/nykibas/PCIDSS.git",
        "scm_branch": "main",
        "scm_clean": True,
        "scm_delete_on_update": False,
        "scm_update_on_launch": True,
        "default_environment": 2,  # Hub Default execution environment
    }
    proj = aap.find_by_name("projects", proj_name)
    if proj:
        proj = aap.req("PATCH", f"projects/{proj['id']}/", proj_payload)
        print(f"[OK] Project mis a jour : id={proj['id']} ({proj_name})")
    else:
        proj = aap.req("POST", "projects/", proj_payload)
        print(f"[OK] Project cree : id={proj['id']} ({proj_name})")

    # 5. Job Template : Deploiement SIEM Wazuh (Single-Node)
    jt_name = "Deploiement SIEM Wazuh (Single-Node)"
    jt_payload = {
        "name": jt_name,
        "description": "Provisioning VM RHEL 9 sur l'hôte ESXi optimal (HQDCKN), enregistrement Satellite, LVM /var/lib/docker, Docker CE et stack SIEM Wazuh Single-Node",
        "job_type": "run",
        "inventory": inv["id"],
        "project": proj["id"],
        "playbook": "DeploiementSIEM/playbooks/deploy_wazuh.yml",
        "execution_environment": 2,  # Hub Default execution environment
        "verbosity": 0,
        "become_enabled": False,
        "survey_enabled": True,
        "ask_variables_on_launch": True,
    }
    jt = aap.find_by_name("job_templates", jt_name)
    if jt:
        jt = aap.req("PATCH", f"job_templates/{jt['id']}/", jt_payload)
        print(f"[OK] Job Template mis a jour : id={jt['id']} ({jt_name})")
    else:
        jt = aap.req("POST", "job_templates/", jt_payload)
        print(f"[OK] Job Template cree : id={jt['id']} ({jt_name})")

    # Associer les 3 Credentials (vCenter id=6, Local Admin id=4, Satellite & Wazuh SIEM - Prod)
    for cid, label in [(6, "vCenter Solidaire Banque"), (4, "Local Admin"), (cred["id"], cred_name)]:
        aap.req("POST", f"job_templates/{jt['id']}/credentials/", {"id": cid})
        print(f"  [+] Credential associe : id={cid} ({label})")

    # Uploader le Survey Spec
    survey_path = os.path.join(SCRIPT_DIR, "survey_spec.json")
    with open(survey_path, "r", encoding="utf-8") as sf:
        survey_spec = json.load(sf)
    aap.req("POST", f"job_templates/{jt['id']}/survey_spec/", survey_spec)
    print(f"[OK] Survey AAP configure ({len(survey_spec['spec'])} questions) sur Job Template id={jt['id']}")

    print("\n=== RESUME AAP ===")
    print(f"URL Job Template : https://{os.environ['ANSIBLE_SERVER']}/execution/templates/job-template/{jt['id']}/details")


if __name__ == "__main__":
    main()
