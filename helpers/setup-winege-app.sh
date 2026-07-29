#!/bin/bash
set -e

USERNAME="$1"
HOME_DIR="$2"
EXE_PATH="$3"
WINE_PREFIX="${4:-$HOME_DIR/.wine}"

[ -z "$USERNAME" ] || [ -z "$HOME_DIR" ] || [ -z "$EXE_PATH" ] && {
    echo "Usage: $0 USERNAME HOME_DIR EXE_PATH [WINE_PREFIX]"
    exit 1
}

[ ! -f "$EXE_PATH" ] && {
    echo "Error: File not found: $EXE_PATH"
    exit 1
}

for cmd in wget tar; do
    command -v $cmd &>/dev/null || {
        echo "Error: $cmd is not installed"
        exit 1
    }
done

echo "Configuring WineGE RemoteApp for: $USERNAME"
echo "  Executable: $EXE_PATH"

WINEGE_DIR="$HOME_DIR/.local/share/winege"
WINEGE_VERSION="GE-Proton8-26"
WINEGE_FILENAME="wine-lutris-$WINEGE_VERSION-x86_64"
WINEGE_URL="https://github.com/GloriousEggroll/wine-ge-custom/releases/download/$WINEGE_VERSION/$WINEGE_FILENAME.tar.xz"
WINE_BIN="$WINEGE_DIR/lutris-$WINEGE_VERSION-x86_64/bin/wine"

# Download WineGE
mkdir -p "$WINEGE_DIR"
if [ ! -d "$WINEGE_DIR/lutris-$WINEGE_VERSION-x86_64" ]; then
    echo "→ Downloading WineGE $WINEGE_VERSION (~750 MB)..."
    cd /tmp
    wget --timeout=300 --tries=3 --show-progress "$WINEGE_URL" -O "winege-$USERNAME.tar.xz" || {
        echo "Error downloading WineGE"
        exit 1
    }
    echo "→ Extracting..."
    tar -xf "winege-$USERNAME.tar.xz" -C "$WINEGE_DIR" || {
        rm -f "winege-$USERNAME.tar.xz"
        exit 1
    }
    rm "winege-$USERNAME.tar.xz"
    echo "  OK WineGE installed"
fi

chown -R "$USERNAME:rdp-users" "$WINEGE_DIR"

# Criar Wine Prefix
if [ ! -d "$WINE_PREFIX" ]; then
echo "→ Creating Wine prefix..."
    su - "$USERNAME" -c "WINEPREFIX='$WINE_PREFIX' WINEARCH=win64 WINEDLLOVERRIDES='mscoree,mshtml=' '$WINE_BIN' wineboot -u" 2>/dev/null

    cat >> "$WINE_PREFIX/user.reg" <<EOFWINE

[Software\\\\Wine] $(date +%s)
"ThreadStackSize"="2097152"
EOFWINE
    chown "$USERNAME:rdp-users" "$WINE_PREFIX/user.reg"
    echo "  OK Wine prefix created"
fi

# Copiar executável para WindowsApps
echo "→ Copying executable to WindowsApps..."
EXE_BASENAME=$(basename "$EXE_PATH")
EXE_DIR=$(dirname "$EXE_PATH")
APPS_DIR="$HOME_DIR/WindowsApps"
TARGET_EXE="$APPS_DIR/$EXE_BASENAME"

mkdir -p "$APPS_DIR"

# Copiar o .exe
cp "$EXE_PATH" "$TARGET_EXE"
chmod 755 "$TARGET_EXE"

# Copiar arquivos de suporte da mesma pasta (DLLs, PNGs, INIs, etc.)
for EXT in dll ini cfg xml png jpg bmp dat; do
    cp "$EXE_DIR"/*.$EXT "$APPS_DIR/" 2>/dev/null || true
done

# Ajustar permissões
chown -R "$USERNAME:rdp-users" "$APPS_DIR"

echo "  OK Executable copied to $TARGET_EXE"

# Salvar caminho do executável na WindowsApps
echo "$TARGET_EXE" > "$HOME_DIR/.winege_app_path"
chown "$USERNAME:rdp-users" "$HOME_DIR/.winege_app_path"

# Criar wrapper script
WRAPPER_SCRIPT="$HOME_DIR/.launch_winege_app.sh"
cat > "$WRAPPER_SCRIPT" <<'EOF'
#!/bin/bash
LOG_FILE="$HOME/.winege_launch.log"
echo "=== $(date) ===" >> "$LOG_FILE"

export HOME="HOME_DIR_PLACEHOLDER"
export USER="USERNAME_PLACEHOLDER"
export WINEPREFIX="WINE_PREFIX_PLACEHOLDER"
export WINEARCH=win64
export WINE_HEAP_SIZE=512M
export WINEDEBUG=-all

ulimit -s 16384
ulimit -n 4096

if [ -z "$DISPLAY" ]; then
    XORG_LOG=$(ls -t $HOME/.xorgxrdp.*.log 2>/dev/null | head -1)
    if [ -n "$XORG_LOG" ]; then
        DISPLAY_NUM=$(basename "$XORG_LOG" | sed 's/\.xorgxrdp\.\([0-9]*\)\.log/\1/')
        export DISPLAY=":$DISPLAY_NUM"
    else
        export DISPLAY=":10"
    fi
fi

WINE_BIN="WINE_BIN_PLACEHOLDER"
APP_EXE=$(cat "$HOME/.winege_app_path")

echo "Wine: $WINE_BIN" >> "$LOG_FILE"
echo "Exe: $APP_EXE" >> "$LOG_FILE"
echo "Display: $DISPLAY" >> "$LOG_FILE"

"$WINE_BIN" "$APP_EXE" "$@" >> "$LOG_FILE" 2>&1
EOF

sed -i "s|HOME_DIR_PLACEHOLDER|$HOME_DIR|g; s|USERNAME_PLACEHOLDER|$USERNAME|g; s|WINE_PREFIX_PLACEHOLDER|$WINE_PREFIX|g; s|WINE_BIN_PLACEHOLDER|$WINE_BIN|g" "$WRAPPER_SCRIPT"
chmod 755 "$WRAPPER_SCRIPT"
chown "$USERNAME:rdp-users" "$WRAPPER_SCRIPT"

# Salvar config
cat > "$HOME_DIR/.winege_config" <<EOF
WINEGE_DIR=$WINEGE_DIR
WINE_PREFIX=$WINE_PREFIX
WINE_BIN=$WINE_BIN
WRAPPER_SCRIPT=$WRAPPER_SCRIPT
EOF
chown "$USERNAME:rdp-users" "$HOME_DIR/.winege_config"

echo "OK WineGE configured successfully!"
echo "Executable will run from: $EXE_PATH"
exit 0
