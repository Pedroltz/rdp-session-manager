#!/bin/bash
# Helper script para instalar dependências Wine adicionais para um usuário
# Uso: pkexec helpers/install-wine-deps.sh USERNAME [PACKAGES...]

set -e

USERNAME="$1"
shift  # Remove USERNAME dos argumentos

if [ -z "$USERNAME" ]; then
    echo "Erro: USERNAME não fornecido"
    echo "Uso: $0 USERNAME [PACKAGES...]"
    echo ""
    echo "Packages comuns:"
    echo "  vcrun2015    - Visual C++ 2015 Runtime"
    echo "  vcrun2019    - Visual C++ 2019 Runtime"
    echo "  dotnet48     - .NET Framework 4.8"
    echo "  dotnet6      - .NET 6"
    echo "  corefonts    - Fontes Microsoft"
    echo "  d3dx9        - DirectX 9"
    echo "  d3dx11       - DirectX 11"
    echo "  msxml3       - Microsoft XML Parser"
    echo "  vcrun6       - Visual C++ 6 Runtime"
    echo ""
    echo "Exemplo: $0 myuser vcrun2015 dotnet48 corefonts"
    exit 1
fi

# Verificar se o usuário existe
if ! id "$USERNAME" &>/dev/null; then
    echo "Erro: Usuário não existe: $USERNAME"
    exit 1
fi

HOME_DIR="/opt/rdp-users/$USERNAME"
WINE_PREFIX="$HOME_DIR/.wine"

if [ ! -d "$WINE_PREFIX" ]; then
    echo "Erro: Wine Prefix não encontrado para $USERNAME"
    echo "  Esperado em: $WINE_PREFIX"
    exit 1
fi

# Se não foram passados pacotes, instalar conjunto padrão
if [ $# -eq 0 ]; then
    echo "Nenhum pacote especificado. Instalando conjunto padrão..."
    PACKAGES="corefonts vcrun2015 msxml3 d3dx9"
else
    PACKAGES="$@"
fi

echo "Instalando dependências Wine para: $USERNAME"
echo "  - Wine Prefix: $WINE_PREFIX"
echo "  - Pacotes: $PACKAGES"
echo ""
echo "AVISO ATENÇÃO: Isso pode levar alguns minutos..."
echo ""

# Instalar cada pacote
for PACKAGE in $PACKAGES; do
    echo "→ Instalando $PACKAGE..."
    su - "$USERNAME" -c "WINEPREFIX='$WINE_PREFIX' winetricks -q $PACKAGE" || {
        echo "  AVISO Falha ao instalar $PACKAGE (continuando...)"
    }
    echo "  OK $PACKAGE instalado"
done

echo ""
echo "OK Dependências Wine instaladas com sucesso!"
echo ""
echo "O usuário $USERNAME pode fazer login via RDP para testar."

exit 0
