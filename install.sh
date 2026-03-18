#!/bin/bash
###############################################################################
# Install RDP Session Manager
###############################################################################
set -e

# Detect distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
SCRIPT_VERSION="0.3.0"

echo "========================================="
echo "  Installing RDP Session Manager"
echo "========================================="
echo "Detected distribution: $DISTRO"
echo "Script version: $SCRIPT_VERSION"
echo ""

# Exporta para evitar travamento em prompts interativos (debconf, tzdata, etc.)
export DEBIAN_FRONTEND=noninteractive

# Check package based on distro
case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        PKG_FILE="release/rdp-session-manager-0.3.0-1-any.pkg.tar.zst"
        ;;
    debian|ubuntu|linuxmint|pop)
        PKG_FILE="release/rdp-session-manager_0.3.0_all.deb"
        ;;
    *)
        echo "ERROR: Unsupported distribution: $DISTRO"
        echo "Supported: Arch Linux (CachyOS, Manjaro, EndeavourOS), Debian, Ubuntu"
        exit 1
        ;;
esac

if [ ! -f "$PKG_FILE" ]; then
    echo "ERROR: Package not found: $PKG_FILE"
    echo "Run ./build_release.sh first"
    exit 1
fi

# =========================================
#   1/5 - Core System Dependencies
# =========================================
echo "========================================="
echo "  1/5 - Core System Dependencies"
echo "========================================="
echo "These packages are required for the application to run."

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        echo "→ Installing Python and GTK4 dependencies..."
        sudo pacman -Sy --noconfirm \
            python python-gobject python-cairo gtk4 libadwaita polkit python-psutil \
            wget tar cabextract zenity openbox
        ;;
    debian|ubuntu|linuxmint|pop)
        echo "→ Updating package cache..."
        sudo apt-get update -qq

        echo "→ Installing Python and GTK4 dependencies..."
        sudo apt-get install -y \
            python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
            libadwaita-1-0 polkitd python3-psutil wget tar cabextract zenity openbox
        ;;
esac

# =========================================
#   2/5 - RDP Server Dependencies
# =========================================
echo ""
echo "========================================="
echo "  2/5 - RDP Server Dependencies"
echo "========================================="
echo "These packages enable RDP connections to this machine."

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        echo "→ Installing xrdp and X11 packages..."
        sudo pacman -S --noconfirm xrdp xorgxrdp
        ;;
    debian|ubuntu|linuxmint|pop)
        echo "→ Installing xrdp and X11 packages..."
        sudo apt-get install -y \
            xrdp xorgxrdp \
            xserver-xorg-core \
            dbus-x11 \
            x11-xserver-utils \
            xauth
        sudo systemctl enable xrdp
        sudo systemctl start xrdp || true
        echo "  ✓ xrdp installed and started"
        ;;
esac

# =========================================
#   3/5 - Wine (WineGE RemoteApp support)
# =========================================
echo ""
echo "========================================="
echo "  3/5 - Wine (WineGE RemoteApp support)"
echo "========================================="
echo "Required to run Windows applications via WineGE."

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        if ! grep -q "^\[multilib\]" /etc/pacman.conf; then
            echo "→ Enabling multilib repository..."
            echo "[multilib]" | sudo tee -a /etc/pacman.conf
            echo "Include = /etc/pacman.d/mirrorlist" | sudo tee -a /etc/pacman.conf
            sudo pacman -Sy
        fi
        sudo pacman -S --noconfirm \
            wine wine-mono wine-gecko winetricks lib32-gnutls lib32-libxinerama \
            lib32-libldap lib32-mpg123 lib32-libpulse lib32-alsa-plugins lib32-alsa-lib \
            lib32-libjpeg-turbo lib32-libxcomposite lib32-libxslt lib32-gst-plugins-base-libs \
            lib32-gst-plugins-good lib32-vulkan-icd-loader lib32-mesa cabextract p7zip unzip curl \
            || echo "⚠ Warning: Some Wine packages failed (install manually later if needed)"
        ;;

    debian|ubuntu|linuxmint|pop)
        sudo dpkg --add-architecture i386
        sudo apt-get update -qq

        sudo apt-get install -y wine wine64 wine32 cabextract p7zip-full unzip curl || true

        echo "→ Installing latest winetricks from upstream..."
        sudo wget -q https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks \
            -O /usr/local/bin/winetricks
        sudo chmod +x /usr/local/bin/winetricks

        sudo apt-get install -y \
            libfreetype6:i386 libfontconfig1:i386 libxrender1:i386 libxinerama1:i386 \
            libxxf86vm1:i386 libxcomposite1:i386 libxrandr2:i386 libxi6:i386 libxcursor1:i386 \
            libvulkan1:i386 mesa-vulkan-drivers:i386 libgl1:i386 libasound2:i386 libpulse0:i386 \
            libgnutls30:i386 libgstreamer1.0-0:i386 libgstreamer-plugins-base1.0-0:i386 || true
        ;;
esac

echo "  ✓ Wine + winetricks installed"

# =========================================
#   4/5 - Oracle Instant Client (opcional)
# =========================================
echo ""
echo "========================================="
echo "  4/5 - Oracle Instant Client (optional)"
echo "========================================="
echo "Required only for applications that connect to Oracle databases."

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        sudo pacman -S --noconfirm libaio unixodbc wget || true
        echo "  ⚠ On Arch: install oracle-instantclient from AUR if needed"
        ;;

    debian|ubuntu|linuxmint|pop)
        sudo apt-get install -y libaio-dev unixodbc unixodbc-dev alien wget || true
        sudo apt-get install -y libaio1 2>/dev/null || \
        sudo apt-get install -y libaio1t64 2>/dev/null || true

        ORACLE_VERSION="21.15.0.0.0"
        ORACLE_MAJOR="2115000"
        ORACLE_DIR="/opt/oracle"
        ORACLE_CLIENT_DIR="$ORACLE_DIR/instantclient_21_15"

        if [ ! -d "$ORACLE_CLIENT_DIR" ]; then
            if [ -f "/tmp/oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm" ] && \
               [ -f "/tmp/oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm" ]; then
                cd /tmp
                sudo alien -i oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm
                sudo alien -i oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm
                sudo mkdir -p "$ORACLE_DIR"
                if [ -d "/usr/lib/oracle/${ORACLE_MAJOR}/client64" ]; then
                    sudo ln -sf "/usr/lib/oracle/${ORACLE_MAJOR}/client64" "$ORACLE_CLIENT_DIR"
                fi
                cat | sudo tee /etc/profile.d/oracle.sh > /dev/null <<EOF
export ORACLE_HOME=$ORACLE_CLIENT_DIR
export LD_LIBRARY_PATH=\$ORACLE_HOME/lib:\$LD_LIBRARY_PATH
export PATH=\$ORACLE_HOME/bin:\$PATH
export TNS_ADMIN=\$ORACLE_HOME/network/admin
EOF
                sudo mkdir -p "$ORACLE_CLIENT_DIR/network/admin"
                echo "  ✓ Oracle Instant Client installed"
            else
                echo "  ⚠ Oracle RPMs not found in /tmp/ → skipped"
                echo "    Place oracle-instantclient-basic-${ORACLE_VERSION}-1.x86_64.rpm"
                echo "    and oracle-instantclient-sqlplus-${ORACLE_VERSION}-1.x86_64.rpm"
                echo "    in /tmp/ and re-run to install Oracle support."
            fi
        else
            echo "  ✓ Oracle Instant Client already installed"
        fi
        ;;
esac

# =========================================
#   5/5 - Install package
# =========================================
echo ""
echo "========================================="
echo "  5/5 - Installing package"
echo "========================================="

case "$DISTRO" in
    arch|manjaro|endeavouros|cachyos)
        sudo pacman -U --noconfirm "$PKG_FILE"
        ;;
    debian|ubuntu|linuxmint|pop)
        sudo dpkg -i "$PKG_FILE"
        sudo apt-get install -f -y
        ;;
esac

# Symlink /opt/rdp-user → /opt/rdp-users
echo ""
echo "→ Configuring system..."
if [ ! -e /opt/rdp-user ]; then
    sudo ln -s /opt/rdp-users /opt/rdp-user
    echo "  ✓ Created symlink /opt/rdp-user → /opt/rdp-users"
else
    echo "  ✓ Symlink /opt/rdp-user already exists"
fi

echo ""
echo "========================================="
echo "  ✓ Installation complete!"
echo "========================================="
echo ""
echo "Run: rdp-session-manager"
