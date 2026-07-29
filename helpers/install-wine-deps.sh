#!/bin/bash
# Helper script to install additional Wine dependencies for a user
# Uso: pkexec helpers/install-wine-deps.sh USERNAME [PACKAGES...]

set -e

USERNAME="$1"
shift  # Remove USERNAME from the arguments

if [ -z "$USERNAME" ]; then
    echo "Error: USERNAME not provided"
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

# Check if the user exists
if ! id "$USERNAME" &>/dev/null; then
    echo "Error: User does not exist: $USERNAME"
    exit 1
fi

HOME_DIR="/opt/rdp-users/$USERNAME"
WINE_PREFIX="$HOME_DIR/.wine"

if [ ! -d "$WINE_PREFIX" ]; then
    echo "Error: Wine Prefix not found for $USERNAME"
    echo "  Expected at: $WINE_PREFIX"
    exit 1
fi

# If no packages were passed, install default set
if [ $# -eq 0 ]; then
    echo "No packages specified. Installing default set..."
    PACKAGES="corefonts vcrun2015 msxml3 d3dx9"
else
    PACKAGES="$@"
fi

echo "Installing Wine dependencies for: $USERNAME"
echo "  - Wine Prefix: $WINE_PREFIX"
echo " - Packets: $PACKAGES"
echo ""
echo "WARNING ATTENTION: This may take a few minutes..."
echo ""

# Install each package
for PACKAGE in $PACKAGES; do
    echo "→ Installing $PACKAGE..."
    su - "$USERNAME" -c "WINEPREFIX='$WINE_PREFIX' winetricks -q $PACKAGE" || {
        echo "WARNING Failed to install $PACKAGE (continuing...)"
    }
    echo "  OK $PACKAGE instalado"
done

echo ""
echo "OK Wine dependencies installed successfully!"
echo ""
echo "User $USERNAME can log in via RDP to test."

exit 0
