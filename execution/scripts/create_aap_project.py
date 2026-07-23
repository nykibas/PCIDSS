import os
import sys
import json
import urllib.request
import urllib.error
import ssl
import base64

def load_secrets():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    # Load unencrypted infra.env
    env_path = os.path.join(project_root, "infra.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
                    
    # Load encrypted secrets dynamically
    try:
        sys.path.insert(0, script_dir)
        import decrypt_secrets
        secrets_path = os.path.join(project_root, ".secrets.env.enc")
        if os.path.exists(secrets_path):
            cipher = decrypt_secrets.get_cipher()
            with open(secrets_path, "rb") as f:
                decrypted = cipher.decrypt(f.read()).decode("utf-8")
            for line in decrypted.splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[-] Erreur de déchiffrement : {e}")

def api_request(url, method="GET", data=None, username="", password=""):
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(url, method=method)
    
    if username and password:
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
        req.add_header("Authorization", f"Basic {b64_auth}")
        
    if data is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(data).encode("utf-8")
        
    try:
        with urllib.request.urlopen(req, context=context) as response:
            res_body = response.read().decode('utf-8')
            return json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"[-] HTTP Error {e.code}: {err_body}")
        return None
    except Exception as e:
        print(f"[-] Request Error: {e}")
        return None

def main():
    print("[*] Initialisation de la configuration...")
    load_secrets()
    
    # Force bypass proxy completely since user confirmed no proxy is needed for AAP
    if "http_proxy" in os.environ:
        del os.environ["http_proxy"]
    if "https_proxy" in os.environ:
        del os.environ["https_proxy"]
    
    # Configuration AAP
    server = os.environ.get("ANSIBLE_SERVER", "ansible-ap.solidairebanque.com")
    username = os.environ.get("ANSIBLE_LOGIN", "admin")
    password = os.environ.get("ANSIBLE_PASSWORD", "")
    
    if not password:
        print("[-] ERREUR: ANSIBLE_PASSWORD introuvable en mémoire.")
        sys.exit(1)
        
    base_url = f"https://{server}/api/controller/v2"
    
    print(f"[*] Connexion à l'API AAP : {base_url}")
    
    # 1. Obtenir l'ID de l'organisation SOLIDAIRE BANQUE
    org_name = "SOLIDAIRE BANQUE"
    org_url = f"{base_url}/organizations/?name={urllib.parse.quote(org_name)}"
    org_res = api_request(org_url, username=username, password=password)
    
    org_id = 1
    if org_res and org_res.get("count", 0) > 0:
        org_id = org_res["results"][0]["id"]
        print(f"[+] Organisation '{org_name}' trouvée (ID: {org_id})")
    else:
        print(f"[-] Organisation '{org_name}' introuvable, utilisation de l'ID 1 par défaut.")
        
    # 2. Vérifier si le projet existe
    project_name = "Unification des accès SSH"
    proj_url = f"{base_url}/projects/?name={urllib.parse.quote(project_name)}"
    proj_res = api_request(proj_url, username=username, password=password)
    
    # Paramètres exacts de l'utilisateur
    github_url = "https://github.com/nykibas/PCIDSS.git"
    
    project_payload = {
        "name": project_name,
        "description": "Projet de déploiement des accès SSH asymétriques pour les nœuds Windows et Linux (Master Playbook).",
        "organization": org_id,
        "scm_type": "git",
        "scm_url": github_url,
        "scm_branch": "main",
        "scm_clean": True,
        "scm_update_on_launch": True
    }
    
    project_id = None
    if proj_res and proj_res.get("count", 0) > 0:
        project_id = proj_res["results"][0]["id"]
        print(f"[*] Projet existant trouvé (ID: {project_id}). Mise à jour en cours...")
        update_url = f"{base_url}/projects/{project_id}/"
        res = api_request(update_url, method="PATCH", data=project_payload, username=username, password=password)
        if res:
            print("[+] Projet mis à jour avec succès.")
    else:
        print("[*] Création du nouveau projet...")
        create_url = f"{base_url}/projects/"
        res = api_request(create_url, method="POST", data=project_payload, username=username, password=password)
        if res and "id" in res:
            project_id = res["id"]
            print(f"[+] Projet créé avec succès (ID: {project_id}).")
        else:
            print("[-] Échec de la création du projet.")
            sys.exit(1)
            
    # 3. Déclencher une mise à jour SCM (Synchronisation)
    if project_id:
        print(f"[*] Lancement de la synchronisation SCM (Project Update) pour l'ID {project_id}...")
        sync_url = f"{base_url}/projects/{project_id}/update/"
        sync_res = api_request(sync_url, method="POST", data={}, username=username, password=password)
        if sync_res and "id" in sync_res:
            print(f"[+] Synchronisation lancée (Job ID: {sync_res['id']}).")
        else:
            print("[-] Impossible de lancer la synchronisation ou elle est déjà en cours.")

if __name__ == "__main__":
    main()
