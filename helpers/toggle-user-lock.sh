#!/bin/bash
# Helper script para habilitar/desabilitar usuário RDP com pkexec
# Uso: pkexec helpers/toggle-user-lock.sh USERNAME lock|unlock

set -e

USERNAME="$1"
ACTION="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/audit-lib.sh"
rdpsm_audit_on_exit "user.$ACTION" "$USERNAME"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Error: Not enough arguments"
    echo "Usage: $0 USERNAME lock|unlock"
    exit 1
fi

# Validar ação
if [ "$ACTION" != "lock" ] && [ "$ACTION" != "unlock" ]; then
    echo "Error: Invalid action. Use 'lock' or 'unlock'"
    exit 1
fi

# Verificar se usuário existe
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

if [ "$ACTION" = "lock" ]; then
    echo "Disabling user $USERNAME..."
    /usr/sbin/usermod --lock "$USERNAME"

    # Terminar sessões ativas do loginctl/systemd se disponível
    if command -v loginctl >/dev/null 2>&1; then
        loginctl terminate-user "$USERNAME" 2>/dev/null || true
    fi

    # Encerrar processos ativos do usuário
    if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
        echo "  Terminating active processes for $USERNAME..."
        /usr/bin/pkill -15 -u "$USERNAME" 2>/dev/null || true
        sleep 1
        if /usr/bin/pgrep -u "$USERNAME" > /dev/null 2>&1; then
            /usr/bin/pkill -9 -u "$USERNAME" 2>/dev/null || true
        fi
    fi

    echo "OK User $USERNAME disabled (account locked and sessions terminated)"
else
    echo "Enabling user $USERNAME..."
    /usr/sbin/usermod --unlock "$USERNAME"
    echo "OK User $USERNAME enabled (account unlocked)"
fi

exit 0
