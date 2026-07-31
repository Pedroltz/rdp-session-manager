#!/bin/bash
# Helper script to update RDP user profiles and .xsession dispatcher with pkexec/sudo
# Usage: pkexec helpers/update-rdp-user-profiles.sh USERNAME PROFILES_JSON_FILE

set -e

USERNAME="$1"
PROFILES_JSON_SRC="$2"

if [ -z "$USERNAME" ] || [ -z "$PROFILES_JSON_SRC" ] || [ ! -f "$PROFILES_JSON_SRC" ]; then
    echo "Error: Invalid arguments"
    echo "Usage: $0 USERNAME PROFILES_JSON_FILE"
    exit 1
fi

HOME_DIR=$(getent passwd "$USERNAME" | cut -d: -f6)
if [ -z "$HOME_DIR" ] || [ ! -d "$HOME_DIR" ]; then
    echo "Error: Home directory for $USERNAME not found"
    exit 1
fi

# 1. Copy profiles JSON file
PROFILES_DEST="$HOME_DIR/.rdp_profiles.json"
/usr/bin/cp "$PROFILES_JSON_SRC" "$PROFILES_DEST"
/usr/bin/chown "$USERNAME:rdp-users" "$PROFILES_DEST"
/usr/bin/chmod 644 "$PROFILES_DEST"

# 2. Update .xsession dispatcher script
XSESSION_FILE="$HOME_DIR/.xsession"

cat > "$XSESSION_FILE" <<'EOFSCRIPT'
#!/bin/bash
# RDP Session startup script with multi-profile dispatcher for $USERNAME

export HOME=$HOME_DIR
export USER=$USERNAME
export LOGNAME=$USERNAME
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin:/var/lib/flatpak/exports/bin:$PATH"
export XDG_DATA_DIRS="/var/lib/snapd/desktop:/var/lib/flatpak/exports/share:$HOME_DIR/.local/share/flatpak/exports/share:/usr/local/share:/usr/share:${XDG_DATA_DIRS:-}"

# Configure keyboard layout
if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    setxkbmap -layout ${XKBLAYOUT:-us} -variant ${XKBVARIANT:-} -model ${XKBMODEL:-pc105} 2>/dev/null || true
fi

# Configure D-Bus
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax --exit-with-session)
fi

# Configure Openbox for full-screen launcher
mkdir -p $HOME/.config/openbox
cat > $HOME/.config/openbox/rc.xml <<'OPENBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <fullscreen>yes</fullscreen>
      <decor>no</decor>
    </application>
  </applications>
</openbox_config>
OPENBOXEOF

openbox --config-file $HOME/.config/openbox/rc.xml &
LAUNCHER_WM_PID=$!
sleep 0.5

# Check for multi-profile setup
LAUNCHER="/opt/rdp-users/rdp-session-launcher.py"
SELECTED_FILE="/tmp/selected_profile_${USER}_$$.json"

if [ -f "$HOME/.rdp_profiles.json" ] && [ -f "$LAUNCHER" ] && python3 "$LAUNCHER" "$1" > "$SELECTED_FILE" 2>/dev/null; then
    kill $LAUNCHER_WM_PID 2>/dev/null || true
    PROFILE_JSON=$(cat "$SELECTED_FILE")
    rm -f "$SELECTED_FILE"

    P_TYPE=$(echo "$PROFILE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('profile_type','desktop'))")
    P_DE=$(echo "$PROFILE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('desktop_env','xfce'))")
    P_CMD=$(echo "$PROFILE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('app_command',''))")
    P_ARGS=$(echo "$PROFILE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('app_args',''))")

    if [ "$P_TYPE" = "remoteapp" ]; then
        mkdir -p $HOME/.config/openbox
        cat > $HOME/.config/openbox/rc.xml <<'OPENBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>yes</decor>
    </application>
  </applications>
</openbox_config>
OPENBOXEOF
        openbox --config-file $HOME/.config/openbox/rc.xml &
        sleep 1
        exec $P_CMD $P_ARGS
    elif [ "$P_TYPE" = "winege-remoteapp" ]; then
        mkdir -p $HOME/.config/openbox
        cat > $HOME/.config/openbox/rc.xml <<'OPENBOXEOF'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications>
    <application class="*">
      <maximized>yes</maximized>
      <decor>yes</decor>
    </application>
  </applications>
</openbox_config>
OPENBOXEOF
        openbox --config-file $HOME/.config/openbox/rc.xml &
        sleep 1
        if [ -f "$HOME/.launch_winege_app.sh" ]; then
            exec $HOME/.launch_winege_app.sh $P_ARGS
        else
            exec wine "$P_CMD" $P_ARGS
        fi
    else
        case "$P_DE" in
            gnome)
                export XDG_CURRENT_DESKTOP=GNOME-Flashback:GNOME
                export XDG_SESSION_DESKTOP=gnome-flashback-metacity
                export XDG_SESSION_TYPE=x11
                export DESKTOP_SESSION=gnome-flashback-metacity
                exec gnome-session
                ;;
            kde)
                export XDG_CURRENT_DESKTOP=KDE
                export XDG_SESSION_DESKTOP=KDE
                export XDG_SESSION_TYPE=x11
                export DESKTOP_SESSION=plasma
                exec startplasma-x11
                ;;
            *)
                export XDG_CURRENT_DESKTOP=XFCE
                export XDG_SESSION_DESKTOP=xfce
                export XDG_SESSION_TYPE=x11
                export DESKTOP_SESSION=xfce
                exec startxfce4
                ;;
        esac
    fi
fi

# Fallback
exec startxfce4
EOFSCRIPT

sed -i "s|\$USERNAME|$USERNAME|g" "$XSESSION_FILE"
sed -i "s|\$HOME_DIR|$HOME_DIR|g" "$XSESSION_FILE"
/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

echo "OK Profiles and .xsession updated for $USERNAME"
