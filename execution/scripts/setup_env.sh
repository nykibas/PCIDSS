#!/usr/bin/env bash
# Environment Setup Script for Oracle DBA & SysAdmin Tasks
# Usage: source execution/scripts/setup_env.sh

set -euo pipefail

# 1. Load configuration from env files
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")")"

for f in "$PROJECT_ROOT/infra.env" "$PROJECT_ROOT/.env"; do
    if [ -f "$f" ]; then
        echo "Loading environment variables from $f..."
        set -a
        source "$f"
        set +a
    fi
done

# 1.5 Load encrypted secrets securely into memory
if [ -f "$PROJECT_ROOT/.secrets.env.enc" ]; then
    echo "Decrypting and loading secrets from .secrets.env.enc..."
    # Evaluate decrypted stdout without writing to disk
    set -a
    eval "$(python "$PROJECT_ROOT/execution/scripts/decrypt_secrets.py")"
    set +a
fi

# 2. Set default Oracle environment variables if not already set
export ORACLE_SID="${ORACLE_SID:-orcl}"
export ORACLE_BASE="${ORACLE_BASE:-/u01/app/oracle}"
export ORACLE_HOME="${ORACLE_HOME:-/u01/app/oracle/product/19.3.0/dbhome_1}"
export TNS_ADMIN="${TNS_ADMIN:-$ORACLE_HOME/network/admin}"

# 3. Update PATH
if [[ ":$PATH:" != *":$ORACLE_HOME/bin:"* ]]; then
    export PATH="$ORACLE_HOME/bin:$PATH"
fi

# 4. Check Proxy Settings
if [ -n "${http_proxy:-}" ]; then
    echo "Network proxy active: $http_proxy"
else
    echo "No network proxy configured."
fi

echo "Environment initialized for SID: $ORACLE_SID"
