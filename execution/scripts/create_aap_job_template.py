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
    print("[*] Initialisation de la configuration pour Job Template...")
    load_secrets()
    
    # Bypass proxy
    if "http_proxy" in os.environ:
        del os.environ["http_proxy"]
    if "https_proxy" in os.environ:
        del os.environ["https_proxy"]
    
    server = os.environ.get("ANSIBLE_SERVER", "ansible-ap.solidairebanque.com")
    username = os.environ.get("ANSIBLE_LOGIN", "admin")
    password = os.environ.get("ANSIBLE_PASSWORD", "")
    
    if not password:
        print("[-] ERREUR: ANSIBLE_PASSWORD introuvable.")
        sys.exit(1)
        
    base_url = f"https://{server}/api/controller/v2"
    
    # 1. Obtenir l'ID du projet
    project_name = "Unification des accès SSH"
    proj_url = f"{base_url}/projects/?name={urllib.parse.quote(project_name)}"
    proj_res = api_request(proj_url, username=username, password=password)
    
    project_id = None
    if proj_res and proj_res.get("count", 0) > 0:
        project_id = proj_res["results"][0]["id"]
        print(f"[+] Projet '{project_name}' trouvé (ID: {project_id}).")
    else:
        print("[-] ERREUR: Le projet est introuvable. Exécutez d'abord le script de création du projet.")
        sys.exit(1)
        
    # 2. Créer le Job Template
    jt_name = "Déploiement des clés SSH (Bootstrap)"
    jt_url = f"{base_url}/job_templates/"
    
    # On demande l'inventaire et les credentials au lancement car on ne connaît pas leurs IDs d'avance
    jt_payload = {
        "name": jt_name,
        "description": "Job Template pour le déploiement initial des clés asymétriques SSH AAP sur les serveurs Windows et Linux.",
        "project": project_id,
        "playbook": "execution/ansible/bootstrap_ssh_keys.yml",
        "ask_inventory_on_launch": True,
        "ask_credential_on_launch": True,
        "ask_limit_on_launch": True,
        "become_enabled": True  # Indispensable pour l'escalade de privilèges (Linux)
    }
    
    # Vérifier si le Job Template existe déjà
    check_url = f"{base_url}/job_templates/?name={urllib.parse.quote(jt_name)}"
    check_res = api_request(check_url, username=username, password=password)
    
    if check_res and check_res.get("count", 0) > 0:
        jt_id = check_res["results"][0]["id"]
        print(f"[*] Job Template existant trouvé (ID: {jt_id}). Mise à jour en cours...")
        update_url = f"{base_url}/job_templates/{jt_id}/"
        res = api_request(update_url, method="PATCH", data=jt_payload, username=username, password=password)
        if res:
            print("[+] Job Template mis à jour avec succès.")
    else:
        print("[*] Création du nouveau Job Template...")
        res = api_request(jt_url, method="POST", data=jt_payload, username=username, password=password)
        if res and "id" in res:
            print(f"[+] Job Template '{jt_name}' créé avec succès (ID: {res['id']}).")
        else:
            print("[-] Échec de la création du Job Template.")
            sys.exit(1)

if __name__ == "__main__":
    main()
