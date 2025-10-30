#!/bin/bash
# Script helper para alterar nome completo (GECOS) de usuário RDP
# Uso: pkexec change-user-fullname.sh USERNAME "Full Name"

set -e

if [ "$#" -ne 2 ]; then
    echo "Uso: $0 USERNAME \"Full Name\""
    exit 1
fi

USERNAME="$1"
FULLNAME="$2"

# Verificar se usuário existe
if ! id "$USERNAME" &>/dev/null; then
    echo "Erro: Usuário $USERNAME não existe"
    exit 1
fi

echo "Alterando nome completo de $USERNAME para: $FULLNAME"

# Alterar GECOS (nome completo)
/usr/sbin/usermod -c "$FULLNAME" "$USERNAME"

echo "✓ Nome completo alterado com sucesso"
exit 0
