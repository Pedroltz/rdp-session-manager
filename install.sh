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
    python3-psutil

echo ""
echo "→ Installing package..."
sudo dpkg -i "$DEB_FILE"
sudo apt-get install -f -y

echo ""
echo "✓ Installation complete!"
echo ""
echo "Run: rdp-session-manager"
