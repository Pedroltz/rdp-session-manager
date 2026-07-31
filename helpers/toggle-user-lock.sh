#!/bin/bash
# Helper script para habilitar/desabilitar usuário RDP com pkexec
# Uso: pkexec helpers/toggle-user-lock.sh USERNAME lock|unlock

set -e

USERNAME="$1"
ACTION="$2"

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
    echo "OK User $USERNAME disabled (account locked)"
else
    echo "Enabling user $USERNAME..."
    /usr/sbin/usermod --unlock "$USERNAME"
    echo "OK User $USERNAME enabled (account unlocked)"
fi

exit 0
