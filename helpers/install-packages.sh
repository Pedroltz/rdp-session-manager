#!/bin/bash
# Helper script para instalar pacotes com pkexec
# Uso: pkexec helpers/install-packages.sh package1 package2 package3...

set -e

# Verificar se há pacotes para instalar
if [ $# -eq 0 ]; then
    echo "Erro: Nenhum pacote especificado"
    exit 1
fi

# Atualizar cache de pacotes
echo "Atualizando cache de pacotes..."
/usr/bin/apt-get update

# Instalar pacotes
echo "Instalando pacotes: $@"
DEBIAN_FRONTEND=noninteractive /usr/bin/apt-get install -y "$@"

echo "Instalação concluída com sucesso!"
exit 0
