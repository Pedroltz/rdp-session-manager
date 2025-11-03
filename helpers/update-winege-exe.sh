#!/bin/bash
set -e

USERNAME="$1"
NEW_EXE_PATH="$2"

[ -z "$USERNAME" ] || [ -z "$NEW_EXE_PATH" ] && {
    echo "Uso: $0 USERNAME NEW_EXE_PATH"
    exit 1
}

id "$USERNAME" &>/dev/null || {
    echo "Erro: Usuário não existe: $USERNAME"
    exit 1
}

[ ! -f "$NEW_EXE_PATH" ] && {
    echo "Erro: Arquivo não encontrado: $NEW_EXE_PATH"
    exit 1
}

HOME_DIR="/opt/rdp-users/$USERNAME"
WINEGE_APP_PATH="$HOME_DIR/.winege_app_path"

[ ! -f "$WINEGE_APP_PATH" ] && {
    echo "Erro: Usuário $USERNAME não é WineGE RemoteApp"
    exit 1
}

echo "Atualizando executável WineGE para: $USERNAME"
echo "  Novo executável: $NEW_EXE_PATH"

# Salvar novo caminho (SEM copiar)
echo "$NEW_EXE_PATH" > "$WINEGE_APP_PATH"
chown "$USERNAME:rdp-users" "$WINEGE_APP_PATH"

echo "OK Executável atualizado com sucesso!"
echo "Executável será executado de: $NEW_EXE_PATH"
exit 0
