#!/bin/bash
# Helper script para conceder/revogar privilégios sudo para usuário RDP com pkexec
# Uso: pkexec helpers/toggle-user-sudo.sh USERNAME grant|revoke

set -e

USERNAME="$1"
ACTION="$2"

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$ACTION" ]; then
    echo "Erro: Parâmetros insuficientes"
    echo "Uso: $0 USERNAME grant|revoke"
    exit 1
fi

# Validar ação
if [ "$ACTION" != "grant" ] && [ "$ACTION" != "revoke" ]; then
    echo "Erro: Ação inválida. Use 'grant' ou 'revoke'"
    exit 1
fi

# Verificar se usuário existe
if ! /usr/bin/id "$USERNAME" &> /dev/null; then
    echo "Erro: Usuário $USERNAME não existe"
    exit 1
fi

if [ "$ACTION" = "grant" ]; then
    echo "Concedendo privilégios de superusuário para $USERNAME..."

    # Adicionar usuário ao grupo sudo
    /usr/sbin/usermod -aG sudo "$USERNAME"

    echo "✓ Privilégios de superusuário concedidos para $USERNAME"
    echo "  O usuário agora pode executar comandos com sudo"
else
    echo "Revogando privilégios de superusuário de $USERNAME..."

    # Remover usuário do grupo sudo usando gpasswd (mais confiável)
    if /usr/bin/gpasswd -d "$USERNAME" sudo 2>/dev/null; then
        echo "✓ Privilégios de superusuário revogados de $USERNAME"
        echo "  O usuário não pode mais executar comandos com sudo"
    else
        # Fallback para deluser se gpasswd falhar
        if /usr/sbin/deluser "$USERNAME" sudo 2>/dev/null; then
            echo "✓ Privilégios de superusuário revogados de $USERNAME"
            echo "  O usuário não pode mais executar comandos com sudo"
        else
            echo "! Aviso: Comando completado mas verifique os grupos do usuário"
        fi
    fi
fi

exit 0