#!/bin/bash
# Helper script para definir senha de usuário com pkexec
# Uso: echo "username:password" | pkexec helpers/set-user-password.sh

set -e

# Ler credenciais do stdin
read -r CREDENTIALS

if [ -z "$CREDENTIALS" ]; then
    echo "Error: Credentials were not provided through stdin"
    exit 1
fi

USERNAME="${CREDENTIALS%%:*}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/audit-lib.sh"
rdpsm_audit_on_exit user.password.change "$USERNAME"

# Definir senha usando chpasswd
echo "$CREDENTIALS" | /usr/sbin/chpasswd

echo "OK Password set successfully!"
exit 0
