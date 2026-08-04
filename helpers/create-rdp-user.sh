#!/bin/bash
# Helper script para criar usuário RDP com pkexec
# Uso: pkexec helpers/create-rdp-user.sh USERNAME USER_UID HOME_DIR FULLNAME SESSION_TYPE SESSION_COMMAND [APP_ARGS]

set -e

step() {
    printf '[%(%Y-%m-%dT%H:%M:%S%z)T] %s\n' -1 "$*"
}

USERNAME="$1"
USER_UID="$2"
HOME_DIR="$3"
FULLNAME="$4"
SESSION_TYPE="$5"        # 'desktop', 'remoteapp', ou 'winege-remoteapp'
SESSION_COMMAND="$6"     # DE command (ex: startxfce4), app command (ex: firefox), ou .exe path para WineGE
APP_ARGS="$7"            # Argumentos do app (apenas para remoteapp)

# Validar parâmetros
if [ -z "$USERNAME" ] || [ -z "$USER_UID" ] || [ -z "$HOME_DIR" ]; then
    echo "Error: Not enough arguments"
    echo "Usage: $0 USERNAME USER_UID HOME_DIR [FULLNAME] [SESSION_TYPE] [SESSION_COMMAND] [APP_ARGS]"
    exit 1
fi

# Defaults
SESSION_TYPE="${SESSION_TYPE:-desktop}"
SESSION_COMMAND="${SESSION_COMMAND:-startxfce4}"

echo "Creating RDP user: $USERNAME"

# Detectar layout de teclado do sistema
XKBLAYOUT="us"
XKBVARIANT=""
XKBMODEL="pc105"

if [ -f /etc/default/keyboard ]; then
    source /etc/default/keyboard
    echo "→ Keyboard layout detected: $XKBLAYOUT"
fi

# Construir comando setxkbmap
SETXKBMAP_CMD="setxkbmap -layout $XKBLAYOUT"
if [ -n "$XKBVARIANT" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -variant $XKBVARIANT"
fi
if [ -n "$XKBMODEL" ]; then
    SETXKBMAP_CMD="$SETXKBMAP_CMD -model $XKBMODEL"
fi

# 1. Criar grupo rdp-users se não existir
if ! getent group rdp-users > /dev/null 2>&1; then
    echo "→ Creating rdp-users group..."
    /usr/sbin/groupadd rdp-users
fi

# 2. Criar diretório base se não existir e instalar launcher
if [ ! -d "/opt/rdp-users" ]; then
    echo "→ Creating /opt/rdp-users directory..."
    /usr/bin/mkdir -p /opt/rdp-users
    /usr/bin/chmod 755 /opt/rdp-users
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/rdp-session-launcher.py" ]; then
    /usr/bin/cp "$SCRIPT_DIR/rdp-session-launcher.py" /opt/rdp-users/rdp-session-launcher.py
    /usr/bin/chmod 755 /opt/rdp-users/rdp-session-launcher.py
fi

# 3. Criar usuário
step "→ Creating user $USERNAME (UID: $USER_UID)..."
if [ -n "$FULLNAME" ]; then
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash -c "$FULLNAME" "$USERNAME"
else
    /usr/sbin/useradd -u "$USER_UID" -d "$HOME_DIR" -m -g rdp-users -s /bin/bash "$USERNAME"
fi
step "  OK System user created"

# 4. Ajustar permissões do home directory (751 para permitir leitura do .xsession)
step "→ Adjusting home directory permissions..."
/usr/bin/chmod 751 "$HOME_DIR"
step "  OK Home directory permissions adjusted"

# 5. Criar arquivo .xsession
step "→ Creating .xsession file (mode: $SESSION_TYPE)..."
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
$SETXKBMAP_CMD

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
    P_APP_ID=$(echo "$PROFILE_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('windows_app_id',''))")

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
        OPENBOX_PID=$!
        sleep 1
        $P_CMD $P_ARGS &
        APP_PID=$!

        WINDOW_FOUND=false
        for i in $(seq 1 20); do
            if xprop -root _NET_CLIENT_LIST 2>/dev/null | grep -q "0x[1-9a-f]"; then
                WINDOW_FOUND=true
                break
            fi
            sleep 0.5
        done

        if [ "$WINDOW_FOUND" = true ]; then
            while true; do
                CLIENTS=$(xprop -root _NET_CLIENT_LIST 2>/dev/null | grep "0x[1-9a-f]" || true)
                if [ -z "$CLIENTS" ]; then
                    break
                fi
                sleep 1
            done
        else
            while kill -0 $APP_PID 2>/dev/null || pgrep -u "$USER" -f "$P_CMD|electron|code|chrome|firefox|thunderbird|flatpak|snap" >/dev/null 2>&1; do
                sleep 1
            done
        fi

        kill $OPENBOX_PID 2>/dev/null || true
        exit 0
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
        OPENBOX_PID=$!
        sleep 1
        WINDOWS_LAUNCHER="/usr/share/rdp-session-manager/helpers/launch-windows-app.py"
        if [ -n "$P_APP_ID" ] && [ -f "$WINDOWS_LAUNCHER" ]; then
            python3 "$WINDOWS_LAUNCHER" "$P_APP_ID" &
        elif [ -f "$HOME/.launch_winege_app.sh" ]; then
            $HOME/.launch_winege_app.sh $P_ARGS &
        else
            wine "$P_CMD" $P_ARGS &
        fi
        APP_PID=$!

        WINDOW_FOUND=false
        for i in $(seq 1 20); do
            if xprop -root _NET_CLIENT_LIST 2>/dev/null | grep -q "0x[1-9a-f]"; then
                WINDOW_FOUND=true
                break
            fi
            sleep 0.5
        done

        if [ "$WINDOW_FOUND" = true ]; then
            while true; do
                CLIENTS=$(xprop -root _NET_CLIENT_LIST 2>/dev/null | grep "0x[1-9a-f]" || true)
                if [ -z "$CLIENTS" ]; then
                    break
                fi
                sleep 1
            done
        else
            while kill -0 $APP_PID 2>/dev/null || pgrep -u "$USER" -f "wine|wineserver|$P_CMD" >/dev/null 2>&1; do
                sleep 1
            done
        fi

        kill $OPENBOX_PID 2>/dev/null || true
        exit 0
    else
        case "$P_DE" in
            gnome)
                export XDG_CURRENT_DESKTOP=GNOME-Flashback:GNOME
                export XDG_SESSION_DESKTOP=gnome-flashback-metacity
                export XDG_SESSION_TYPE=x11
                export DESKTOP_SESSION=gnome-flashback-metacity
                if command -v gnome-flashback >/dev/null 2>&1; then
                    exec gnome-session --session=gnome-flashback-metacity
                else
                    export XDG_CURRENT_DESKTOP=GNOME
                    export XDG_SESSION_DESKTOP=gnome
                    export DESKTOP_SESSION=gnome
                    exec gnome-session --session=gnome
                fi
                ;;
            kde)
                export XDG_CURRENT_DESKTOP=KDE
                export XDG_SESSION_DESKTOP=KDE
                export XDG_SESSION_TYPE=x11
                export DESKTOP_SESSION=plasma
                export KDE_SESSION_VERSION=6
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

# Fallback se não usar perfis
exec $SESSION_COMMAND $APP_ARGS
EOFSCRIPT

sed -i "s|\$USERNAME|$USERNAME|g" "$XSESSION_FILE"
sed -i "s|\$HOME_DIR|$HOME_DIR|g" "$XSESSION_FILE"
sed -i "s|\$SESSION_COMMAND|$SESSION_COMMAND|g" "$XSESSION_FILE"
sed -i "s|\$APP_ARGS|$APP_ARGS|g" "$XSESSION_FILE"
sed -i "s|\$SETXKBMAP_CMD|$SETXKBMAP_CMD|g" "$XSESSION_FILE"

/usr/bin/chmod 755 "$XSESSION_FILE"
/usr/bin/chown "$USERNAME:rdp-users" "$XSESSION_FILE"

# Create .xinitrc (required for Arch Linux startwm.sh)
XINITRC_FILE="$HOME_DIR/.xinitrc"
/usr/bin/ln -sf "$XSESSION_FILE" "$XINITRC_FILE"
/usr/bin/chown -h "$USERNAME:rdp-users" "$XINITRC_FILE"
echo "  OK .xsession and .xinitrc files created"

# Replace the legacy inline dispatcher with the versioned, argument-safe launcher.
SESSION_WRAPPER="$SCRIPT_DIR/create-session-wrapper.sh"
if [ ! -x "$SESSION_WRAPPER" ]; then
    echo "  X Error: create-session-wrapper.sh is missing or not executable" >&2
    exit 1
fi
"$SESSION_WRAPPER" "$USERNAME" "$HOME_DIR"
RESOURCE_PROFILE="linux-light"
[ "$SESSION_TYPE" = "winege-remoteapp" ] && RESOURCE_PROFILE="windows-standard"
/usr/bin/python3 "$SCRIPT_DIR/apply-user-resource.py" "$USERNAME" "$RESOURCE_PROFILE"

# 6. Configure the maintained umu runtime for Windows RemoteApp.
if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    echo ""
    echo "→ Configuring Windows RemoteApp (umu)..."

    # SESSION_COMMAND contém o caminho do .exe
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    WINEGE_SCRIPT="$SCRIPT_DIR/setup-winege-app.sh"

    if [ ! -f "$WINEGE_SCRIPT" ]; then
        echo "  X Error: setup-winege-app.sh script not found in $SCRIPT_DIR"
        exit 1
    fi

    # Executar setup do WineGE (não precisa de pkexec, já estamos como root)
    bash "$WINEGE_SCRIPT" "$USERNAME" "$HOME_DIR" "$SESSION_COMMAND"

    if [ $? -ne 0 ]; then
        echo "  X Error configuring WineGE"
        exit 1
    fi

    echo "  OK Windows RemoteApp configured successfully"
fi

echo "OK User $USERNAME created successfully!"
echo "  - Keyboard layout: $XKBLAYOUT"
exit 0
