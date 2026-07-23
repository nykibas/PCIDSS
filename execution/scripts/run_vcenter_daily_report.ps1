# ==============================================================================
# Script : run_vcenter_daily_report.ps1
# Description : Wrapper PowerShell d'exécution quotidienne du rapport vCenter sur Windows.
# ==============================================================================

$ErrorActionPreference = "Stop"

# 1. Définition des chemins du projet
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Resolve-Path "$ScriptDir\..\.."
$LogDir = Join-Path $ProjectRoot "logs"
$ReportDir = Join-Path $ProjectRoot "reports"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir | Out-Null }

$LogFile = Join-Path $LogDir "vcenter_health_automation.log"

# Fonction d'écriture de log horodaté
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $FormattedMessage = "[$Timestamp] $Message"
    Write-Host $FormattedMessage
    Add-Content -Path $LogFile -Value $FormattedMessage
}

Write-Log "======================================================================="
Write-Log "Lancement de l'automatisation du rapport vCenter (Windows PowerShell)"
Write-Log "======================================================================="

# 2. Recherche de l'exécutable Python
$PythonBin = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonBin) {
    $PythonBin = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
}

if (-not (Test-Path $PythonBin)) {
    Write-Log "[!] ERREUR: Python est introuvable. Veuillez vérifier l'installation de Python."
    exit 1
}

# 3. Traitement des arguments
$ScriptArgs = @("--output-dir", $ReportDir)

if ($args -contains "--test") {
    Write-Log "[i] Mode qualification / test activé"
    $ScriptArgs += "--test-mode"
    $ScriptArgs += "--dry-run"
} elseif ($args -contains "--send") {
    $ScriptArgs += "--send-email"
} else {
    $ScriptArgs += "--dry-run"
}

# 4. Exécution du script Python
Write-Log "[*] Exécution du script Python via $PythonBin..."
$PythonScript = Join-Path $ScriptDir "generate_vcenter_health_report.py"

& $PythonBin $PythonScript @ScriptArgs 2>&1 | ForEach-Object { Write-Log $_ }

# 5. Purge des anciens rapports (> 30 jours)
Write-Log "[*] Nettoyage des rapports de plus de 30 jours..."
$LimitDate = (Get-Date).AddDays(-30)
Get-ChildItem -Path $ReportDir -File | Where-Object { 
    ($_.Extension -eq ".pdf" -or $_.Extension -eq ".html") -and ($_.LastWriteTime -lt $LimitDate) 
} | Remove-Item -Force

Write-Log "[+] Rapport quotidien terminé avec succès."
