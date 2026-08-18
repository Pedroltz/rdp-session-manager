#!/bin/bash
# Script helper para alterar nome completo (GECOS) de usuário RDP
# Uso: pkexec change-user-fullname.sh USERNAME "Full Name"

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 USERNAME \"Full Name\""
    exit 1
fi

USERNAME="$1"
FULLNAME="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/audit-lib.sh"
rdpsm_audit_on_exit user.fullname.change "$USERNAME"

# Verificar se usuário existe
if ! id "$USERNAME" &>/dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

echo "Changing full name for $USERNAME to: $FULLNAME"

# Alterar GECOS (nome completo)
/usr/sbin/usermod -c "$FULLNAME" "$USERNAME"

echo "OK Full name changed successfully"
exit 0
