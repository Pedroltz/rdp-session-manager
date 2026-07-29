#!/bin/bash
# Helper script para conceder/revogar privilégios sudo para usuário RDP com pkexec
# Uso: pkexec helpers/toggle-user-sudo.sh USERNAME grant|revoke

set -e

USERNAME="$1"
ACTION="$2"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Error: Not enough arguments"
    echo "Usage: $0 USERNAME grant|revoke"
    exit 1
fi

# Validar ação
if [ "$ACTION" != "grant" ] && [ "$ACTION" != "revoke" ]; then
    echo "Error: Invalid action. Use 'grant' or 'revoke'"
    exit 1
fi

# Verificar se usuário existe
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Error: User $USERNAME does not exist"
    exit 1
fi

if [ "$ACTION" = "grant" ]; then
    echo "Granting superuser privileges to $USERNAME..."

    # Adicionar usuário ao grupo sudo
    /usr/sbin/usermod -aG sudo "$USERNAME"

    echo "OK Superuser privileges granted to $USERNAME"
    echo "  The user can now run commands with sudo"
else
    echo "Revoking superuser privileges from $USERNAME..."

    # Remover usuário do grupo sudo usando gpasswd (mais confiável)
    if /usr/bin/gpasswd -d "$USERNAME" sudo 2>/dev/null; then
        echo "OK Superuser privileges revoked from $USERNAME"
        echo "  The user can no longer run commands with sudo"
    else
        # Fallback para deluser se gpasswd falhar
        if /usr/sbin/deluser "$USERNAME" sudo 2>/dev/null; then
        echo "OK Superuser privileges revoked from $USERNAME"
        echo "  The user can no longer run commands with sudo"
        else
        echo "! Warning: Command completed, but check the user's groups"
        fi
    fi
fi

exit 0
