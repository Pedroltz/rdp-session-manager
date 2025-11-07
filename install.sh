#!/bin/bash
###############################################################################
# Install RDP Session Manager
###############################################################################

set -e

DEB_FILE="release/rdp-session-manager_0.3.0_all.deb"

echo "========================================="
echo "  Installing RDP Session Manager"
echo "========================================="
echo ""

# Check package
if [ ! -f "$DEB_FILE" ]; then
    echo "ERROR: Package not found: $DEB_FILE"
    echo "Run ./build_release.sh first"
    exit 1
fi

# Install dependencies
echo "→ Installing dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-adw-1 \
    libadwaita-1-0 \
    polkitd \
    python3-psutil \
    wget \
    tar \
    cabextract \
    zenity \
    openbox

# Optional: Install Wine for WineGE RemoteApp support
echo ""
echo "→ Installing Wine and dependencies (for WineGE RemoteApp support)..."
echo "  This is required if you want to run Windows applications via WineGE."
echo ""

# Enable 32-bit architecture for Wine
sudo dpkg --add-architecture i386
sudo apt-get update

# Install Wine and essential dependencies
echo "  → Installing Wine packages..."
sudo apt-get install -y \
    wine \
    wine64 \
    wine32 \
    winetricks \
    cabextract \
    p7zip-full \
    unzip \
    curl \
    libfreetype6:i386 \
    libfontconfig1:i386 \
    libxrender1:i386 \
    libxinerama1:i386 \
    libxxf86vm1:i386 \
    libxcomposite1:i386 \
    libxrandr2:i386 \
    libxi6:i386 \
    libxcursor1:i386 \
    libvulkan1:i386 \
    mesa-vulkan-drivers:i386 \
    libgl1:i386 \
    libasound2:i386 \
    libpulse0:i386 \
    libgnutls30:i386 \
    libgstreamer1.0-0:i386 \
    libgstreamer-plugins-base1.0-0:i386 || {
    echo "⚠ Warning: Failed to install some Wine dependencies."
    echo "  WineGE RemoteApp may not work properly."
    echo "  You can install it manually later with: sudo apt install wine wine64 winetricks"
}

echo "  ✓ Wine dependencies installed"

# Optional: Install Oracle Instant Client for database connectivity
echo ""
echo "→ Installing Oracle Instant Client (for Oracle Database connectivity)..."
echo "  This is required if you want to run applications that connect to Oracle databases."
echo ""

# Install dependencies for Oracle Instant Client
echo "  → Installing Oracle dependencies..."
sudo apt-get install -y \
    libaio1 \
    libaio-dev \
    unixodbc \
    unixodbc-dev \
    alien \
    wget || {
    echo "⚠ Warning: Failed to install some Oracle dependencies."
    echo "  Oracle database connectivity may not work properly."
    echo "  You can install it manually later with: sudo apt install libaio1 unixodbc"
}

# Download and install Oracle Instant Client
ORACLE_VERSION="21.15.0.0.0"
ORACLE_MAJOR="2115000"
ORACLE_DIR="/opt/oracle"
ORACLE_CLIENT_DIR="$ORACLE_DIR/instantclient_21_15"

if [ ! -d "$ORACLE_CLIENT_DIR" ]; then
    echo "  → Downloading Oracle Instant Client..."
    echo "    Note: This requires accepting Oracle's license agreement."
    echo "    Download manually from: https://www.oracle.com/database/technologies/instant-client/downloads.html"
    echo "    Place the following files in /tmp/:"
    echo "      - oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm"
    echo "      - oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm"
    echo ""

    if [ -f "/tmp/oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm" ] && \
       [ -f "/tmp/oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm" ]; then

        echo "  → Found Oracle Instant Client RPMs, converting to DEB..."
        cd /tmp
        sudo alien -i oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm
        sudo alien -i oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm

        # Create symlinks
        sudo mkdir -p "$ORACLE_DIR"
        if [ -d "/usr/lib/oracle/${ORACLE_MAJOR}/client64" ]; then
            sudo ln -sf "/usr/lib/oracle/${ORACLE_MAJOR}/client64" "$ORACLE_CLIENT_DIR"
        fi

        # Configure environment
        echo "  → Configuring Oracle environment..."
        cat | sudo tee /etc/profile.d/oracle.sh > /dev/null <<EOF
export ORACLE_HOME=$ORACLE_CLIENT_DIR
export LD_LIBRARY_PATH=\$ORACLE_HOME/lib:\$LD_LIBRARY_PATH
export PATH=\$ORACLE_HOME/bin:\$PATH
export TNS_ADMIN=\$ORACLE_HOME/network/admin
EOF

        # Create tnsnames.ora directory
        sudo mkdir -p "$ORACLE_CLIENT_DIR/network/admin"

        # Create sample tnsnames.ora
        cat | sudo tee "$ORACLE_CLIENT_DIR/network/admin/tnsnames.ora" > /dev/null <<EOF
# Sample TNS Names Configuration
# Uncomment and configure your Oracle database connections below:
#
# MYDB =
#   (DESCRIPTION =
#     (ADDRESS = (PROTOCOL = TCP)(HOST = hostname)(PORT = 1521))
#     (CONNECT_DATA =
#       (SERVER = DEDICATED)
#       (SERVICE_NAME = service_name)
#     )
#   )
EOF

        echo "  ✓ Oracle Instant Client installed"
        echo "  → Edit $ORACLE_CLIENT_DIR/network/admin/tnsnames.ora to configure connections"
    else
        echo "  ⚠ Oracle Instant Client RPMs not found in /tmp/"
        echo "    Skipping Oracle installation."
        echo "    To install later:"
        echo "    1. Download RPMs from Oracle website"
        echo "    2. Place in /tmp/"
        echo "    3. Run: sudo alien -i oracle-instantclient-*.rpm"
    fi
else
    echo "  ✓ Oracle Instant Client already installed"
fi

echo ""
echo "→ Installing package..."
sudo dpkg -i "$DEB_FILE"
sudo apt-get install -f -y

echo ""
echo "→ Configuring system..."

# Criar link simbólico /opt/rdp-user -> /opt/rdp-users
# (Alguns aplicativos Wine procuram caminhos sem o 's' final)
if [ ! -e /opt/rdp-user ]; then
    sudo ln -s /opt/rdp-users /opt/rdp-user
    echo "  ✓ Created symlink /opt/rdp-user -> /opt/rdp-users"
else
    echo "  ✓ Symlink /opt/rdp-user already exists"
fi

echo ""
echo "✓ Installation complete!"
echo ""
echo "Run: rdp-session-manager"
