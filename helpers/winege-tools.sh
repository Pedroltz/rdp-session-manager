#!/bin/bash
set -e

COMMAND="$1"
USERNAME="$2"

[ -z "$COMMAND" ] || [ -z "$USERNAME" ] && {
    echo "Usage: $0 {list-exes|view-logs|copy-files} USERNAME"
    echo ""
    echo "Commands:"
    echo "  list-exes   - List available executables"
    echo "  view-logs   - View Wine execution logs"
    echo "  copy-files  - Copy application files to the home directory"
    exit 1
}

HOME_DIR="/opt/rdp-users/$USERNAME"
[ ! -d "$HOME_DIR" ] && {
        echo "Error: User does not exist: $USERNAME"
    exit 1
}

find_installed_apps() {
    find "$HOME_DIR/.wine/drive_c/Program Files" "$HOME_DIR/.wine/drive_c/Program Files (x86)" \
        -name "*.exe" -type f 2>/dev/null | \
        grep -v -i "unins\|uninst\|windows nt\|internet explorer\|windows media\|windows mail\|windows photo\|wordpad\|notepad"
}

case "$COMMAND" in
    list-exes)
        echo "Executables for $USERNAME:"
        echo ""

        [ -d "$HOME_DIR/WindowsApps" ] && {
            echo "WindowsApps (portable):"
            find "$HOME_DIR/WindowsApps" -name "*.exe" -type f 2>/dev/null | sed 's/^/  /'
            echo ""
        }

        [ -d "$HOME_DIR/.wine/drive_c" ] && {
            echo "Installed applications:"
            find_installed_apps | sed 's/^/  /'
            echo ""
        }

        echo "Current executable:"
            [ -f "$HOME_DIR/.winege_app_path" ] && cat "$HOME_DIR/.winege_app_path" || echo "  (none)"
        ;;

    view-logs)
        LOG_FILE="$HOME_DIR/.winege_launch.log"
        [ ! -f "$LOG_FILE" ] && {
                echo "No log found"
            exit 1
        }
        echo "=== Logs WineGE: $USERNAME ==="
        tail -100 "$LOG_FILE"
        ;;

    copy-files)
        [ ! -d "$HOME_DIR/.wine" ] && {
                echo "Error: Wine prefix not found"
            exit 1
        }

        INSTALLED_APP=$(find_installed_apps | head -n 1)
        [ -z "$INSTALLED_APP" ] && {
                echo "Error: No application installed"
            exit 1
        }

        APP_DIR=$(dirname "$INSTALLED_APP")
            echo "Copying files from: $(basename "$APP_DIR")"

        FILE_COUNT=0
        for EXT in ini dll dat png cfg xml conf jpg bmp ico; do
            while IFS= read -r -d '' file; do
                cp "$file" "$HOME_DIR/" 2>/dev/null && {
                    chown "$USERNAME:rdp-users" "$HOME_DIR/$(basename "$file")"
                    FILE_COUNT=$((FILE_COUNT + 1))
                }
            done < <(find "$APP_DIR" -maxdepth 1 -name "*.$EXT" -type f -print0 2>/dev/null)
        done

        echo "OK $FILE_COUNT files copied"
        ;;

    *)
        echo "Invalid command: $COMMAND"
        exit 1
        ;;
esac

exit 0
