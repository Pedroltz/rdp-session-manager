#!/bin/bash
###############################################################################
# Uninstall RDP Session Manager
###############################################################################

echo "========================================="
echo "  Uninstalling RDP Session Manager"
echo "========================================="
echo ""

echo "→ Removing package..."
sudo apt-get remove -y rdp-session-manager 2>/dev/null || true
sudo dpkg --remove --force-all rdp-session-manager 2>/dev/null || true

echo "→ Cleaning up files..."
sudo rm -rf /usr/bin/rdp-session-manager
sudo rm -rf /usr/bin/rdpsm
sudo rm -rf /usr/share/rdp-session-manager
sudo rm-rf /usr/share/applications/com.rdp.SessionManager.desktop
sudo rm -rf /usr/share/icons/hicolor/scalable/apps/com.rdp.SessionManager.png
sudo rm -rf /usr/share/polkit-1/actions/com.rdp.SessionManager.policy
sudo rm -rf /usr/share/glib-2.0/schemas/com.rdp.SessionManager.gschema.xml
sudo rm -rf /usr/share/metainfo/com.rdp.SessionManager.appdata.xml

echo "→ Updating system caches..."
sudo gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
sudo update-desktop-database /usr/share/applications 2>/dev/null || true
sudo glib-compile-schemas /usr/share/glib-2.0/schemas 2>/dev/null || true

echo ""
echo "✓ Uninstall complete!"
