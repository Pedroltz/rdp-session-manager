#!/bin/bash
# Helper script para definir senha de usuário com pkexec
# Uso: echo "username:password" | pkexec helpers/set-user-password.sh

set -e

# Ler credenciais do stdin
read -r CREDENTIALS

if [ -z "$CREDENTIALS" ]; then
    echo "Erro: Credenciais não fornecidas via stdin"
    exit 1
fi

# Definir senha usando chpasswd
echo "$CREDENTIALS" | /usr/sbin/chpasswd

echo "✓ Senha definida com sucesso!"
exit 0
