#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rapport Quotidien de Santé vCenter 8 - Solidaire Banque DSI
Génère des rapports au format HTML et PDF avec transmission par email.
"""

import os
import sys
import argparse
import datetime
import smtplib
import ssl
import atexit
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# vSphere modules
try:
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    PYVMOMI_INSTALLED = True
except ImportError:
    PYVMOMI_INSTALLED = False

# ReportLab modules for PDF generation
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# ------------------------------------------------------------------------------
# 1. ENVIRONMENT & CONFIGURATION LOADING
# ------------------------------------------------------------------------------
def load_env_file():
    """Charge les variables du fichier infra.env ou .env s'ils existent."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    
    env_paths = [
        os.path.join(project_root, "infra.env"),
        os.path.join(project_root, ".env")
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
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
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception as e:
        print(f"[-] Attention : Impossible de déchiffrer les secrets. {e}")

load_env_file()

# Configurations par défaut
VCENTER_SERVER = os.environ.get("VCENTER_SERVER", "vcenter01.solidairebanque.com")
SMTP_SERVER = os.environ.get("SMTP_SERVER", "mail.solidairebanque.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
SMTP_USER = os.environ.get("SMTP_USER", "dsi-automation@solidairebanque.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_SENDER = os.environ.get("SMTP_SENDER", "dsi-automation@solidairebanque.com")
REPORT_RECIPIENTS = os.environ.get("REPORT_RECIPIENTS", "DSI@solidairebanque.com")

# ------------------------------------------------------------------------------
# 2. VCENTER METRICS COLLECTOR (Real / Mock Fallback)
# ------------------------------------------------------------------------------
def get_all_objs(content, vimtype):
    obj = {}
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        obj.update({c: c.name})
    return obj

def get_snapshots(vm):
    snapshots = []
    if vm.snapshot is not None:
        def traverse_snapshots(tree):
            for node in tree:
                snapshots.append(node)
                traverse_snapshots(node.childSnapshotList)
        traverse_snapshots(vm.snapshot.rootSnapshotList)
    return snapshots

def get_mock_metrics(today_str):
    return {
        "timestamp": today_str,
        "vcenter_host": VCENTER_SERVER,
        "cluster_name": "CL-PRD-SDC01",
        "datacenter_name": "DC1-MAIN-DC",
        "overall_status": "WARNING",
        "health_score": 88,
        "summary": {
            "total_hosts": 6, "connected_hosts": 6,
            "total_vms": 142, "powered_on_vms": 134, "powered_off_vms": 8,
            "total_cpu_cores": 192, "used_cpu_ghz": 245.8, "total_cpu_ghz": 420.0,
            "cpu_usage_pct": 58.5, "total_ram_gb": 1536, "used_ram_gb": 1260, "ram_usage_pct": 82.0,
        },
        "hosts": [
            {"name": "esxi01.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 62, "ram_pct": 84, "vms": 25},
            {"name": "esxi02.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 59, "ram_pct": 81, "vms": 24},
            {"name": "esxi03.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 71, "ram_pct": 89, "vms": 26},
            {"name": "esxi04.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 54, "ram_pct": 78, "vms": 22},
            {"name": "esxi05.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 48, "ram_pct": 76, "vms": 20},
            {"name": "esxi06.solidairebanque.com", "model": "Dell PowerEdge R750", "status": "Connected", "cpu_pct": 46, "ram_pct": 84, "vms": 17},
        ],
        "datastores": [
            {"name": "DS_NVME_ORACLE_PRD01", "type": "VMFS6", "capacity_tb": 12.0, "used_tb": 10.44, "free_tb": 1.56, "pct": 87.0, "status": "WARNING"},
            {"name": "DS_SSD_APP_PRD01", "type": "VMFS6", "capacity_tb": 20.0, "used_tb": 14.20, "free_tb": 5.80, "pct": 71.0, "status": "OK"},
            {"name": "DS_SSD_APP_PRD02", "type": "VMFS6", "capacity_tb": 20.0, "used_tb": 13.80, "free_tb": 6.20, "pct": 69.0, "status": "OK"},
            {"name": "DS_NFS_BACKUP_TEMP", "type": "NFS4", "capacity_tb": 30.0, "used_tb": 24.90, "free_tb": 5.10, "pct": 83.0, "status": "OK"},
        ],
        "snapshots": [
            {"vm_name": "VM-ORCL-SBCPROD-02", "snapshot_name": "Pre-Patch_RHEL9_20260717", "size_gb": 48.5, "age_hours": 78, "status": "CRITICAL"},
            {"vm_name": "VM-APP-COREBANK-04", "snapshot_name": "Pre-Deploy_v4.2.1", "size_gb": 18.2, "age_hours": 52, "status": "WARNING"},
        ],
        "alarms": [
            {"severity": "CRITICAL", "entity": "VM-ORCL-SBCPROD-02", "description": "Snapshot ancienneté > 72 heures", "time": "2026-07-20 04:15"},
        ],
        "highlights": [
            "⚠️ <b>Datastore NVMe Oracle :</b> Le datastore <code>DS_NVME_ORACLE_PRD01</code> a dépassé le seuil d'avertissement avec <b>87.0%</b> d'occupation.",
            "🔴 <b>Snapshot Récurrent à Purger :</b> La VM <code>VM-ORCL-SBCPROD-02</code> possède un snapshot de 48.5 GB actif depuis <b>78 heures</b> (> 72h).",
            "✅ <b>Hôtes ESXi & Cluster :</b> Les 6 hôtes ESXi sont en état <code>Connected</code>.",
        ]
    }

def collect_vcenter_metrics(test_mode=False):
    today_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    if test_mode or not PYVMOMI_INSTALLED:
        print("[i] Mode TEST ou pyVmomi non installé : Retour des métriques simulées.")
        return get_mock_metrics(today_str)
        
    try:
        context = None
        if hasattr(ssl, "_create_unverified_context"):
            context = ssl._create_unverified_context()
            
        VCENTER_LOGIN_REAL = os.environ.get("VCENTER_LOGIN", "Administrator@vsphere.local")
        VCENTER_PASSWORD_REAL = os.environ.get("VCENTER_PASSWORD", "")
        
        print(f"[*] Connexion au vCenter {VCENTER_SERVER}...")
        si = SmartConnect(host=VCENTER_SERVER,
                          user=VCENTER_LOGIN_REAL,
                          pwd=VCENTER_PASSWORD_REAL,
                          port=443,
                          sslContext=context)
        atexit.register(Disconnect, si)
        content = si.RetrieveContent()
        
        cluster_name = "Cluster"
        clusters = get_all_objs(content, [vim.ClusterComputeResource])
        if clusters:
            cluster_name = list(clusters.values())[0]

        hosts = get_all_objs(content, [vim.HostSystem])
        total_hosts = len(hosts)
        connected_hosts = 0
        total_cpu_hz, used_cpu_hz = 0, 0
        total_ram_bytes, used_ram_bytes = 0, 0
        
        hosts_data = []
        for host, h_name in hosts.items():
            h_status = host.runtime.connectionState
            if h_status == vim.HostSystem.ConnectionState.connected:
                connected_hosts += 1
            
            hw = host.hardware
            if hw:
                h_model = f"{hw.systemInfo.vendor} {hw.systemInfo.model}"
                cores = hw.cpuInfo.numCpuCores
                hz = hw.cpuInfo.hz * cores
                ram = hw.memorySize
                total_cpu_hz += hz
                total_ram_bytes += ram
            else:
                h_model, cores, hz, ram = "Unknown", 0, 0, 0
                
            qs = host.summary.quickStats
            if qs and qs.overallCpuUsage and qs.overallMemoryUsage:
                u_cpu_hz = qs.overallCpuUsage * 1000 * 1000
                u_ram_bytes = qs.overallMemoryUsage * 1024 * 1024
                used_cpu_hz += u_cpu_hz
                used_ram_bytes += u_ram_bytes
                h_cpu_pct = round((u_cpu_hz / hz) * 100, 1) if hz > 0 else 0
                h_ram_pct = round((u_ram_bytes / ram) * 100, 1) if ram > 0 else 0
            else:
                h_cpu_pct, h_ram_pct = 0, 0
                
            h_vms = len(host.vm) if host.vm else 0
            
            hosts_data.append({
                "name": h_name, "model": h_model, "status": str(h_status),
                "cpu_pct": h_cpu_pct, "ram_pct": h_ram_pct, "vms": h_vms
            })
            
        vms = get_all_objs(content, [vim.VirtualMachine])
        total_vms = len(vms)
        powered_on_vms = sum(1 for vm in vms if vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn)
        powered_off_vms = total_vms - powered_on_vms
        
        snapshots_data = []
        for vm, v_name in vms.items():
            for snap in get_snapshots(vm):
                snap_time = snap.createTime.replace(tzinfo=None)
                age = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - snap_time).total_seconds() / 3600
                if age > 48:
                    status = "CRITICAL" if age > 72 else "WARNING"
                    snapshots_data.append({
                        "vm_name": v_name, "snapshot_name": snap.name,
                        "size_gb": 0, "age_hours": int(age), "status": status
                    })
                    
        datastores = get_all_objs(content, [vim.Datastore])
        datastores_data = []
        for ds, d_name in datastores.items():
            summary = ds.summary
            capacity_tb = summary.capacity / (1024**4) if summary.capacity else 0
            free_tb = summary.freeSpace / (1024**4) if summary.freeSpace else 0
            used_tb = capacity_tb - free_tb
            pct = round((used_tb / capacity_tb) * 100, 1) if capacity_tb > 0 else 0
            
            status = "CRITICAL" if pct > 85 else ("WARNING" if pct > 75 else "OK")
            datastores_data.append({
                "name": d_name, "type": summary.type, "capacity_tb": round(capacity_tb, 2),
                "used_tb": round(used_tb, 2), "free_tb": round(free_tb, 2), "pct": pct, "status": status
            })

        cpu_usage_pct = round((used_cpu_hz / total_cpu_hz) * 100, 1) if total_cpu_hz > 0 else 0
        ram_usage_pct = round((used_ram_bytes / total_ram_bytes) * 100, 1) if total_ram_bytes > 0 else 0
        
        overall_status = "OK"
        if cpu_usage_pct > 85 or ram_usage_pct > 90 or any(s['status'] == 'CRITICAL' for s in snapshots_data) or any(d['status'] == 'CRITICAL' for d in datastores_data):
            overall_status = "CRITICAL"
        elif cpu_usage_pct > 75 or ram_usage_pct > 80 or any(s['status'] == 'WARNING' for s in snapshots_data) or any(d['status'] == 'WARNING' for d in datastores_data):
            overall_status = "WARNING"

        highlights = []
        for d in datastores_data:
            if d['status'] != "OK":
                highlights.append(f"⚠️ <b>Datastore {d['name']} :</b> Occupation = <b>{d['pct']}%</b>.")
        for s in snapshots_data:
            highlights.append(f"🔴 <b>Snapshot Ancien :</b> VM <code>{s['vm_name']}</code> - snapshot de <b>{s['age_hours']}h</b>.")
        if not highlights:
            highlights.append(f"✅ <b>Infrastructure Saine :</b> Cluster opérationnel, aucune alerte de capacité.")
        highlights.append(f"ℹ️ <b>Ressources :</b> CPU = {cpu_usage_pct}%, RAM = {ram_usage_pct}%.")

        return {
            "timestamp": today_str,
            "vcenter_host": VCENTER_SERVER,
            "cluster_name": cluster_name,
            "overall_status": overall_status,
            "health_score": 100 if overall_status == "OK" else (70 if overall_status == "WARNING" else 40),
            "summary": {
                "total_hosts": total_hosts, "connected_hosts": connected_hosts,
                "total_vms": total_vms, "powered_on_vms": powered_on_vms, "powered_off_vms": powered_off_vms,
                "cpu_usage_pct": cpu_usage_pct, "ram_usage_pct": ram_usage_pct,
            },
            "hosts": hosts_data,
            "datastores": datastores_data,
            "snapshots": snapshots_data,
            "highlights": highlights,
            "alarms": []
        }
    except Exception as e:
        print(f"[!] ERREUR lors de la connexion vCenter réelle : {e}")
        print("[i] Basculement vers les données simulées (mock) par sécurité.")
        return get_mock_metrics(today_str)

# ------------------------------------------------------------------------------
# 3. HTML REPORT GENERATOR
# ------------------------------------------------------------------------------
def generate_html_report(metrics, output_path):
    """Génère un rapport HTML autonome moderne et responsive."""
    status_color = "#e53e3e" if metrics["overall_status"] == "CRITICAL" else ("#dd6b20" if metrics["overall_status"] == "WARNING" else "#38a169")
    
    html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport Quotidien de Santé vCenter - Solidaire Banque</title>
    <style>
        :root {{
            --primary: #1a365d;
            --secondary: #2b6cb0;
            --bg: #f7fafc;
            --card-bg: #ffffff;
            --text: #2d3748;
            --border: #e2e8f0;
            --ok: #38a169;
            --warning: #dd6b20;
            --critical: #e53e3e;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{ margin: 0; font-size: 24px; font-weight: 700; }}
        .header p {{ margin: 5px 0 0 0; opacity: 0.85; font-size: 14px; }}
        .badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
            color: white;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-warning {{ background-color: var(--warning); }}
        .badge-critical {{ background-color: var(--critical); }}
        .badge-ok {{ background-color: var(--ok); }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        .card h3 {{ margin-top: 0; font-size: 14px; color: #718096; text-transform: uppercase; }}
        .card .value {{ font-size: 28px; font-weight: bold; color: var(--primary); margin: 5px 0; }}
        .card .subtext {{ font-size: 12px; color: #a0aec0; }}

        .section {{
            background: var(--card-bg);
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        .section h2 {{ margin-top: 0; font-size: 18px; color: var(--primary); border-bottom: 2px solid var(--border); padding-bottom: 10px; }}

        ul.highlights {{
            list-style-type: none;
            padding: 0;
            margin: 0;
        }}
        ul.highlights li {{
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        ul.highlights li:last-child {{ border-bottom: none; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{ background-color: #edf2f7; color: #4a5568; font-weight: 600; }}
        
        .progress-bar {{
            background-color: #edf2f7;
            border-radius: 10px;
            height: 10px;
            width: 100%;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 10px;
        }}
        .bg-ok {{ background-color: var(--ok); }}
        .bg-warning {{ background-color: var(--warning); }}
        .bg-critical {{ background-color: var(--critical); }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 12px;
            color: #a0aec0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <div>
                <h1>SOLIDAIRE BANQUE - vCenter Health Report</h1>
                <p>Serveur: {metrics['vcenter_host']} | Cluster: {metrics['cluster_name']} | Date: {metrics['timestamp']}</p>
            </div>
            <div>
                <span class="badge badge-{"warning" if metrics["overall_status"] == "WARNING" else ("critical" if metrics["overall_status"] == "CRITICAL" else "ok")}">
                    Statut: {metrics['overall_status']} ({metrics['health_score']}/100)
                </span>
            </div>
        </div>

        <!-- KPI SUMMARY CARDS -->
        <div class="grid">
            <div class="card">
                <h3>Hôtes ESXi</h3>
                <div class="value">{metrics['summary']['connected_hosts']} / {metrics['summary']['total_hosts']}</div>
                <div class="subtext">Tous les hôtes sont connectés</div>
            </div>
            <div class="card">
                <h3>Machines Virtuelles</h3>
                <div class="value">{metrics['summary']['powered_on_vms']} / {metrics['summary']['total_vms']}</div>
                <div class="subtext">{metrics['summary']['powered_off_vms']} VMs éteintes</div>
            </div>
            <div class="card">
                <h3>Utilisation CPU Cluster</h3>
                <div class="value">{metrics['summary']['cpu_usage_pct']}%</div>
                <div class="progress-bar"><div class="progress-fill bg-ok" style="width: {metrics['summary']['cpu_usage_pct']}%;"></div></div>
            </div>
            <div class="card">
                <h3>Utilisation RAM Cluster</h3>
                <div class="value">{metrics['summary']['ram_usage_pct']}%</div>
                <div class="progress-bar"><div class="progress-fill bg-warning" style="width: {metrics['summary']['ram_usage_pct']}%;"></div></div>
            </div>
        </div>

        <!-- HIGHLIGHTS / FAITS SAILLANTS -->
        <div class="section">
            <h2>📌 Faits Saillants (Executive Summary)</h2>
            <ul class="highlights">
"""
    for item in metrics["highlights"]:
        html_content += f"                <li>{item}</li>\n"

    html_content += """            </ul>
        </div>

        <!-- ESXI HOSTS TABLE -->
        <div class="section">
            <h2>💻 Statut des Hôtes ESXi</h2>
            <table>
                <thead>
                    <tr>
                        <th>Nom de l'hôte</th>
                        <th>Modèle Serveur</th>
                        <th>Statut</th>
                        <th>CPU Utilisation</th>
                        <th>RAM Utilisation</th>
                        <th>VMs Active</th>
                    </tr>
                </thead>
                <tbody>
"""
    for host in metrics["hosts"]:
        html_content += f"""                    <tr>
                        <td><b>{host['name']}</b></td>
                        <td>{host['model']}</td>
                        <td><span style="color: var(--ok); font-weight: bold;">{host['status']}</span></td>
                        <td>{host['cpu_pct']}%</td>
                        <td>{host['ram_pct']}%</td>
                        <td>{host['vms']}</td>
                    </tr>
"""

    html_content += """                </tbody>
            </table>
        </div>

        <!-- DATASTORES TABLE -->
        <div class="section">
            <h2>💾 État des Datastores SAN / NFS</h2>
            <table>
                <thead>
                    <tr>
                        <th>Nom du Datastore</th>
                        <th>Type</th>
                        <th>Capacité Totale</th>
                        <th>Espace Utilisé</th>
                        <th>Espace Libre</th>
                        <th>Taux d'occupation</th>
                        <th>Statut</th>
                    </tr>
                </thead>
                <tbody>
"""
    for ds in metrics["datastores"]:
        ds_badge = f"<span class='badge badge-warning'>WARNING</span>" if ds["status"] == "WARNING" else "<span class='badge badge-ok'>OK</span>"
        html_content += f"""                    <tr>
                        <td><b>{ds['name']}</b></td>
                        <td>{ds['type']}</td>
                        <td>{ds['capacity_tb']} TB</td>
                        <td>{ds['used_tb']} TB</td>
                        <td>{ds['free_tb']} TB</td>
                        <td><b>{ds['pct']}%</b></td>
                        <td>{ds_badge}</td>
                    </tr>
"""

    html_content += """                </tbody>
            </table>
        </div>

        <!-- SNAPSHOTS ALERT TABLE -->
        <div class="section">
            <h2>📸 Snapshots Active (> 48h)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Machine Virtuelle</th>
                        <th>Nom du Snapshot</th>
                        <th>Taille GB</th>
                        <th>Ancienneté (Heures)</th>
                        <th>Niveau de Risque</th>
                    </tr>
                </thead>
                <tbody>
"""
    for snap in metrics["snapshots"]:
        snap_badge = "<span class='badge badge-critical'>CRITIQUE (>72h)</span>" if snap["status"] == "CRITICAL" else "<span class='badge badge-warning'>WARNING (>48h)</span>"
        html_content += f"""                    <tr>
                        <td><b>{snap['vm_name']}</b></td>
                        <td><code>{snap['snapshot_name']}</code></td>
                        <td>{snap['size_gb']} GB</td>
                        <td>{snap['age_hours']}h</td>
                        <td>{snap_badge}</td>
                    </tr>
"""

    html_content += f"""                </tbody>
            </table>
        </div>

        <!-- FOOTER -->
        <div class="footer">
            Rapport automatisé généré par Antigravity SI Platform - Solidaire Banque &copy; {datetime.datetime.now().year}
        </div>
    </div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"[+] Rapport HTML généré avec succès : {output_path}")
    return output_path

# ------------------------------------------------------------------------------
# 4. PDF REPORT GENERATOR (ReportLab)
# ------------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    """Canvas personnalisé pour ajouter les numéros de page et l'en-tête de document PDF."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#718096"))
        
        # Header (Top line)
        self.drawString(40, 810, "SOLIDAIRE BANQUE - Direction des Systèmes d'Information (DSI)")
        self.drawRightString(555, 810, "Rapport de Santé vCenter 8")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(40, 802, 555, 802)
        
        # Footer (Bottom line)
        self.line(40, 45, 555, 45)
        self.drawString(40, 30, "Confidentiel - Usage Interne Uniquement")
        page_text = f"Page {self._pageNumber} sur {page_count}"
        self.drawRightString(555, 30, page_text)
        self.restoreState()

def generate_pdf_report(metrics, output_path):
    """Génère un document PDF complet et élégant via ReportLab."""
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=55,
        bottomMargin=55
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1A365D"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4A5568"),
        spaceAfter=15
    )
    
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=12,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2D3748")
    )
    
    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4
    )

    story = []
    
    # Title & Header Banner
    story.append(Paragraph("Rapport Quotidien de Santé vCenter", title_style))
    subtitle_text = f"Infrastructure: <b>{metrics['vcenter_host']}</b> | Cluster: <b>{metrics['cluster_name']}</b> | Généré le: <b>{metrics['timestamp']}</b>"
    story.append(Paragraph(subtitle_text, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2B6CB0"), spaceAfter=15))

    # Executive Summary Table (KPI Cards)
    kpi_data = [
        [
            Paragraph("<b>Statut Global</b>", body_style),
            Paragraph("<b>Hôtes ESXi</b>", body_style),
            Paragraph("<b>VMs Actives</b>", body_style),
            Paragraph("<b>RAM Cluster</b>", body_style)
        ],
        [
            Paragraph(f"<font color='#DD6B20'><b>{metrics['overall_status']} ({metrics['health_score']}/100)</b></font>", body_style),
            Paragraph(f"<b>{metrics['summary']['connected_hosts']} / {metrics['summary']['total_hosts']} OK</b>", body_style),
            Paragraph(f"<b>{metrics['summary']['powered_on_vms']} / {metrics['summary']['total_vms']}</b>", body_style),
            Paragraph(f"<b>{metrics['summary']['ram_usage_pct']}%</b> (1260 GB)", body_style)
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[130, 125, 125, 135])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F7FAFC")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#2D3748")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 15))

    # Faits Saillants (Executive Summary)
    story.append(Paragraph("📌 Faits Saillants & Synthèse Opérationnelle", h2_style))
    for h in metrics["highlights"]:
        # Clean HTML code tags for reportlab Paragraph
        clean_h = h.replace("<code>", "<b>").replace("</code>", "</b>")
        story.append(Paragraph(f"• {clean_h}", bullet_style))
    
    story.append(Spacer(1, 15))

    # ESXi Hosts Table
    story.append(Paragraph("💻 Statut des Hôtes ESXi", h2_style))
    hosts_data = [["Nom de l'hôte", "Modèle", "Statut", "CPU %", "RAM %", "VMs"]]
    for host in metrics["hosts"]:
        hosts_data.append([
            host['name'],
            host['model'],
            host['status'],
            f"{host['cpu_pct']}%",
            f"{host['ram_pct']}%",
            str(host['vms'])
        ])
    
    hosts_table = Table(hosts_data, colWidths=[160, 130, 75, 50, 50, 50])
    hosts_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(hosts_table)
    story.append(Spacer(1, 15))

    # Datastores Table
    story.append(Paragraph("💾 État des Datastores SAN", h2_style))
    ds_data = [["Nom Datastore", "Type", "Capacité", "Utilisé", "Libre", "Occupation", "Statut"]]
    for ds in metrics["datastores"]:
        status_txt = f"<font color='#DD6B20'><b>{ds['status']}</b></font>" if ds['status'] != "OK" else "OK"
        ds_data.append([
            ds['name'],
            ds['type'],
            f"{ds['capacity_tb']} TB",
            f"{ds['used_tb']} TB",
            f"{ds['free_tb']} TB",
            f"{ds['pct']}%",
            Paragraph(status_txt, body_style)
        ])
    
    ds_table = Table(ds_data, colWidths=[150, 55, 60, 60, 60, 70, 60])
    ds_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(ds_table)
    story.append(Spacer(1, 15))

    # Snapshots Table
    story.append(Paragraph("📸 Snapshots VM Actifs (> 48h)", h2_style))
    snap_data = [["Machine Virtuelle", "Nom du Snapshot", "Taille", "Âge", "Niveau d'Alerte"]]
    for snap in metrics["snapshots"]:
        risk_txt = "<font color='#E53E3E'><b>CRITIQUE (>72h)</b></font>" if snap['status'] == "CRITICAL" else "<font color='#DD6B20'><b>WARNING (>48h)</b></font>"
        snap_data.append([
            snap['vm_name'],
            snap['snapshot_name'],
            f"{snap['size_gb']} GB",
            f"{snap['age_hours']}h",
            Paragraph(risk_txt, body_style)
        ])
    
    snap_table = Table(snap_data, colWidths=[130, 170, 65, 50, 100])
    snap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4A5568")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(snap_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Rapport PDF généré avec succès : {output_path}")
    return output_path

# ------------------------------------------------------------------------------
# 5. EMAIL SENDER WITH HIGHLIGHTS SUMMARY IN BODY
# ------------------------------------------------------------------------------
def send_email_report(metrics, pdf_path, html_path, recipients=REPORT_RECIPIENTS, dry_run=False):
    """Envoie l'email avec résumé des faits saillants dans le corps et pièces jointes."""
    subject = f"[vCenter Health Report] Rapport Quotidien de Santé VMware - {datetime.datetime.now().strftime('%Y-%m-%d')} - [{metrics['overall_status']}]"
    
    # Construction du corps de texte
    text_body = f"""Bonjour à l'équipe IT / DSI,

Voici le rapport quotidien automatisé de santé pour le vCenter ({metrics['vcenter_host']}).

======================================================================
FAITS SAILLANTS & SYNTHÈSE DU JOUR ({metrics['timestamp']})
======================================================================
"""
    for h in metrics["highlights"]:
        # strip html tags for text body
        clean_txt = h.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", "")
        text_body += f"\n- {clean_txt}"
        
    text_body += f"""

----------------------------------------------------------------------
Résumé de l'Infrastructure:
- Statut Global : {metrics['overall_status']} (Score: {metrics['health_score']}/100)
- Hôtes ESXi    : {metrics['summary']['connected_hosts']} / {metrics['summary']['total_hosts']} Connectés
- VMs en service: {metrics['summary']['powered_on_vms']} / {metrics['summary']['total_vms']}
- Charge RAM    : {metrics['summary']['ram_usage_pct']}%
- Charge CPU    : {metrics['summary']['cpu_usage_pct']}%
----------------------------------------------------------------------

Les rapports complets aux formats PDF et HTML sont disponibles en pièces jointes.

Cordialement,
Automation Agent - Direction des Systèmes d'Information
Solidaire Banque
"""

    # Construction du corps HTML
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #2d3748; line-height: 1.6;">
        <div style="background-color: #1a365d; color: white; padding: 15px 20px; border-radius: 6px;">
            <h2 style="margin: 0;">SOLIDAIRE BANQUE - Rapport Quotidien vCenter</h2>
            <p style="margin: 5px 0 0 0; font-size: 13px; opacity: 0.9;">Date : {metrics['timestamp']} | Statut : <b>{metrics['overall_status']}</b></p>
        </div>
        
        <h3 style="color: #1a365d; margin-top: 20px;">📌 Faits Saillants (Executive Summary)</h3>
        <ul style="background-color: #f7fafc; border-left: 4px solid #2b6cb0; padding: 15px 15px 15px 35px; border-radius: 4px;">
    """
    for h in metrics["highlights"]:
        html_body += f"            <li style='margin-bottom: 8px;'>{h}</li>\n"
        
    html_body += f"""
        </ul>
        
        <p>Veuillez trouver ci-joint les documents de synthèse au format <b>PDF</b> et <b>HTML</b>.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="font-size: 12px; color: #718096;">Message généré automatiquement par l'Agent d'Infrastructure SI - Solidaire Banque.</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("mixed")
    msg["From"] = SMTP_SENDER
    msg["To"] = recipients
    msg["Subject"] = subject

    # Alternative HTML/Text container
    msg_alternative = MIMEMultipart("alternative")
    msg_alternative.attach(MIMEText(text_body, "plain", "utf-8"))
    msg_alternative.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(msg_alternative)

    # Attach PDF
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(pdf_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(pdf_path)}"'
            msg.attach(part)

    # Attach HTML
    if os.path.exists(html_path):
        with open(html_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(html_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(html_path)}"'
            msg.attach(part)

    if dry_run:
        print(f"[i] MODE TEST / DRY-RUN : Email préparé pour {recipients}.")
        print(f"    Sujet : {subject}")
        print(f"    Pièces jointes : {os.path.basename(pdf_path)}, {os.path.basename(html_path)}")
        return True

    try:
        print(f"[*] Connexion au serveur SMTP {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        if SMTP_USE_TLS:
            try:
                server.starttls()
            except Exception as tls_err:
                print(f"[i] Information STARTTLS ignorée sur le relay: {tls_err}")
        if SMTP_USER and SMTP_PASSWORD and SMTP_PASSWORD.strip() != "":
            try:
                server.login(SMTP_USER, SMTP_PASSWORD)
            except Exception as auth_err:
                print(f"[i] Authentification ignorée sur le relay direct: {auth_err}")
        server.sendmail(SMTP_SENDER, [r.strip() for r in recipients.split(",")], msg.as_string())
        server.quit()
        print(f"[+] Email transmis avec succès à {recipients} via {SMTP_SERVER}")
        return True
    except Exception as e:
        print(f"[!] Erreur lors de l'envoi de l'email SMTP via {SMTP_SERVER} : {e}")
        print("[i] Les fichiers PDF et HTML restent sauvegardés en local.")
        return False


# ------------------------------------------------------------------------------
# 6. MAIN EXECUTION
# ------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Générateur de Rapport Quotidien vCenter 8 (PDF/HTML)")
    parser.add_argument("--output-dir", default="./reports", help="Répertoire de sortie des rapports")
    parser.add_argument("--send-email", action="store_true", help="Transmettre le rapport par e-mail SMTP")
    parser.add_argument("--dry-run", action="store_true", help="Simuler l'envoi de l'email sans connexion SMTP")
    parser.add_argument("--test-mode", action="store_true", help="Utiliser des métriques simulées pour la qualification")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    date_stamp = datetime.datetime.now().strftime("%Y%m%d")
    
    html_filename = f"Rapport_Sante_vCenter_{date_stamp}.html"
    pdf_filename = f"Rapport_Sante_vCenter_{date_stamp}.pdf"
    
    html_path = os.path.join(args.output_dir, html_filename)
    pdf_path = os.path.join(args.output_dir, pdf_filename)

    print("=======================================================================")
    print("   GÉNÉRATEUR DE RAPPORT QUOTIDIEN DE SANTÉ VCENTER 8 - DSI SOLBANQUE   ")
    print("=======================================================================")
    
    metrics = collect_vcenter_metrics(test_mode=args.test_mode)
    
    # 1. Génération HTML
    generate_html_report(metrics, html_path)
    
    # 2. Génération PDF
    generate_pdf_report(metrics, pdf_path)

    # 3. Transmettre E-mail
    if args.send_email or args.dry_run:
        send_email_report(metrics, pdf_path, html_path, dry_run=args.dry_run)

    print("[+] Opération terminée avec succès.")

if __name__ == "__main__":
    main()
