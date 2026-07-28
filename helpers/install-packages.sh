#!/bin/bash
# Helper script para instalar pacotes com pkexec
# Uso: pkexec helpers/install-packages.sh package1 package2 package3...

set -e

# Detectar distribuição
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)

# Verificar se há pacotes para instalar
if [ $# -eq 0 ]; then
    echo "Erro: Nenhum pacote especificado"
    exit 1
fi

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        # Atualizar cache de pacotes
        echo "Atualizando cache de pacotes..."
        # Avoid partial upgrades: Arch requires a full sync before installing.
        /usr/bin/pacman -Syu --needed --noconfirm

        # Instalar pacotes
        echo "Instalando pacotes: $@"
        /usr/bin/pacman -S --noconfirm "$@"
        ;;
    debian|ubuntu|linuxmint|pop)
        # Atualizar cache de pacotes
        echo "Atualizando cache de pacotes..."
        /usr/bin/apt-get update

        # Instalar pacotes
        echo "Instalando pacotes: $@"
        DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install -y "$@"
        ;;
    *)
        echo "Erro: Distribuição não suportada: $DISTRO"
        exit 1
        ;;
esac

echo "Instalação concluída com sucesso!"
exit 0
