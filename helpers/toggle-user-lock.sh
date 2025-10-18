#!/bin/bash
# Helper script para habilitar/desabilitar usuário RDP com pkexec
# Uso: pkexec helpers/toggle-user-lock.sh USERNAME lock|unlock

set -e

USERNAME="$1"
ACTION="$2"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Erro: Parâmetros insuficientes"
    echo "Uso: $0 USERNAME lock|unlock"
    exit 1
fi

# Validar ação
if [ "$ACTION" != "lock" ] && [ "$ACTION" != "unlock" ]; then
    echo "Erro: Ação inválida. Use 'lock' ou 'unlock'"
    exit 1
fi

# Verificar se usuário existe
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Erro: Usuário $USERNAME não existe"
    exit 1
fi

if [ "$ACTION" = "lock" ]; then
    echo "Desabilitando usuário $USERNAME..."
    /usr/sbin/usermod --lock "$USERNAME"
    echo "✓ Usuário $USERNAME desabilitado (conta bloqueada)"
else
    echo "Habilitando usuário $USERNAME..."
    /usr/sbin/usermod --unlock "$USERNAME"
    echo "✓ Usuário $USERNAME habilitado (conta desbloqueada)"
fi

exit 0
