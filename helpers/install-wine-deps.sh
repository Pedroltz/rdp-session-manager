#!/bin/bash
# Helper script para instalar dependências Wine adicionais para um usuário
# Uso: pkexec helpers/install-wine-deps.sh USERNAME [PACKAGES...]

set -e

USERNAME="$1"
shift  # Remove USERNAME dos argumentos

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/audit-lib.sh"
rdpsm_audit_on_exit windows.dependencies.install "$USERNAME"

if [ -z "$USERNAME" ]; then
    echo "Error: USERNAME was not provided"
    echo "Usage: $0 USERNAME [PACKAGES...]"
    echo ""
    echo "Common packages:"
    echo "  vcrun2015    - Visual C++ 2015 Runtime"
    echo "  vcrun2019    - Visual C++ 2019 Runtime"
    echo "  dotnet48     - .NET Framework 4.8"
    echo "  dotnet6      - .NET 6"
    echo "  corefonts    - Microsoft fonts"
    echo "  d3dx9        - DirectX 9"
    echo "  d3dx11       - DirectX 11"
    echo "  msxml3       - Microsoft XML Parser"
    echo "  vcrun6       - Visual C++ 6 Runtime"
    echo ""
    echo "Example: $0 myuser vcrun2015 dotnet48 corefonts"
    exit 1
fi

# Verificar se o usuário existe
if ! id "$USERNAME" &>/dev/null; then
    echo "Error: User does not exist: $USERNAME"
    exit 1
fi

HOME_DIR="/opt/rdp-users/$USERNAME"
WINE_PREFIX="$HOME_DIR/.wine"

if [ ! -d "$WINE_PREFIX" ]; then
    echo "Error: Wine prefix not found for $USERNAME"
    echo "  Expected at: $WINE_PREFIX"
    exit 1
fi

# Se não foram passados pacotes, instalar conjunto padrão
if [ $# -eq 0 ]; then
    echo "No package specified. Installing the default set..."
    PACKAGES="corefonts vcrun2015 msxml3 d3dx9"
else
    PACKAGES="$@"
fi

echo "Installing Wine dependencies for: $USERNAME"
echo "  - Wine Prefix: $WINE_PREFIX"
echo "  - Packages: $PACKAGES"
echo ""
echo "WARNING: This may take a few minutes..."
echo ""

# Instalar cada pacote
for PACKAGE in $PACKAGES; do
    echo "→ Installing $PACKAGE..."
    su - "$USERNAME" -c "WINEPREFIX='$WINE_PREFIX' winetricks -q $PACKAGE" || {
        echo "  WARNING Failed to install $PACKAGE (continuing...)"
    }
    echo "  OK $PACKAGE installed"
done

echo ""
echo "OK Wine dependencies installed successfully!"
echo ""
echo "User $USERNAME can now log in through RDP for testing."

exit 0
