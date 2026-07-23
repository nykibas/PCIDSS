#!/usr/bin/env bash
# ==============================================================================
# Script : run_vcenter_daily_report.sh
# Description : Wrapper d'exécution quotidienne du rapport de santé vCenter 8.
# Conforme aux normes RHEL SysAdmin Solidaire Banque (set -euo pipefail).
# ==============================================================================

set -euo pipefail

# 1. Définition des chemins du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Fichier de log et sous-dossier de rapports
LOG_DIR="${PROJECT_ROOT}/logs"
REPORT_DIR="${PROJECT_ROOT}/reports"

mkdir -p "${LOG_DIR}" "${REPORT_DIR}"

LOG_FILE="${LOG_DIR}/vcenter_health_automation.log"

exec 3>&1 4>&2
exec 1>>"${LOG_FILE}" 2>&1

echo "======================================================================="
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Lancement de l'automatisation du rapport vCenter"
echo "======================================================================="

# 2. Chargement de l'environnement
if [ -f "${SCRIPT_DIR}/setup_env.sh" ]; then
    # Source sans interruption si possible
    source "${SCRIPT_DIR}/setup_env.sh" || true
fi

# 3. Détermination des flags d'exécution
TEST_FLAG=""
DRY_RUN_FLAG=""

if [[ "${1:-}" == "--test" ]]; then
    echo "[i] Mode qualification / test activé"
    TEST_FLAG="--test-mode"
    DRY_RUN_FLAG="--dry-run"
elif [[ "${1:-}" == "--send" ]]; then
    DRY_RUN_FLAG="--send-email"
else
    # Par défaut, dry-run sécurisé si exécuté en sandbox sans argument
    DRY_RUN_FLAG="--dry-run"
fi

# 4. Exécution du script Python
PYTHON_BIN="python"
if [ -f "/c/Users/ynzau/AppData/Local/Programs/Python/Python312/python.exe" ]; then
    PYTHON_BIN="/c/Users/ynzau/AppData/Local/Programs/Python/Python312/python.exe"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
fi

echo "[*] Exécution du script Python de génération des rapports via ${PYTHON_BIN}..."
"${PYTHON_BIN}" "${SCRIPT_DIR}/generate_vcenter_health_report.py" \
    --output-dir "${REPORT_DIR}" \
    ${TEST_FLAG} \
    --dry-run # Ne pas envoyer via le script Python

# 4.5. Envoi du mail via le système (RHEL / mailx)
# Décommentez et adaptez cette section pour utiliser la même commande que votre script Oracle
# DATE_STR=$(date '+%Y%m%d')
# REPORT_PDF="${REPORT_DIR}/Rapport_Sante_vCenter_${DATE_STR}.pdf"
# REPORT_HTML="${REPORT_DIR}/Rapport_Sante_vCenter_${DATE_STR}.html"
# if [ -f "$REPORT_PDF" ]; then
#     echo "[*] Envoi de l'e-mail via mailx (Configuration RHEL native)..."
#     echo "Veuillez trouver ci-joint le rapport de santé quotidien vCenter (PDF & HTML)." | \
#     mailx -s "Rapport Quotidien de Santé vCenter" \
#           -a "$REPORT_PDF" -a "$REPORT_HTML" \
#           -S from="monitoring@solidairebanque.com" \
#           DSI@solidairebanque.com
# fi

# 5. Purge des anciens rapports (> 30 jours)
echo "[*] Nettoyage des rapports de plus de 30 jours..."
find "${REPORT_DIR}" -type f \( -name "*.pdf" -o -name "*.html" \) -mtime +30 -exec rm -f {} + 2>/dev/null || true

echo "[+] Rapport quotidien terminé avec succès le $(date '+%Y-%m-%d %H:%M:%S')"
echo "-----------------------------------------------------------------------"
