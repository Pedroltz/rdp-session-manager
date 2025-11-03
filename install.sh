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
    zenity

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
